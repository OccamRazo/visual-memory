#!/usr/bin/env python3
"""Run the two pre-registered D0 boundary calls with a durable quota ledger.

These synthetic checks exercise 24 images and the full 8192-token reservation;
they are not scientific answers and do not replace the 48 real dev requests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egvqa_pilot.model import QwenBackend
from egvqa_pilot.protocol import BudgetLedger, parse_answer, parse_control


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--model-path", default="/root/autodl-tmp/models/Qwen3-VL-8B-Instruct")
    args = parser.parse_args()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = args.run_dir / "boundary_ledger.json"
    calls_path = args.run_dir / "boundary_calls.jsonl"
    if ledger_path.exists():
        raise SystemExit("Boundary ledger already exists; do not silently add or retry D0 physical requests")
    from PIL import Image, ImageDraw
    images = []
    for index in range(24):
        picture = Image.new("RGB", (224, 224), "white")
        draw = ImageDraw.Draw(picture)
        draw.rectangle((30, 30, 194, 194), fill="red" if index == 12 else "blue")
        images.append({"image": picture, "id": f"C{index:02}", "pts": float(index)})
    prompts = {
        "answer": 'Identify the ID of the image with a red square. Return only JSON with keys "answer" (short string) and "citations" (list of supporting input ID strings).',
        "control": 'The question is: What happened before and after the red square? Identify up to two missing temporal observations to retrieve. Do not answer the question. Return only JSON with key "queries", containing one or two short search strings.',
    }
    backend = QwenBackend(args.model_path, cache_dir=args.run_dir / "model_cache")
    write_json(args.run_dir / "model_identity.json", backend.identity())
    ledger = BudgetLedger()
    results = []
    try:
        for role, instruction in prompts.items():
            prefix = "Synthetic maximum-context boundary test. Ignore the following padding when following the final instruction:\n"
            suffix = "\nEnd of padding. Final instruction: " + instruction
            # Include one filler in the baseline: the first token changes the
            # newline boundary, while every additional " x" is exactly one token.
            base = backend.prepare(role, prefix + " x" + suffix, images)
            padding_tokens = backend.max_context_tokens - base.max_new_tokens - base.input_tokens + 1
            prepared = backend.prepare(role, prefix + " x" * padding_tokens + suffix, images)
            if prepared.input_tokens + prepared.max_new_tokens != backend.max_context_tokens:
                raise RuntimeError("Boundary padding did not produce exactly the registered token limit")
            request_id = f"D0-boundary-{role}-1"
            ledger.reserve(request_id=request_id, phase="D0", question_id=f"synthetic-boundary-{role}",
                           method="boundary", condition="max_context_24_images", role=role,
                           input_tokens=prepared.input_tokens, max_output_tokens=prepared.max_new_tokens,
                           physical_request=True)
            write_json(ledger_path, ledger.records())
            result = backend.generate(prepared=prepared, request_id=request_id, use_cache=False,
                                      metadata={"phase": "D0", "condition": "max_context_24_images", "synthetic": True})
            ledger.finalize(request_id, output_tokens=None if result["error"] else result["output_tokens"], error=result["error"])
            write_json(ledger_path, ledger.records())
            result["parsed"] = (parse_answer(result["output_text"], [item["id"] for item in images])
                                if role == "answer" else parse_control(result["output_text"], "What happened before and after the red square?", "R2"))
            with calls_path.open("a") as stream:
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
            results.append(result)
            print(json.dumps({key: result.get(key) for key in ["request_id", "input_tokens", "visual_tokens", "output_tokens", "output_text", "truncated", "error", "generation_s", "latency_s", "peak_cuda_allocated_bytes", "peak_cuda_reserved_bytes", "parsed"]}), flush=True)
    finally:
        backend.unload()
    summary = {"completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "synthetic_boundary_checks": len(results), "remaining_d0_physical_quota": 50 - ledger.summary()["physical_calls"],
               "ledger": ledger.summary(), "passed": all(not r["error"] and not r["truncated"] and r["parsed"]["parse_ok"] for r in results) and len(results) == 2,
               "note": "Two synthetic boundary requests count toward D0=50; 48 real-dev requests remain. GPU unloaded."}
    write_json(args.run_dir / "boundary_summary.json", summary)
    print(json.dumps(summary), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
