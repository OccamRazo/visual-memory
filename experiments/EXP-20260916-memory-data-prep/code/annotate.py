#!/usr/bin/env python3
"""Resumable draft annotation and blind visual audit. All labels are proxies."""
import argparse
import base64
import collections
import concurrent.futures
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import threading
import time
import zipfile
from urllib.parse import urlsplit

import av
import httpx
from openai import OpenAI
from PIL import Image
import pysrt

from prepare import dump, jsonl, sha

STOP = set("a an the this that these those is are was were be been being it its in on at of to for from by with as and or but what which who whom whose how when where why does do did has have had video shown show showing following according most mainly can could would should".split())


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def terms(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


def retrieve(question, annotation, candidates, limit):
    queries = [question] + annotation.get("search_queries", [])
    qtokens = set(terms(" ".join(queries)))
    docs = [collections.Counter(terms(c["text"])) for c in candidates]
    df = collections.Counter(w for d in docs for w in d)
    avg = sum(sum(d.values()) for d in docs) / max(1, len(docs))
    scored = []
    for c, d in zip(candidates, docs):
        dl = sum(d.values())
        score = sum(math.log(1 + (len(docs) - df[w] + 0.5)/(df[w] + 0.5)) * d[w] * 2.5 / (d[w] + 1.5 * (0.25 + 0.75 * dl / max(1, avg))) for w in qtokens if d[w])
        scored.append((score, c))
    scored.sort(key=lambda x: (-x[0], x[1]["start_s"]))
    return [{**c, "bm25_score": round(score, 6)} for score, c in scored[:limit]]


def retrieve_per_fact(question, annotation, candidates, limit):
    # Evaluation-only search may use the unverified reference; never reuse as a method reader.
    items = re.findall(r"\([a-z]\)\s*(.*?)(?=\([a-z]\)|$)", question, re.I | re.S)
    queries = [x.strip(" ;?.") for x in items]
    queries.extend(f["statement"] for f in annotation["required_facts"])
    queries.append(annotation["reference_answer_draft"])
    queries.extend(annotation.get("search_queries", []))
    queries.append(question)
    queries = list(dict.fromkeys(q for q in queries if q.strip()))
    rankings = [retrieve(q, {"search_queries":[]}, candidates, 4) for q in queries]
    selected, seen = [], set()
    for depth in range(4):
        for query, ranking in zip(queries, rankings):
            if depth >= len(ranking):
                continue
            row = ranking[depth]
            if row["source_id"] not in seen:
                selected.append({**row,"matched_annotation_query":query})
                seen.add(row["source_id"])
            if len(selected) >= limit:
                return selected
    return selected


class Runner:
    def __init__(self, config, inventory, output):
        self.cfg = json.loads(config.read_text())
        self.inventory, self.output = inventory, output
        self.output.mkdir(parents=True, exist_ok=True)
        self.code = Path(__file__).resolve().parent
        self.prompts = {p.stem: p.read_text() for p in (self.code / "prompts").glob("*.txt")}
        if self.cfg.get("include_official_subtitles"):
            self.prompts["blind_visual"] = self.prompts["blind_multimodal"]
        self.credentials = json.loads(Path(self.cfg["credentials_file"]).read_text())
        self.model = self.credentials["model"]
        base = self.credentials["base_url"].rstrip("/")
        if urlsplit(base).path in ("", "/"):
            base += "/v1"
        self.base = base
        self.local = threading.local()
        self.questions = {q["qid"]: q for q in read_jsonl(inventory / "questions.jsonl")}
        self.manifest = json.loads((inventory / "selection_manifest.json").read_text())
        self.by_history = collections.defaultdict(list)
        for c in read_jsonl(inventory / "candidates.jsonl"):
            self.by_history[c["history_id"]].append(c)
        for values in self.by_history.values():
            values.sort(key=lambda c: c["start_s"])
        state = {"config_sha256": sha(config), "inventory_manifest_sha256": sha(inventory / "selection_manifest.json"), "requested_model": self.model, "prompts_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k,v in self.prompts.items()}, "code_sha256": sha(__file__), "temperature": "provider_default_unset", "response_format": "json_object", "credentials_in_logs": False, "human_audit": "not_run"}
        p = self.output / "run_manifest.json"
        if p.exists() and json.loads(p.read_text()) != state:
            raise RuntimeError("Run implementation/config changed; use a new output directory")
        dump(p, state)
        snapshot = self.output / "code_snapshot"
        if not snapshot.exists():
            shutil.copytree(self.code, snapshot, ignore=shutil.ignore_patterns("__pycache__"))
        dump(self.output / "protocol.json", self.cfg)
        if self.cfg.get("draft_source"):
            source = Path(self.cfg["draft_source"])
            target = self.output / "drafts"
            target.mkdir(exist_ok=True)
            provenance = {}
            for p in sorted((source / "drafts").glob("*.json")):
                destination = target / p.name
                if destination.exists() and sha(destination) != sha(p):
                    raise RuntimeError("Inherited draft differs")
                if not destination.exists():
                    shutil.copyfile(p,destination)
                provenance[p.name] = {"source":str(p),"sha256":sha(p)}
            dump(self.output / "inherited_drafts.json",provenance)

    def client(self):
        if not hasattr(self.local, "client"):
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            self.local.client = OpenAI(api_key=self.credentials["api_key"], base_url=self.base, http_client=httpx.Client(proxy=proxy, trust_env=False), timeout=self.cfg["api"]["timeout_seconds"], max_retries=0)
        return self.local.client

    def call(self, qid, stage, data=None, content=None):
        prompt = self.prompts[stage]
        user = content if content is not None else canonical(data)
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": user}]
        max_tokens = self.cfg["api"]["visual_output_tokens" if stage == "blind_visual" else "text_output_tokens"]
        payload = {"model": self.model, "messages": messages, "max_completion_tokens": max_tokens, "response_format": {"type": "json_object"}}
        digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
        folder = self.output / "calls" / qid.replace(":", "__") / stage
        folder.mkdir(parents=True, exist_ok=True)
        completed = folder / "completed.json"
        if completed.exists():
            saved = json.loads(completed.read_text())
            if saved["request_sha256"] != digest:
                raise RuntimeError("Cached request differs")
            return saved["parsed"]
        manifest = json.loads(canonical(payload))
        if content is not None:
            for item in manifest["messages"][1]["content"]:
                if item["type"] == "image_url":
                    url = item["image_url"]["url"]
                    item["image_url"]["url"] = "sha256:" + hashlib.sha256(base64.b64decode(url.split(",",1)[1])).hexdigest()
        dump(folder / "request_manifest.json", {"request_sha256": digest, "payload": manifest})
        previous = len(list(folder.glob("attempt-*.json")))
        for attempt in range(self.cfg["api"]["attempts"]):
            started = time.time()
            record = {"qid": qid, "stage": stage, "request_sha256": digest, "started_unix": started, "attempt": previous + attempt + 1}
            try:
                r = self.client().chat.completions.create(**payload)
                raw = r.choices[0].message.content or ""
                record.update({"resolved_model": r.model, "response_id": r.id, "finish_reason": r.choices[0].finish_reason, "raw_text": raw, "usage": r.usage.model_dump() if r.usage else None})
                if r.choices[0].finish_reason != "stop":
                    raise ValueError("Response was not completed normally")
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("Expected JSON object")
                record.update({"status": "ok", "elapsed_s": round(time.time()-started, 3), "parsed": parsed})
                dump(folder / f"attempt-{record['attempt']:02}.json", record)
                dump(completed, record)
                return parsed
            except Exception as exc:
                msg = str(exc).replace(self.credentials["api_key"], "<redacted>").replace(self.credentials["base_url"], "<endpoint>")
                record.update({"status": "failed", "elapsed_s": round(time.time()-started,3), "error_type": type(exc).__name__, "status_code": getattr(exc, "status_code", None), "message": msg[:1200]})
                dump(folder / f"attempt-{record['attempt']:02}.json", record)
                if attempt + 1 == self.cfg["api"]["attempts"]:
                    raise RuntimeError(f"API call failed: {qid}/{stage}, see redacted attempt record") from None

    def draft(self, qid):
        q = self.questions[qid]
        data = {k: q[k] for k in ["original_question", "original_options", "reference_draft", "official_task_type"]}
        result = self.call(qid, "draft", data=data)
        if not isinstance(result.get("short_question"), str) or not result["short_question"].strip():
            raise ValueError("Missing short question")
        if result.get("adaptation_status") not in ["unchanged", "rewritten", "needs_review", "unsuitable"]:
            raise ValueError("Invalid adaptation status")
        facts = result.get("required_facts")
        if not isinstance(facts, list) or (not facts and result["adaptation_status"] not in ["unsuitable", "needs_review"]):
            raise ValueError("Invalid fact list")
        fact_ids = [f["id"] for f in facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("Duplicate fact IDs")
        if result.get("evidence_scope") not in ["local", "cross_segment", "global_coverage", "unknown"]:
            raise ValueError("Invalid scope")
        if result.get("modality") not in ["visual", "audio_subtitle", "mixed", "unknown"]:
            raise ValueError("Invalid modality")
        labels = result.get("task_type")
        if not isinstance(labels, list) or not labels or any(x not in ["identity_handoff", "state_change", "event_order", "single_event_recognition", "other"] for x in labels):
            raise ValueError("Invalid task labels")
        dump(self.output / "drafts" / (qid.replace(":", "__") + ".json"), {"qid": qid, "annotation": result, "source_verified": False, "human_reviewed": False})
        return {"qid": qid, "status": "ok"}

    def frames(self, qid, candidates):
        folder = self.output / "frames" / qid.replace(":", "__")
        folder.mkdir(parents=True, exist_ok=True)
        records = []
        for c in candidates:
            start, end = c["video_offset_start_s"], c["video_offset_end_s"]
            # Default 10-second segments: 1 fps, chronological, actual decoded PTS recorded.
            n = min(self.cfg["visual_pilot"]["frames_per_candidate"], max(1, math.ceil(end-start)))
            targets = [start + i * (end-start)/n for i in range(n)]
            with av.open(c["video_path"]) as container:
                stream = container.streams.video[0]
                container.seek(int(max(0,start) / float(stream.time_base)), stream=stream, backward=True)
                idx = 0
                for frame in container.decode(stream):
                    if frame.pts is None:
                        continue
                    actual = float(frame.pts * stream.time_base)
                    if actual >= end:
                        break
                    if actual + 1e-6 < targets[idx]:
                        continue
                    image = frame.to_image().convert("RGB")
                    image.thumbnail((self.cfg["visual_pilot"]["max_image_side"],)*2, Image.Resampling.LANCZOS)
                    name = c["source_id"].replace(":", "__") + f"-{idx:02}.jpg"
                    file = folder / name
                    image.save(file, quality=90)
                    records.append({"source_id": c["source_id"], "path": str(file), "sha256": sha(file), "requested_time_s": targets[idx], "actual_pts_s": actual, "width": image.width, "height": image.height, "source_video": c["video_path"]})
                    idx += 1
                    while idx < n and targets[idx] <= actual + 1e-6:
                        idx += 1
                    if idx >= n:
                        break
            if not any(r["source_id"] == c["source_id"] for r in records):
                raise ValueError("No decodable frames for source " + c["source_id"])
        dump(folder / "manifest.json", records)
        return records

    def visual(self, qid):
        q = self.questions[qid]
        draft_file = self.output / "drafts" / (qid.replace(":", "__") + ".json")
        if not draft_file.exists():
            raise ValueError("Draft not completed")
        ann = json.loads(draft_file.read_text())["annotation"]
        if ann["adaptation_status"] in ["unsuitable", "needs_review"]:
            dump(self.output / "visual" / (qid.replace(":", "__") + ".json"), {"qid": qid, "status": "adaptation_requires_review", "annotation": ann, "evidence_status": "undetermined", "human_reviewed": False})
            return {"qid": qid, "status": "adaptation_requires_review"}
        history = self.by_history[q["history_id"]]
        retrieval = retrieve_per_fact if self.cfg.get("retrieval") == "per_fact_round_robin" else retrieve
        retrieved = retrieval(ann["short_question"], ann, history, self.cfg["visual_pilot"]["max_caption_candidates"])
        nomination_input = {"question": ann["short_question"], "unverified_reference": ann["reference_answer_draft"], "required_facts_draft": ann["required_facts"], "scope_draft": ann["evidence_scope"], "candidates": [{k:c[k] for k in ["source_id", "start_s", "end_s", "text", "bm25_score"]} for c in retrieved]}
        proposal = self.call(qid, "nominate", data=nomination_input)
        valid = {c["source_id"] for c in retrieved}
        selected_ids = proposal.get("selected_source_ids", [])
        if not isinstance(selected_ids, list) or len(selected_ids)>4 or any(s not in valid for s in selected_ids):
            raise ValueError("Invalid nomination IDs")
        if not selected_ids:
            dump(self.output / "visual" / (qid.replace(":", "__") + ".json"), {"qid": qid, "status": "no_evidence_nominated", "proposal": proposal, "evidence_status": "undetermined", "human_reviewed": False})
            return {"qid": qid, "status": "no_evidence_nominated"}
        selected_ids = list(dict.fromkeys(selected_ids))
        by_id = {c["source_id"]:c for c in history}
        position = {c["source_id"]:i for i,c in enumerate(history)}
        expanded = list(selected_ids)
        for offset in [-1, 1]:
            for sid in selected_ids:
                i = position[sid] + offset
                if 0 <= i < len(history):
                    neighbor = history[i]
                    if neighbor["source_id"] not in expanded and len(expanded)<self.cfg["visual_pilot"]["max_visual_candidates"]:
                        expanded.append(neighbor["source_id"])
        sources = sorted([by_id[s] for s in expanded], key=lambda c:c["start_s"])
        frames = self.frames(qid, sources)
        subtitles = []
        if self.cfg.get("include_official_subtitles"):
            archive = Path(self.cfg["datasets_root"]) / "Video-MME/subtitle.zip"
            with zipfile.ZipFile(archive) as z:
                name = f"subtitle/{q['video_id']}.srt"
                if name in z.namelist():
                    raw = z.read(name)
                    entries = pysrt.from_string(raw.decode("utf-8-sig"))
                    for i, entry in enumerate(entries):
                        start, end = entry.start.ordinal/1000, entry.end.ordinal/1000
                        source_ids = [s["source_id"] for s in sources if start < s["end_s"] and end > s["start_s"]]
                        if source_ids:
                            subtitles.append({"subtitle_id":f"{q['history_id']}:subtitle:{i:05}","start_s":start,"end_s":end,"text":entry.text,"overlapping_source_ids":source_ids})
                    dump(self.output/"subtitles"/(qid.replace(":","__")+".json"),{"archive":str(archive),"member":name,"member_sha256":hashlib.sha256(raw).hexdigest(),"segments":subtitles})
        header = {"question": ann["short_question"], "source_segments": [{k:c[k] for k in ["source_id", "start_s", "end_s"]} for c in sources], "input_note": "Sampled frames with actual PTS. No reference answers, proposed facts, generated captions or nomination reasoning supplied."}
        if self.cfg.get("include_official_subtitles"):
            header["subtitles"] = subtitles
        else:
            header["input_note"] += " Silent frames; no subtitles or audio."
        content = [{"type": "text", "text": canonical(header)}]
        for f in frames:
            content.append({"type": "text", "text": f"Source {f['source_id']}; actual frame time {f['actual_pts_s']:.3f} seconds"})
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(Path(f["path"]).read_bytes()).decode(), "detail": "high"}})
        blind = self.call(qid, "blind_visual", content=content)
        if blind.get("package_status") not in ["sufficient_proxy", "explicit_gap_proxy", "undetermined"]:
            raise ValueError("Invalid visual status")
        all_ids = set(expanded)
        for ob in blind.get("observations", []):
            if ob.get("source_id") not in all_ids:
                raise ValueError("Visual audit cited an unseen source")
        comparison = self.call(qid, "compare", data={"question": ann["short_question"], "reference_answer_draft": ann["reference_answer_draft"], "required_facts": ann["required_facts"], "scope_draft": ann["evidence_scope"], "blind_audit": blind})
        if comparison.get("evidence_status") not in ["sufficient_proxy", "explicit_gap_proxy", "undetermined"]:
            raise ValueError("Invalid comparison evidence status")
        if {f.get("fact_id") for f in comparison.get("facts", [])} != {f["id"] for f in ann["required_facts"]}:
            raise ValueError("Comparison facts do not match the rubric")
        for fact in comparison["facts"]:
            if any(s not in all_ids for s in fact.get("source_ids", [])):
                raise ValueError("Fact comparison cited an unseen source")
        for path in comparison.get("sufficient_paths_proxy", []):
            if not path or any(s not in all_ids for s in path):
                raise ValueError("Comparison cited an unseen source")
        # Scope uncertainty cannot be overridden by textual answer agreement.
        guard_flags = []
        if ann["evidence_scope"] == "global_coverage" or blind.get("requires_wider_coverage") or blind.get("requires_audio"):
            if comparison.get("evidence_status") == "sufficient_proxy":
                guard_flags.append("Sufficiency downgraded: missing whole-range coverage or audio")
                comparison = {**comparison, "evidence_status": "undetermined", "sufficient_paths_proxy": []}
        record = {"qid": qid, "status": "ok", "annotation": ann, "retrieved_sources": retrieved, "proposal": proposal, "visual_sources": sources, "frames": frames, "subtitles":subtitles, "blind_audit": blind, "comparison": comparison, "guard_flags": guard_flags, "human_reviewed": False, "labels_are_automatic_proxies": True}
        dump(self.output / "visual" / (qid.replace(":", "__") + ".json"), record)
        return {"qid": qid, "status": "ok", "evidence_status": comparison.get("evidence_status"), "frames": len(frames)}

    def summary(self):
        attempts = [json.loads(p.read_text()) for p in sorted((self.output / "calls").glob("*/*/attempt-*.json"))]
        drafts = [json.loads(p.read_text()) for p in sorted((self.output / "drafts").glob("*.json"))]
        visual = [json.loads(p.read_text()) for p in sorted((self.output / "visual").glob("*.json"))]
        token_keys = ["prompt_tokens", "completion_tokens", "total_tokens"]
        usage = {k:sum((r.get("usage") or {}).get(k,0) for r in attempts) for k in token_keys}
        result = {"draft_count": len(drafts), "adaptation_status": dict(collections.Counter(r["annotation"]["adaptation_status"] for r in drafts)), "scope_labels": dict(collections.Counter(r["annotation"]["evidence_scope"] for r in drafts)), "modality_labels": dict(collections.Counter(r["annotation"]["modality"] for r in drafts)), "visual_records": len(visual), "visual_status": dict(collections.Counter(r.get("comparison",{}).get("evidence_status",r.get("evidence_status","unknown")) for r in visual)), "reference_status": dict(collections.Counter(r.get("comparison",{}).get("reference_status","unknown") for r in visual)), "decoded_frames": sum(len(r.get("frames",[])) for r in visual), "api_attempts": len(attempts), "api_failures": sum(r["status"] != "ok" for r in attempts), "resolved_models": sorted({r.get("resolved_model") for r in attempts if r.get("resolved_model")}), "usage": usage, "billing_cost": "unknown; provider billing not queried", "human_audit": "not_run; all labels are automatic proxies", "formal_test_frozen": False, "experimental_method_runs": 0}
        dump(self.output / "summary.json", result)
        jsonl(self.output / "api_ledger.jsonl", [{k:v for k,v in r.items() if k not in ["raw_text","parsed"]} for r in attempts])
        self.review(visual, drafts)
        print(json.dumps(result,ensure_ascii=False),flush=True)

    def review(self, visual, drafts):
        parts = ["<!doctype html><meta charset='utf-8'><title>Video-MME 开发标注审核</title><style>body{font:16px system-ui;margin:32px;max-width:1400px}pre{white-space:pre-wrap;background:#f5f5f5;padding:16px}section{border-top:2px solid #ccc;margin-top:32px}figure{display:inline-block;margin:4px;vertical-align:top}img{width:220px}figcaption{font-size:12px;max-width:220px}</style><h1>Video-MME 开发标注审核</h1><p>所有标签均为自动代理，尚未人工审核。图像为实际解码帧；时间为视频实际 PTS。原始视频、caption、评分事实分别保留。</p>"]
        for r in visual:
            q = self.questions[r["qid"]]
            parts.append("<section><h2>"+html.escape(r["qid"])+"</h2><p>"+html.escape(q["original_question"])+"</p>")
            for key in ["annotation","proposal","blind_audit","comparison","guard_flags"]:
                if key in r:
                    parts.append("<details><summary>"+key+"</summary><pre>"+html.escape(json.dumps(r[key],ensure_ascii=False,indent=2))+"</pre></details>")
            for f in r.get("frames",[]):
                rel=Path(f["path"]).relative_to(self.output).as_posix()
                parts.append(f"<figure><img loading='lazy' src='{html.escape(rel,quote=True)}'><figcaption>{html.escape(f['source_id'])}<br>{f['actual_pts_s']:.3f}s</figcaption></figure>")
            parts.append("</section>")
        parts.append("<section><h2>全部开发题草稿</h2>")
        for d in drafts:
            parts.append("<details><summary>"+html.escape(d["qid"])+"</summary><pre>"+html.escape(json.dumps(d,ensure_ascii=False,indent=2))+"</pre></details>")
        (self.output / "human_review.html").write_text("\n".join(parts))
        dump(self.output / "human_review_queue.json", [{"qid": r["qid"], "reviewer": None, "reviewed_at": None, "status": "pending", "reference_correction": None, "evidence_verdict": None, "notes": None} for r in visual])


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",type=Path,required=True)
    p.add_argument("--inventory",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--stage",choices=["draft","visual","summarize"],required=True)
    p.add_argument("--limit",type=int)
    args=p.parse_args()
    r=Runner(args.config,args.inventory,args.output)
    if args.stage != "summarize":
        ids=r.manifest["dev_qids" if args.stage=="draft" else "visual_pilot_qids"]
        if args.limit:
            ids=ids[:args.limit]
        func=r.draft if args.stage=="draft" else r.visual
        results=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=r.cfg["api"]["concurrency"]) as pool:
            futures={pool.submit(func,q):q for q in ids}
            for future in concurrent.futures.as_completed(futures):
                q=futures[future]
                try:result=future.result()
                except Exception as exc:
                    result={"qid":q,"status":"failed","error_type":type(exc).__name__,"message":str(exc)[:500]}
                    dump(r.output / "failures" / f"{q.replace(':','__')}-{args.stage}-{int(time.time())}.json",result)
                results.append(result)
                print(json.dumps(result,ensure_ascii=False),flush=True)
        dump(r.output / f"{args.stage}_last_execution.json",results)
    r.summary()


if __name__=="__main__":
    main()
