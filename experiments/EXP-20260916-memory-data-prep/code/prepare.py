#!/usr/bin/env python3
"""Read-only source inventory, normalized evaluation data and deterministic dev split."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import zipfile
from datetime import datetime

import pyarrow.parquet as pq


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clock_seconds(value):
    s = str(value).zfill(8)
    if not re.fullmatch(r"\d{8}", s):
        raise ValueError(f"Invalid timestamp: {s}")
    hh, mm, ss, cc = (int(s[:2]), int(s[2:4]), int(s[4:6]), int(s[6:]))
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
        raise ValueError(f"Invalid clock: {s}")
    return hh * 3600 + mm * 60 + ss + cc / 100


def rank(seed, value):
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def probe(path):
    p = Path(path)
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name,avg_frame_rate:format=duration", "-of", "json", str(p)], capture_output=True, text=True, timeout=40)
        d = json.loads(r.stdout)
        if r.returncode or not d.get("streams"):
            raise ValueError("No valid video stream")
        return {"path": str(p), "status": "ok", "duration_s": float(d["format"]["duration"]), **d["streams"][0]}
    except Exception as e:
        return {"path": str(p), "status": "failed", "error_type": type(e).__name__}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    cfg = json.loads(a.config.read_text())
    out = a.output
    if out.exists():
        raise SystemExit("Output already exists; use a separate run directory")
    out.mkdir(parents=True)
    dump(out / "protocol.json", cfg)
    root = Path(cfg["datasets_root"])
    vroot = root / "Video-MME"
    vqa = vroot / "videomme/test-00000-of-00001.parquet"
    zpath = Path(cfg["artifacts_root"]) / "resources/worldmm-videomme-caption.zip"
    rows = [r for r in pq.read_table(vqa).to_pylist() if r["duration"] == "long"]
    vids = sorted({r["videoID"] for r in rows})
    devvids = sorted(vids, key=lambda x: rank(cfg["seed"], "video:" + x))[:cfg["development"]["video_count"]]
    devset = set(devvids)
    questions, candidates, videos, errors = [], [], [], []
    raw_options = lambda opts: {chr(65 + i): re.sub(r"^[A-D][.)]\s*", "", x) for i, x in enumerate(opts)}
    for r in rows:
        opts = raw_options(r["options"])
        questions.append({"qid": "videomme:" + r["question_id"], "dataset": "videomme_long", "original_id": r["question_id"], "history_id": "videomme:" + r["videoID"], "video_id": r["videoID"], "split": "dev" if r["videoID"] in devset else "heldout_pool_unfrozen", "original_question": r["question"], "original_options": opts, "reference_option": r["answer"], "reference_draft": opts[r["answer"]], "official_task_type": r["task_type"], "domain": r["domain"], "sub_category": r["sub_category"], "query_cutoff_s": None, "source": str(vqa), "reference_status": "official_mcq_not_source_verified"})
    with zipfile.ZipFile(zpath) as z:
        capnames = [n for n in z.namelist() if n.endswith("/10sec.json") and not n.startswith("__MACOSX")]
        capids = {n.split("/")[-2] for n in capnames}
        for name in sorted(capnames):
            vid = name.split("/")[-2]
            if vid not in vids:
                continue
            for i, c in enumerate(json.loads(z.read(name))):
                start, end = clock_seconds(c["start_time"]), clock_seconds(c["end_time"])
                path = vroot / "data" / (vid + ".mp4")
                candidates.append({"source_id": f"videomme:{vid}:{i:05}", "dataset": "videomme_long", "history_id": "videomme:" + vid, "video_id": vid, "start_s": start, "end_s": end, "video_path": str(path), "video_offset_start_s": start, "video_offset_end_s": end, "text": c["text"], "caption_source": "WorldMM@3a55b65235e4f9618626a91c28e7e45baa6d8bdf", "caption_modality": "vision_and_transcript_mixed", "original_start_time": c["start_time"], "original_end_time": c["end_time"]})
    for vid in vids:
        p = vroot / "data" / (vid + ".mp4")
        videos.append({"dataset": "videomme_long", "video_id": vid, "history_id": "videomme:" + vid, "path": str(p), "exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else None})
    dev = [q for q in questions if q["split"] == "dev"]
    pilot, seen = [], set()
    for q in sorted(dev, key=lambda q: rank(cfg["seed"], "pilot:" + q["qid"])):
        if q["history_id"] not in seen:
            pilot.append(q["qid"])
            seen.add(q["history_id"])
        if len(pilot) == cfg["visual_pilot"]["question_count"]:
            break
    manifest = {"seed": cfg["seed"], "dev_video_ids": devvids, "dev_qids": [q["qid"] for q in dev], "visual_pilot_qids": pilot, "test_frozen": False}
    dump(out / "selection_manifest.json", manifest)
    jsonl(out / "questions.jsonl", questions)
    jsonl(out / "candidates.jsonl", candidates)
    jsonl(out / "videos.jsonl", videos)
    dump(out / "source_checksums.json", {str(p): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in [vqa, zpath, a.config, Path(__file__)]})
    # Metadata checks cover all long videos.
    probe_paths = [v["path"] for v in videos if v["dataset"] == "videomme_long" and v["exists"]]
    print(f"Inventory: {len(questions)} QA, {len(candidates)} captions; probing {len(probe_paths)} videos", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        probes = list(pool.map(probe, probe_paths))
    jsonl(out / "video_probes.jsonl", probes)
    missing_sources = sorted({c["video_path"] for c in candidates if not Path(c["video_path"]).is_file()})
    invalid_intervals = [c["source_id"] for c in candidates if c["end_s"] <= c["start_s"] or c["video_offset_start_s"] < -0.1]
    summary = {"created_at": datetime.now().astimezone().isoformat(), "host": platform.node(), "python": platform.python_version(), "qa_by_dataset": dict(collections.Counter(q["dataset"] for q in questions)), "video_by_dataset": dict(collections.Counter(v["dataset"] for v in videos)), "captions_by_dataset": dict(collections.Counter(c["dataset"] for c in candidates)), "worldmm_caption_video_count": len(capids), "worldmm_missing_long_ids": sorted(set(vids)-capids), "worldmm_extra_ids": sorted(capids-set(vids)), "dev_questions": len(dev), "dev_videos": len(devvids), "visual_pilot_questions": len(pilot), "missing_video_files": [v["path"] for v in videos if not v["exists"]], "missing_caption_source_files": missing_sources, "invalid_candidate_intervals": invalid_intervals, "target_parse_errors": errors, "video_metadata_probed": len(probes), "video_metadata_failures": [p for p in probes if p["status"] != "ok"], "full_video_decode": "not_run; selected evidence frames are decoded in visual stage", "human_audit": "not_run", "formal_test_selection": "not_frozen"}
    dump(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
