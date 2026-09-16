#!/usr/bin/env python3
"""Prepare query-hidden snapshots and separate privileged E1 packages as data arrives."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from egvqa_pilot.data import prepare_video, prepare_e1_video, sha256_file, write_json


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--dataset-root",type=Path,default=Path("data/downloads/egvqa-pilot"))
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--workers",type=int,default=4)
    parser.add_argument("--watch",action="store_true")
    parser.add_argument("--max-wait-seconds",type=float,default=7200)
    parser.add_argument("--k",type=int,choices=(32,64),default=64)
    args=parser.parse_args(argv)
    manifest=json.loads((args.dataset_root/"manifest.json").read_text())
    records={r["record"]["video_id"]:r for r in manifest["videos"]}
    args.output.mkdir(parents=True,exist_ok=True)
    status={"planned_videos":len(records),"videos":{},"k":args.k,"seed":17}
    waiting=set(records);writing={};packing={};start=time.monotonic()
    def save():write_json(args.output/"preparation_status.json",status)
    # Spawned writer processes receive only paths/IDs/fixed parameters. The E1
    # pool receives annotations after snapshots are sealed and is separate.
    context=mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=max(1,args.workers//2),mp_context=context) as writers, \
         ProcessPoolExecutor(max_workers=max(1,args.workers-args.workers//2),mp_context=context) as privileged:
        while waiting or writing or packing:
            for video_id in sorted(waiting):
                row=records[video_id];record=row["record"]
                video=args.dataset_root/record["video_path"]
                receipt=args.dataset_root/"cache/receipts"/(video.name+".json")
                if not video.exists() or not receipt.exists():continue
                marker=json.loads(receipt.read_text())
                if "sha256" not in marker:continue
                if sha256_file(video)!=marker["sha256"]:
                    status["videos"][video_id]={"status":"error","error":"video_receipt_sha256_mismatch"}
                    waiting.remove(video_id);continue
                dest=args.output/video_id
                waiting.remove(video_id)
                existing=dest/"audit/decode_report.json"
                if existing.exists() and (dest/"snapshot/manifest.json").exists():
                    report=json.loads(existing.read_text())
                    snapshot=json.loads((dest/"snapshot/manifest.json").read_text())
                    if snapshot["k"]!=args.k or report["source_sha256"]!=marker["sha256"]:
                        raise ValueError("Existing preparation configuration/source mismatch")
                    status["videos"][video_id]={"status":"snapshot_ready","role":row["role"],"decode":report}
                    packing[privileged.submit(prepare_e1_video,video,video_id,record["questions"],dest)]=video_id
                else:
                    status["videos"][video_id]={"status":"writing","role":row["role"]}
                    writing[writers.submit(prepare_video,video,video_id,dest,17,args.k)]=video_id
                print(f"QUEUED {row['role']} {video_id}",flush=True);save()
            for future,video_id in list(writing.items()):
                if not future.done():continue
                del writing[future]
                try:
                    report=future.result();row=records[video_id];record=row["record"]
                    status["videos"][video_id].update(status="snapshot_ready",decode=report)
                    packing[privileged.submit(prepare_e1_video,args.dataset_root/record["video_path"],video_id,
                                               record["questions"],args.output/video_id)]=video_id
                    print(f"SNAPSHOT_READY {video_id} {report['slots']} slots {report['actual_bytes']} bytes",flush=True)
                except Exception as exc:
                    status["videos"][video_id].update(status="error",error=repr(exc))
                    print(f"ERROR {video_id} {exc!r}",flush=True)
                save()
            for future,video_id in list(packing.items()):
                if not future.done():continue
                del packing[future]
                try:
                    plans=future.result()
                    count=sum(p["construction_status"]=="constructed_pending_human_audit" for p in plans)
                    status["videos"][video_id].update(status="complete",e1_constructed=count,e1_planned=len(plans),
                                                       human_audit_status="pending")
                    print(f"COMPLETE {video_id} E1 {count}/{len(plans)} audit pending",flush=True)
                except Exception as exc:
                    status["videos"][video_id].update(status="e1_error",error=repr(exc))
                    print(f"E1_ERROR {video_id} {exc!r}",flush=True)
                save()
            if waiting and not args.watch and not writing and not packing:break
            if time.monotonic()-start>args.max_wait_seconds:
                print("Preparation watch deadline reached",flush=True);break
            if waiting or writing or packing:time.sleep(2)
    status["pending_video_ids"]=sorted(waiting)
    status["complete_videos"]=sum(v["status"]=="complete" for v in status["videos"].values())
    save()
    return 0 if status["complete_videos"]==len(records) else 1


if __name__=="__main__":
    raise SystemExit(main())
