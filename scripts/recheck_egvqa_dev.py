#!/usr/bin/env python3
"""Repeat fixed dev answers after the recorded format-only prompt calibration.

The 32 answers and eight blind judge batches use 40 requests from the core
reserve. Original D0 outputs are preserved. No controller is called again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from egvqa_pilot import prompts
from egvqa_pilot.model import QwenBackend
from egvqa_pilot.protocol import BudgetLedger, anonymous_judge_batch, fixed_hash_order, parse_answer, parse_control, parse_judge
from run_egvqa_dev import CONDITIONS, append_jsonl, e1_images, load_jsonl, quantiles, utc_now, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--dev-annotations", type=Path, default=Path("data/downloads/egvqa-pilot/annotations/dev.json"))
    parser.add_argument("--final-format-pass", action="store_true", help="Use 40 further reserve calls plus one 8192-token boundary; write dev_final_* artifacts")
    args = parser.parse_args()
    run = args.run_dir
    prefix = "dev_final" if args.final_format_pass else "dev_recheck"
    request_prefix = prefix if args.final_format_pass else "RESERVE-format"
    call_cap = 41 if args.final_format_pass else 40
    initial_ledger_name = "dev_recheck_ledger.json" if args.final_format_pass else "d0_ledger.json"
    artifact = lambda suffix: run / f"{prefix}_{suffix}"
    if args.dev_annotations.name != "dev.json":
        raise ValueError("Recheck is restricted to the fixed dev annotation split")
    selection = json.loads((run / "d0_manifest.json").read_text())
    if selection["annotation_sha256"] != hashlib.sha256(args.dev_annotations.read_bytes()).hexdigest():
        raise ValueError("Fixed dev annotations changed")
    questions = {q["question_id"]: q for video in json.loads(args.dev_annotations.read_text()) for q in video["questions"]}
    frozen_path = artifact("manifest.json")
    frozen = {"frozen_at_utc": utc_now(), "phase": "RESERVE", "physical_request_cap": call_cap,
              "reservation_source": f"{call_cap} of the plan's 100 core reserve calls; no increase to D0=50 or core=1400",
              "d0_manifest_sha256": hashlib.sha256((run / "d0_manifest.json").read_bytes()).hexdigest(),
              "selected_questions": selection["selected_questions"], "conditions": CONDITIONS,
              "prompts": prompts.identity(), "change": "Common answer format: <=30 words, no invented IDs, empty citations without images, <=6 distinct real IDs.",
              "model_generation_limits_unchanged": not args.final_format_pass, "judge_order_seed_rule": "43 + zero-based question position"}
    if args.final_format_pass:
        frozen["change"] = "Final dev adaptation: answer output limit 128; exact allowed visible citation IDs appended to answer text, [] for Blind. Control 96 and judge 256 unchanged."
    if frozen_path.exists():
        old = json.loads(frozen_path.read_text())
        if old["d0_manifest_sha256"] != frozen["d0_manifest_sha256"] or old["prompts"] != frozen["prompts"]:
            raise ValueError("Recheck selection or prompts changed after freeze")
    else:
        write_json(frozen_path, frozen)

    normalized = []
    for old_control in load_jsonl(run / "d0_controls.jsonl"):
        normalized.append({"request_id": old_control["request_id"], "question_id": old_control["question_id"],
                           "method": old_control["method"], "original_output": old_control["output_text"],
                           "original_parse": old_control["parsed"],
                           "normalized_parse": parse_control(old_control["output_text"], questions[old_control["question_id"]]["question"], old_control["method"])})
    normalization_report = {"new_model_calls": 0,
               "rule": "A nonempty single query string is normalized to a one-element query list; no semantic retrieval content changes.",
               "original_parse_failures": sum(not r["original_parse"]["parse_ok"] for r in normalized),
               "normalized_parse_failures": sum(not r["normalized_parse"]["parse_ok"] for r in normalized),
               "normalized_from_string": sum(r["normalized_parse"].get("normalized_from_string", False) for r in normalized), "rows": normalized}
    if not args.final_format_pass:
        write_json(run / "control_normalization_report.json", normalization_report)

    ledger_path, calls_path = artifact("ledger.json"), artifact("calls.jsonl")
    ledger = BudgetLedger.from_records(json.loads((ledger_path if ledger_path.exists() else run / initial_ledger_name).read_text()))
    calls = {row["request_id"]: row for row in load_jsonl(calls_path)}
    for entry in list(ledger.entries.values()):
        if entry.state == "reserved":
            recovered = calls.get(entry.request_id)
            if recovered is None:
                raise RuntimeError("Interrupted request with unknown output: no unregistered model retry is allowed")
            ledger.finalize(entry.request_id, output_tokens=recovered["output_tokens"] if recovered.get("output_tokens_complete", True) else None,
                            error=recovered.get("error") or ("output_truncated" if recovered["truncated"] else None))
    write_json(ledger_path, ledger.records())
    import torch
    torch.set_num_threads(4)
    backend = QwenBackend(cache_dir=run / "model_cache")
    if not args.final_format_pass and backend.identity()["identity_hash"] != json.loads((run / "d0_model_identity.json").read_text())["identity_hash"]:
        raise ValueError("Model/processor/precision/generation identity changed during the format-only recheck")
    if args.final_format_pass:
        if backend.identity()["role_max_new_tokens"] != {"answer": 128, "control": 96, "judge": 256}:
            raise ValueError("Final registered generation limits differ")
        write_json(artifact("model_identity.json"), backend.identity())
        probe = backend.prepare("answer", "Return a short answer.", [])
        decoded = backend.processor.tokenizer.decode(probe.inputs["input_ids"][0], skip_special_tokens=False)
        if not probe.effective_text.endswith("Allowed citation IDs: []") or "Allowed citation IDs: []" not in decoded:
            raise ValueError("Blind citation manifest was not injected in the actual model prompt")
        write_json(artifact("citation_injection_check.json"), {"passed": True, "physical_requests": 0,
                   "effective_user_text": probe.effective_text, "decoded_actual_model_prompt": decoded,
                   "allowed_citation_ids": probe.allowed_citation_ids, "max_new_tokens": probe.max_new_tokens})

    def invoke(request_id, role, text, images, metadata, prepared=None):
        if request_id in calls:
            return calls[request_id]
        if request_id in ledger.entries:
            raise RuntimeError("Recheck request already exists without an output; cannot silently retry")
        if sum(row.request_id.startswith(request_prefix + "-") for row in ledger.entries.values()) >= call_cap:
            raise RuntimeError(f"This registered dev pass is capped at {call_cap} physical requests")
        prepared = prepared or backend.prepare(role, text, images)
        ledger.reserve(request_id=request_id, phase="RESERVE", question_id=metadata["question_id"], method="dev_format_recheck",
                       condition=metadata["condition"], role=role, input_tokens=prepared.input_tokens,
                       max_output_tokens=prepared.max_new_tokens, physical_request=True)
        write_json(ledger_path, ledger.records())
        result = backend.generate(prepared=prepared, request_id=request_id, use_cache=False,
                                  metadata={**metadata, "phase": "RESERVE", "forced_physical_recheck": True})
        append_jsonl(calls_path, result); calls[request_id] = result
        ledger.finalize(request_id, output_tokens=result["output_tokens"] if result.get("output_tokens_complete", True) else None,
                        error=result.get("error") or ("output_truncated" if result["truncated"] else None))
        write_json(ledger_path, ledger.records())
        print(json.dumps({"request_id": request_id, "physical_total": ledger.summary()["physical_calls"], "latency_s": result["latency_s"],
                          "output_tokens": result["output_tokens"], "truncated": result["truncated"], "error": result["error"]}), flush=True)
        return result

    answers, judges = [], []
    try:
        if args.final_format_pass:
            images = []
            for index in range(24):
                pixels = np.full((224, 224, 3), 255, dtype=np.uint8)
                pixels[30:195, 30:195] = [255, 0, 0] if index == 12 else [0, 0, 255]
                images.append({"image": pixels, "id": f"C{index:02}", "pts": float(index)})
            lead = "Synthetic maximum-context boundary test. Ignore the following padding and follow the final instruction:\n"
            tail = '\nEnd of padding. Identify the ID of the image with a red square. Return only JSON with keys "answer" (short string) and "citations" (list of supporting input ID strings).'
            base = backend.prepare("answer", lead + " x" + tail, images)
            pad_count = 8192 - base.max_new_tokens - base.input_tokens + 1
            prepared = backend.prepare("answer", lead + " x" * pad_count + tail, images)
            if prepared.input_tokens != 8064 or prepared.max_new_tokens != 128:
                raise ValueError("Final boundary must reserve exactly 8064 + 128 = 8192 tokens")
            boundary = invoke(prefix + "-boundary-answer", "answer", prepared.text, images,
                              {"question_id": "synthetic-final-boundary", "condition": "max_context_24_images", "synthetic": True}, prepared=prepared)
            boundary_parse = parse_answer(boundary["output_text"], [r["id"] for r in images])
            write_json(artifact("boundary_summary.json"), {"request_id": boundary["request_id"], "input_tokens": prepared.input_tokens,
                       "max_new_tokens": prepared.max_new_tokens, "parsed": boundary_parse, "truncated": boundary["truncated"], "error": boundary["error"],
                       "passed": not boundary["truncated"] and not boundary["error"] and boundary_parse["parse_ok"] and boundary_parse["citations_legal"]})
            if boundary["error"] or boundary["truncated"] or not boundary_parse["parse_ok"] or not boundary_parse["citations_legal"]:
                raise RuntimeError("Final boundary failed; no unregistered retry or further configuration change")
        for index, selected in enumerate(selection["selected_questions"]):
            qid, video_id = selected["question_id"], selected["video_id"]
            question = questions[qid]
            package_dir = run / "prepared" / video_id / "e1" / qid
            package = json.loads((package_dir / "manifest.json").read_text())
            frozen_video = next(v for v in selection["all_dev_readiness"] if v["video_id"] == video_id)
            frozen_package = next(q for q in frozen_video["questions"] if q["question_id"] == qid)
            if package["package_hash"] != frozen_package["package_hash"]:
                raise ValueError("Dev E1 package changed after original selection freeze")
            with np.load(package_dir / "pixels.npz", allow_pickle=False) as data:
                pixels = data["images"]
            current_answers = []
            for condition in CONDITIONS:
                images = e1_images(package, pixels, condition)
                result = invoke(f"{request_prefix}-{qid}-{condition}", "answer", prompts.ANSWER.format(question=question["question"]), images,
                                {"question_id": qid, "video_id": video_id, "condition": condition, "package_hash": package["package_hash"]})
                anonymous_id = "a" + hashlib.sha256(f"43:{qid}:{condition}".encode()).hexdigest()[:12]
                row = {"question_id": qid, "video_id": video_id, "condition": condition, "anonymous_id": anonymous_id,
                       "question": question["question"], "reference_answer": question["answer"], "request_id": result["request_id"],
                       "output_text": result["output_text"], "parsed": parse_answer(result["output_text"], package["conditions"][condition]["group_ids"]),
                       "truncated": result["truncated"], "error": result["error"]}
                answers.append(row); current_answers.append(row)
            by_anon = {r["anonymous_id"]: r for r in current_answers}
            raw_items = [{"item_id": r["anonymous_id"], "question": question["question"], "reference": question["answer"],
                          "prediction": r["parsed"]["answer"] or "[No parseable answer]"} for r in current_answers]
            items, mapping = anonymous_judge_batch(raw_items, seed=43 + index)
            result = invoke(f"{request_prefix}-{qid}-judge", "judge", prompts.JUDGE.format(items=json.dumps(items, ensure_ascii=False)), [],
                            {"question_id": qid, "video_id": video_id, "condition": "judge", "anonymous_ids": list(mapping)})
            parsed_local = parse_judge(result["output_text"], list(mapping))
            judges.append({"question_id": qid, "request_id": result["request_id"], "anonymous_input": items,
                           "anonymous_mapping": {anon: {"global_anonymous_id": global_id, "condition": by_anon[global_id]["condition"],
                               "answer_request_id": by_anon[global_id]["request_id"]} for anon, global_id in mapping.items()},
                           "output_text": result["output_text"], "parsed_local_ids": parsed_local,
                           "parsed": [{**r, "id": mapping[r["id"]], "judge_local_id": r["id"]} for r in parsed_local]})
            for suffix, rows in [("answers.jsonl", answers), ("judge_batches.jsonl", judges)]:
                artifact(suffix).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    finally:
        backend.unload()

    verdicts = {r["id"]: r for batch in judges for r in batch["parsed"]}
    by_anon = {r["anonymous_id"]: r for r in answers}
    blind, key_rows = [], []
    for index, anonymous_id in enumerate(fixed_hash_order(by_anon, seed=43), 1):
        row = by_anon[anonymous_id]
        blind.extend([f"### {index}. {anonymous_id}", "", f"问题：{row['question']}", "", f"参考答案：{row['reference_answer']}", "",
                      f"匿名预测：{row['parsed']['answer'] or '[No parseable answer]'}", "", "人工判断（correct / incorrect / uncertain）：______", "", "理由：______", ""])
        key_rows.append({"anonymous_id": anonymous_id, "question_id": row["question_id"], "condition": row["condition"],
                         "automatic_judge": verdicts[anonymous_id], "human_verdict": None})
    artifact("human_blind_audit.md").write_text("# Dev 格式复核：32 条匿名答案人工核验\n\n本表隐藏条件与自动判分。请先独立填答，再与独立保存的自动判分对照。人工审核尚未进行。\n\n" + "\n".join(blind))
    artifact("judge_calibration_key.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in key_rows))
    old_summary = json.loads((run / "d0_summary.json").read_text())
    categories = {"answer_with_images": [r for r in calls.values() if r["role"] == "answer" and r["visual_tokens"] and not r["metadata"].get("synthetic")],
                  "answer_blind": [r for r in calls.values() if r["role"] == "answer" and not r["visual_tokens"]],
                  "judge": [r for r in calls.values() if r["role"] == "judge"],
                  "boundary": [r for r in calls.values() if r["metadata"].get("synthetic")]}
    profile = {name: {"latency_s": quantiles([r["latency_s"] for r in rows]),
                      "generation_s": quantiles([r["generation_s"] for r in rows if "generation_s" in r]),
                      "peak_cuda_reserved_bytes": max((r.get("peak_cuda_reserved_bytes", 0) for r in rows), default=0)} for name, rows in categories.items()}
    scores = {}
    for condition in CONDITIONS:
        rows = [r for r in answers if r["condition"] == condition]
        correct = sum(verdicts[r["anonymous_id"]]["verdict"] == "correct" and r["parsed"]["parse_ok"] and not r["truncated"] and not r["error"] for r in rows)
        scores[condition] = {"n": len(rows), "correct": correct, "accuracy_uncertain_as_zero": correct / len(rows),
                             "original_d0_correct": old_summary["local_judge_pilot_scores_unvalidated"][condition]["correct"]}
    summary = {"completed_at_utc": utc_now(), "status": "COMPLETE" if len(calls) == call_cap else "INCOMPLETE",
               "new_physical_requests": len(calls), "ledger": ledger.summary(), "core_reserve_used_by_this_recheck": call_cap,
               "original_d0_preserved": True, "same_8_dev_questions_and_packages": True,
               "model_errors": sum(bool(r["error"]) for r in calls.values()), "truncated_outputs": sum(r["truncated"] for r in calls.values()),
               "answer_parse_failures": sum(not r["parsed"]["parse_ok"] for r in answers),
               "answer_invalid_or_illegal_citations": sum(not r["parsed"]["citations_legal"] for r in answers),
               "judge_item_parse_failures": sum(not r["parse_ok"] for batch in judges for r in batch["parsed"]),
               "control_normalization_new_calls": 0, "control_parse_failures_after_normalization": sum(not r["normalized_parse"]["parse_ok"] for r in normalized),
               "profile": profile, "local_judge_pilot_scores_unvalidated": scores,
               "human_judge_calibration": {"status": "NOT_RUN", "required_agreement": "at least 28/32", "observed_agreement": None},
               "gpu_unloaded": True, "prompt_identity": prompts.identity(), "d0_gate_passed": False,
               "gate_note": "Format-only dev validation does not replace human judge calibration or other D0 scientific gates."}
    summary["format_validation_passed"] = (summary["model_errors"] == summary["truncated_outputs"] == summary["answer_parse_failures"] == summary["answer_invalid_or_illegal_citations"] == summary["judge_item_parse_failures"] == 0)
    write_json(artifact("summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
