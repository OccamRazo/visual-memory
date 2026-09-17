#!/usr/bin/env python3
"""Validate actual data products, split isolation, image provenance and blinding."""
import argparse
import collections
import json
from pathlib import Path

from prepare import dump, sha
from annotate import read_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--annotation", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    errors, warnings, checks = [], [], {}
    def check(name, ok, detail=None):
        checks[name] = {"passed": bool(ok), "detail": detail}
        if not ok:
            errors.append(name)
    questions = read_jsonl(a.inventory / "questions.jsonl")
    candidates = read_jsonl(a.inventory / "candidates.jsonl")
    videos = read_jsonl(a.inventory / "videos.jsonl")
    probes = read_jsonl(a.inventory / "video_probes.jsonl")
    selection = json.loads((a.inventory / "selection_manifest.json").read_text())
    check("only_videomme_long", all(x["dataset"] == "videomme_long" for x in questions + candidates + videos))
    check("900_questions_300_videos", len(questions) == 900 and len(videos) == 300)
    check("unique_question_ids", len({q["qid"] for q in questions}) == len(questions))
    check("unique_source_ids", len({c["source_id"] for c in candidates}) == len(candidates))
    dev = [q for q in questions if q["qid"] in selection["dev_qids"]]
    other = [q for q in questions if q["qid"] not in selection["dev_qids"]]
    check("dev_60_questions_20_videos", len(dev)==60 and len({q["history_id"] for q in dev})==20)
    check("no_history_leakage", not ({q["history_id"] for q in dev} & {q["history_id"] for q in other}))
    check("pilot_is_dev_subset", len(selection["visual_pilot_qids"])==12 and set(selection["visual_pilot_qids"])<=set(selection["dev_qids"]))
    check("metadata_all_successful", len(probes)==300 and all(p["status"]=="ok" for p in probes))
    check("source_files_present", all(Path(c["video_path"]).is_file() for c in candidates))
    check("caption_text_nonempty", all(c["text"].strip() for c in candidates))
    byvideo = collections.defaultdict(list)
    for c in candidates:
        byvideo[c["video_path"]].append(c)
    durations = {p["path"]:p.get("duration_s") for p in probes}
    timeline_errors = []
    for path, cs in byvideo.items():
        cs.sort(key=lambda c:c["start_s"])
        if cs[0]["start_s"] != 0 or any(abs(x["end_s"]-y["start_s"])>0.001 for x,y in zip(cs,cs[1:])):
            timeline_errors.append(path)
        if durations.get(path) is None or abs(cs[-1]["end_s"]-durations[path])>1.1:
            timeline_errors.append(path)
    check("caption_timeline_and_video_duration", not timeline_errors, timeline_errors)
    check("caption_coverage_all_video_ids", {c["video_id"] for c in candidates} == {v["video_id"] for v in videos})
    if a.annotation:
        drafts = [json.loads(p.read_text()) for p in (a.annotation / "drafts").glob("*.json")]
        visual = [json.loads(p.read_text()) for p in (a.annotation / "visual").glob("*.json")]
        check("all_60_dev_drafts", {d["qid"] for d in drafts} == set(selection["dev_qids"]))
        check("all_12_pilot_outcomes_recorded", {v["qid"] for v in visual} == set(selection["visual_pilot_qids"]))
        check("human_labels_not_fabricated", all(not r["human_reviewed"] for r in drafts + visual))
        frame_errors, blind_errors, timestamp_errors = [], [], []
        checked_frames = 0
        for v in visual:
            if v["status"] != "ok":
                continue
            qdir = v["qid"].replace(":", "__")
            intervals = {s["source_id"]:s for s in v["visual_sources"]}
            frame_times = collections.defaultdict(list)
            for f in v["frames"]:
                checked_frames += 1
                source = intervals[f["source_id"]]
                frame_times[f["source_id"]].append(f["actual_pts_s"])
                if sha(f["path"]) != f["sha256"] or not (source["start_s"]-0.001 <= f["actual_pts_s"] < source["end_s"]):
                    frame_errors.append(f["path"])
            for ob in v["blind_audit"].get("observations", []):
                if any(s not in {x["subtitle_id"] for x in v.get("subtitles",[])} for s in ob.get("subtitle_ids",[])):
                    blind_errors.append(v["qid"]+":unknown_subtitle_id")
                for t in ob.get("frame_times_s", []):
                    if not any(abs(t-actual)<=0.1 for actual in frame_times[ob["source_id"]]):
                        timestamp_errors.append({"qid":v["qid"],"source_id":ob["source_id"],"cited":t})
            request = json.loads((a.annotation/"calls"/qdir/"blind_visual/request_manifest.json").read_text())
            content = request["payload"]["messages"][1]["content"]
            first = json.loads(content[0]["text"])
            if not {"question","source_segments","input_note"} <= set(first) or set(first)-{"question","source_segments","input_note","subtitles"} or any(set(s)!={"source_id","start_s","end_s"} for s in first["source_segments"]):
                blind_errors.append(v["qid"])
            if first.get("subtitles",[]) != v.get("subtitles",[]):
                blind_errors.append(v["qid"]+":subtitle_provenance")
            images = [x for x in content if x["type"]=="image_url"]
            if [x["image_url"]["url"] for x in images] != ["sha256:"+f["sha256"] for f in v["frames"]]:
                blind_errors.append(v["qid"])
        check("frame_hash_and_timestamp_provenance", not frame_errors, {"frames_checked":checked_frames,"errors":frame_errors})
        check("blind_input_excludes_reference_and_captions", not blind_errors, blind_errors)
        # Do not rewrite original model citations. Flag loose timestamps for human review.
        checks["model_citation_timestamp_precision"] = {"passed":not timestamp_errors,"detail":timestamp_errors}
        if timestamp_errors:
            warnings.append("Some model-cited timestamps do not match sampled frame PTS within 0.1s; inspect original audit before accepting support.")
    result = {"passed":not errors,"checks":checks,"errors":errors,"warnings":warnings,"scope":"Data integrity and input isolation only; not human verification or a method result"}
    dump(a.output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
