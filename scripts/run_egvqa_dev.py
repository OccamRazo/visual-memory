#!/usr/bin/env python3
"""Run the remaining 48 D0 requests, with blinded judge audit materials.

Only the fixed dev annotation file is read. By default selection waits until
all six dev videos have sealed snapshots and a recorded E1 construction result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from egvqa_pilot import prompts
from egvqa_pilot.encoding import ClipEncoder
from egvqa_pilot.model import QwenBackend
from egvqa_pilot.protocol import BudgetLedger, parse_answer, parse_control, parse_judge, anonymous_judge_batch, fixed_hash_order as stable_order
from egvqa_pilot.reader import SafeReader, packet_images


CONDITIONS = ["Full", "Blind", "Key-1", "Irrel-1"]


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def append_jsonl(path, value):
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()


def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def ready_selection(args, videos):
    started = time.monotonic()
    while True:
        eligible, readiness = {}, []
        for video in videos:
            video_id = video["video_id"]
            root = args.run_dir / "prepared" / video_id
            snapshot_path = root / "snapshot/manifest.json"
            snapshot = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else {}
            qrows = []
            for question in video["questions"]:
                path = root / "e1" / question["question_id"] / "manifest.json"
                if path.exists():
                    package = json.loads(path.read_text())
                    qrows.append({"question_id": question["question_id"], "construction_status": package["construction_status"],
                                  "frontend_revision": package.get("frontend_revision"),
                                  "reasons": package.get("reasons", []), "package_hash": package["package_hash"]})
            ready = (snapshot.get("keys_status") == "ready" and len(qrows) == len(video["questions"])
                     and all(row["frontend_revision"] == "e1-v2-disjoint-time-regions" for row in qrows))
            constructed = [q for q in qrows if q["construction_status"] == "constructed_pending_human_audit"]
            readiness.append({"video_id": video_id, "ready": ready, "keys_status": snapshot.get("keys_status", "missing"),
                              "planned_questions": len(video["questions"]), "questions": qrows,
                              "snapshot_hash": snapshot.get("snapshot_hash")})
            if ready and len(constructed) >= 2:
                eligible[video_id] = constructed
        write_json(args.run_dir / "d0_preparation_wait.json", {"timestamp_utc": utc_now(), "videos": readiness,
                    "eligible_video_count": len(eligible), "elapsed_s": time.monotonic() - started})
        if len(eligible) >= 4 and all(row["ready"] for row in readiness):
            selected_videos = stable_order(list(eligible), seed=17)[:4]
            selected = [{"video_id": video_id, "question_id": qid}
                        for video_id in selected_videos
                        for qid in stable_order([row["question_id"] for row in eligible[video_id]], seed=17)[:2]]
            manifest = {"frozen_at_utc": utc_now(), "annotation_path": str(args.dev_annotations.resolve()),
                        "annotation_sha256": hashlib.sha256(args.dev_annotations.read_bytes()).hexdigest(),
                        "selection_seed": 17, "judge_order_seed": 43, "judge_batch_seed_rule": "43 + zero-based question position", "all_dev_readiness": readiness,
                        "frontend_revision": "e1-v2-disjoint-time-regions",
                        "selected_videos": selected_videos, "selected_questions": selected,
                        "conditions": CONDITIONS, "control_methods": ["R1", "R2"] * 4,
                        "expected_new_requests": 48, "existing_boundary_requests": 2,
                        "selection_rule": "Wait for all six fixed dev videos; hash-order eligible videos; first four, each first two hash-ordered constructible questions.",
                        "selection_bias": "Dev calibration uses the constructible subset (four PTS per group and three distractors). It may favor longer/clearer annotated events; this is not the eval sample.",
                        "human_audit_status": "pending; automated construction is not visual validation"}
            write_json(args.run_dir / "d0_manifest.json", manifest)
            return manifest
        if all(row["ready"] for row in readiness) and len(eligible) < 4:
            raise RuntimeError("All dev videos prepared but fewer than four have two constructible questions; D0 cannot meet the registered selection")
        if time.monotonic() - started > args.wait_timeout:
            raise TimeoutError("Timed out waiting for all six dev videos; no model requests or time-dependent sample substitutions made")
        print(json.dumps({"state": "waiting_for_all_dev", "ready_videos": sum(row["ready"] for row in readiness),
                          "eligible_videos": len(eligible), "elapsed_s": round(time.monotonic() - started)}), flush=True)
        time.sleep(20)


def e1_images(package, pixels, condition):
    groups = {group["group_id"]: group for group in package["groups"]}
    result = []
    for group_id in package["conditions"][condition]["group_ids"]:
        group = groups[group_id]
        for index, (pts, image) in enumerate(zip(group["pts"], pixels[group["image_index"]])):
            if hashlib.sha256(image.tobytes()).hexdigest() != group["frame_hashes"][index]:
                raise ValueError("E1 image hash differs from the construction manifest")
            result.append({"image": image, "id": group_id, "pts": pts})
    if len(result) != package["conditions"][condition]["num_images"]:
        raise ValueError("E1 frame count mismatch")
    return result


def quantiles(values):
    return {"n": len(values), **({f"p{p}": float(np.percentile(values, p)) for p in (50, 75, 95)} if values else {})}


def build_summary(args, ledger, calls, answers, controls, judge_batches, manifest):
    boundary = load_jsonl(args.run_dir / "boundary_calls.jsonl")
    physical = [row for row in calls if row.get("physical_request")]
    categories = {"answer_with_images": [row for row in physical if row["role"] == "answer" and row["visual_tokens"]],
                  "answer_blind": [row for row in physical if row["role"] == "answer" and not row["visual_tokens"]],
                  "control": [row for row in physical if row["role"] == "control"],
                  "judge": [row for row in physical if row["role"] == "judge"], "boundary": boundary}
    profile = {category: {"latency_s": quantiles([row["latency_s"] for row in rows]),
                "generation_s": quantiles([row["generation_s"] for row in rows if "generation_s" in row]),
                "input_tokens": quantiles([row["input_tokens"] for row in rows]),
                "output_tokens": quantiles([row["output_tokens"] for row in rows]),
                "peak_cuda_allocated_bytes": max((row.get("peak_cuda_allocated_bytes", 0) for row in rows), default=0),
                "peak_cuda_reserved_bytes": max((row.get("peak_cuda_reserved_bytes", 0) for row in rows), default=0)}
               for category, rows in categories.items()}
    auto_verdicts = {row["id"]: row for batch in judge_batches for row in batch["parsed"]}
    condition_scores = {}
    for condition in CONDITIONS:
        rows = [row for row in answers if row["condition"] == condition]
        verdicts = [auto_verdicts.get(row["anonymous_id"], {"verdict": "uncertain"})["verdict"] for row in rows]
        condition_scores[condition] = {"n": len(rows), "correct": verdicts.count("correct"), "incorrect": verdicts.count("incorrect"),
                                      "uncertain": verdicts.count("uncertain"), "accuracy_uncertain_as_zero": verdicts.count("correct") / len(rows) if rows else None}
    summary = {"completed_at_utc": utc_now(), "status": "COMPLETE" if len(calls) == 48 else "INCOMPLETE",
               "dev_answer_count": len(answers), "dev_control_count": len(controls), "dev_judge_batches": len(judge_batches),
               "selected_video_count": len(manifest["selected_videos"]), "selected_question_count": len(manifest["selected_questions"]),
               "ledger": ledger.summary(), "profile": profile,
               "gpu": {key: next((row[key] for row in calls if key in row), None)
                       for key in ["gpu_name", "gpu_compute_capability", "gpu_total_memory_bytes", "torch_cuda_version"]},
               "model_errors": sum(bool(row.get("error")) for row in calls + boundary),
               "truncated_outputs": sum(bool(row.get("truncated")) for row in calls + boundary),
               "answer_parse_failures": sum(not row["parsed"]["parse_ok"] for row in answers),
               "control_parse_failures": sum(not row["parsed"]["parse_ok"] for row in controls),
               "judge_item_parse_failures": sum(not row["parse_ok"] for batch in judge_batches for row in batch["parsed"]),
               "answer_illegal_citations": sum(not row["parsed"]["citations_legal"] for row in answers),
               "local_judge_pilot_scores_unvalidated": condition_scores,
               "human_judge_calibration": {"status": "NOT_RUN", "required_agreement": "at least 28/32", "observed_agreement": None,
                                           "blind_form": "d0_human_blind_audit.md", "separate_auto_key": "d0_judge_calibration_key.jsonl"},
               "d0_gate_passed": False, "d0_gate_note": "Human 32-answer judge agreement and remaining data/protocol gates must be assessed separately. Completion of model profiling alone does not pass D0.",
               "gpu_unloaded": True, "prompt_identity": prompts.identity()}
    write_json(args.run_dir / "d0_summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--dev-annotations", type=Path, default=Path("data/downloads/egvqa-pilot/annotations/dev.json"))
    parser.add_argument("--model-path", default="/root/autodl-tmp/models/Qwen3-VL-8B-Instruct")
    parser.add_argument("--clip-path", default="/root/autodl-tmp/models/clip-vit-base-patch32")
    parser.add_argument("--wait-timeout", type=float, default=3600)
    args = parser.parse_args()
    if args.dev_annotations.name != "dev.json":
        raise ValueError("D0 is restricted to the fixed dev.json annotation split")
    videos = json.loads(args.dev_annotations.read_text())
    if len(videos) != 6:
        raise ValueError("Expected the preregistered six-video dev split")
    manifest_path = args.run_dir / "d0_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else ready_selection(args, videos)
    if manifest["annotation_sha256"] != hashlib.sha256(args.dev_annotations.read_bytes()).hexdigest():
        raise ValueError("Dev annotation file changed after D0 manifest freeze")
    by_question = {question["question_id"]: question for video in videos for question in video["questions"]}
    ledger_path, calls_path = args.run_dir / "d0_ledger.json", args.run_dir / "d0_calls.jsonl"
    initial = json.loads((ledger_path if ledger_path.exists() else args.run_dir / "boundary_ledger.json").read_text())
    ledger = BudgetLedger.from_records(initial)
    call_records = {row["request_id"]: row for row in load_jsonl(calls_path)}
    for entry in list(ledger.entries.values()):
        if entry.state == "reserved":
            recovered = call_records.get(entry.request_id)
            ledger.finalize(entry.request_id, output_tokens=recovered["output_tokens"] if recovered and not recovered.get("error") else None,
                            error=recovered.get("error") if recovered else "Interrupted request with unknown output; full reservation retained, no retry")
    write_json(ledger_path, ledger.records())
    import torch
    encoder = ClipEncoder(args.clip_path, device="cpu")
    question_keys, truncated = encoder.texts([by_question[row["question_id"]]["question"] for row in manifest["selected_questions"]])
    query_metadata = {"encoder": encoder.identity, "questions": [{**row, "query_truncated_at_77": bool(flag)}
                      for row, flag in zip(manifest["selected_questions"], truncated)]}
    write_json(args.run_dir / "d0_retrieval_queries.json", query_metadata)
    encoder.unload()
    torch.set_num_threads(4)
    backend = QwenBackend(args.model_path, cache_dir=args.run_dir / "model_cache")
    write_json(args.run_dir / "d0_model_identity.json", backend.identity())

    def invoke(request_id, role, text, images, metadata):
        if request_id in call_records:
            return call_records[request_id]
        if request_id in ledger.entries:
            raise RuntimeError(f"Unknown interrupted output cannot be retried outside D0 quota: {request_id}")
        prepared = backend.prepare(role, text, images)
        cached = backend.cache_lookup(prepared) is not None
        ledger.reserve(request_id=request_id, phase="D0", question_id=metadata["question_id"], method=metadata["method"],
                       condition=metadata["condition"], role=role, input_tokens=prepared.input_tokens,
                       max_output_tokens=prepared.max_new_tokens, physical_request=not cached)
        write_json(ledger_path, ledger.records())
        result = backend.generate(prepared=prepared, request_id=request_id, metadata=metadata)
        # Preserve generated output before finalizing, allowing crash recovery.
        append_jsonl(calls_path, result)
        call_records[request_id] = result
        ledger.finalize(request_id, output_tokens=None if result.get("error") else result["output_tokens"], error=result.get("error"))
        write_json(ledger_path, ledger.records())
        print(json.dumps({"request_id": request_id, "role": role, "physical_so_far_including_boundaries": ledger.summary()["physical_calls"],
                          "latency_s": result["latency_s"], "output_tokens": result["output_tokens"],
                          "truncated": result["truncated"], "error": result["error"]}), flush=True)
        return result

    answers, controls, judge_batches = [], [], []
    try:
        for index, selected in enumerate(manifest["selected_questions"]):
            qid, video_id = selected["question_id"], selected["video_id"]
            question = by_question[qid]
            root = args.run_dir / "prepared" / video_id
            package_path = root / "e1" / qid / "manifest.json"
            package = json.loads(package_path.read_text())
            frozen_video = next(row for row in manifest["all_dev_readiness"] if row["video_id"] == video_id)
            frozen_package = next(row for row in frozen_video["questions"] if row["question_id"] == qid)
            if package["package_hash"] != frozen_package["package_hash"]:
                raise ValueError("E1 package changed after D0 manifest freeze")
            with np.load(package_path.parent / "pixels.npz", allow_pickle=False) as payload:
                pixels = payload["images"]
            current_answers = []
            for condition in CONDITIONS:
                images = e1_images(package, pixels, condition)
                result = invoke(f"D0-{qid}-{condition}", "answer", prompts.ANSWER.format(question=question["question"]), images,
                                {"question_id": qid, "video_id": video_id, "method": "E1_dev", "condition": condition,
                                 "package_hash": package["package_hash"], "input_hash": package["conditions"][condition]["input_hash"]})
                anonymous_id = "a" + hashlib.sha256(f"43:{qid}:{condition}".encode()).hexdigest()[:12]
                row = {"question_id": qid, "video_id": video_id, "condition": condition, "anonymous_id": anonymous_id,
                       "question": question["question"], "reference_answer": question["answer"],
                       "request_id": result["request_id"], "output_text": result["output_text"],
                       "parsed": parse_answer(result["output_text"], package["conditions"][condition]["group_ids"]),
                       "truncated": result["truncated"], "error": result["error"]}
                answers.append(row); current_answers.append(row)
            method = manifest["control_methods"][index]
            with SafeReader(root / "snapshot") as reader:
                if reader.identity["snapshot_hash"] != frozen_video["snapshot_hash"]:
                    raise ValueError("Snapshot changed after D0 manifest freeze")
                initial_ids = reader.request("rank", query=question_keys[index].tolist(), k=3)
                packet = reader.request("packet", ids=initial_ids)
                result = invoke(f"D0-{qid}-control-{method}", "control", getattr(prompts, f"CONTROL_{method}").format(question=question["question"]), packet_images(packet),
                                {"question_id": qid, "video_id": video_id, "method": method, "condition": "control",
                                 "snapshot_hash": packet["snapshot_hash"], "read_ids": initial_ids, "landlock_abi": reader.identity["abi"]})
                controls.append({"question_id": qid, "video_id": video_id, "method": method, "request_id": result["request_id"],
                                 "read_ids": initial_ids, "snapshot_hash": packet["snapshot_hash"], "landlock_abi": reader.identity["abi"],
                                 "output_text": result["output_text"], "parsed": parse_control(result["output_text"], question["question"], method)})
            by_anon = {row["anonymous_id"]: row for row in current_answers}
            raw_items = [{"item_id": row["anonymous_id"], "question": question["question"], "reference": question["answer"],
                          "prediction": row["parsed"]["answer"] or "[No parseable answer]"} for row in current_answers]
            items, batch_mapping = anonymous_judge_batch(raw_items, seed=43 + index)
            anon_order = list(batch_mapping)
            result = invoke(f"D0-{qid}-judge", "judge", prompts.JUDGE.format(items=json.dumps(items, ensure_ascii=False)), [],
                            {"question_id": qid, "video_id": video_id, "method": "anonymous_judge", "condition": "judge", "anonymous_ids": anon_order})
            parsed_local = parse_judge(result["output_text"], anon_order)
            judge_batches.append({"question_id": qid, "request_id": result["request_id"], "anonymous_input": items,
                                  "anonymous_mapping": {anon: {"question_id": qid, "global_anonymous_id": batch_mapping[anon],
                                      "condition": by_anon[batch_mapping[anon]]["condition"], "answer_request_id": by_anon[batch_mapping[anon]]["request_id"]} for anon in anon_order},
                                  "output_text": result["output_text"], "parsed_local_ids": parsed_local,
                                  "parsed": [{**row, "id": batch_mapping[row["id"]], "judge_local_id": row["id"]} for row in parsed_local]})
            # Recreate compact products atomically; physical calls remain append-only.
            for name, rows in [("d0_answers.jsonl", answers), ("d0_controls.jsonl", controls), ("d0_judge_batches.jsonl", judge_batches)]:
                (args.run_dir / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    finally:
        backend.unload()

    verdict_by_id = {row["id"]: row for batch in judge_batches for row in batch["parsed"]}
    by_anon = {row["anonymous_id"]: row for row in answers}
    blind_rows, key_rows = [], []
    for position, anonymous_id in enumerate(stable_order(list(by_anon), seed=43), 1):
        row = by_anon[anonymous_id]
        blind_rows.extend([f"### {position}. {anonymous_id}", "", f"问题：{row['question']}", "", f"参考答案：{row['reference_answer']}", "",
                           f"匿名预测：{row['parsed']['answer'] or '[No parseable answer]'}", "", "人工判断（correct / incorrect / uncertain）：______", "", "理由：______", ""])
        key_rows.append({"anonymous_id": anonymous_id, "question_id": row["question_id"], "condition": row["condition"],
                         "automatic_judge": verdict_by_id[anonymous_id], "human_verdict": None})
    (args.run_dir / "d0_human_blind_audit.md").write_text("# D0：32 条匿名答案人工核验\n\n请先独立填答，再与独立保存的自动判分对照。此表不显示条件或自动判分。审核尚未进行。\n\n" + "\n".join(blind_rows))
    (args.run_dir / "d0_judge_calibration_key.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in key_rows))
    summary = build_summary(args, ledger, list(call_records.values()), answers, controls, judge_batches, manifest)
    print(json.dumps({"state": "D0_model_requests_completed", "ledger": summary["ledger"], "model_errors": summary["model_errors"],
                      "truncated_outputs": summary["truncated_outputs"], "human_calibration": "NOT_RUN", "gpu_unloaded": True}), flush=True)


if __name__ == "__main__":
    main()
