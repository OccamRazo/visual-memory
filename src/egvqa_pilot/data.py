"""CPU video front end and privileged E1 package construction.

The writer API takes only a video, source ID and fixed front-end parameters.
Audit records are deliberately outside the reader's snapshot directory.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Iterable

import av
import numpy as np
from PIL import Image

from .protocol import merge_evidence_intervals

SLOT_BYTES = 640 * 1024
GLOBAL_BYTES = 64 * 1024
SIDE = 224
FRAMES = 4


def json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(json_bytes(value) + b"\n")
    temp.replace(path)


def letterbox(image: Image.Image | np.ndarray) -> np.ndarray:
    image = Image.fromarray(image) if isinstance(image, np.ndarray) else image
    image = image.convert("RGB")
    scale = min(SIDE / image.width, SIDE / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    image = image.resize(size, Image.Resampling.BICUBIC)
    canvas = Image.new("RGB", (SIDE, SIDE), (0, 0, 0))
    canvas.paste(image, ((SIDE - size[0]) // 2, (SIDE - size[1]) // 2))
    return np.asarray(canvas, dtype=np.uint8).copy()


def equidistant_indices(length: int, count: int = 4) -> list[int]:
    if length < count:
        return list(range(length))
    return [round(i * (length - 1) / (count - 1)) for i in range(count)]


@dataclass
class Capsule:
    metadata: dict
    images: np.ndarray


class ReservoirWriter:
    """Algorithm R; final stream length and questions are absent from this API."""

    def __init__(self, source_id: str, k: int = 64, seed: int = 17):
        if k not in (32, 64):
            raise ValueError("Only preregistered K=32/64 are supported")
        self.source_id, self.k, self.seed = source_id, k, seed
        self.rng = random.Random(seed)
        self.seen = 0
        self.slots: list[Capsule] = []

    def update(self, capsule: Capsule) -> None:
        if capsule.images.shape != (4, SIDE, SIDE, 3) or capsule.images.dtype != np.uint8:
            raise ValueError("Invalid capsule pixels")
        # Reserve a float32 CLIP-B/32 key even before GPU encoding.
        if capsule.images.nbytes + len(json_bytes(capsule.metadata)) + 512 * 4 > SLOT_BYTES:
            raise ValueError("Persistent slot budget exceeded")
        self.seen += 1
        if len(self.slots) < self.k:
            self.slots.append(capsule)
        else:
            index = self.rng.randrange(self.seen)
            if index < self.k:
                self.slots[index] = capsule

    def prefix_hash(self) -> str:
        return hashlib.sha256(json_bytes({"seen": self.seen, "slots": [c.metadata for c in self.slots]})).hexdigest()


def _make_capsule(source_id: str, index: int, frames: list, end: float | None = None) -> Capsule:
    selected = [frames[i] for i in equidistant_indices(len(frames))]
    images = [letterbox(f.to_image()) for _, _, f in selected]
    times = [time for time, _, _ in selected]
    raw_pts = [pts for _, pts, _ in selected]
    valid = [True] * len(images)
    hashes = [hashlib.sha256(x.tobytes()).hexdigest() for x in images]
    while len(images) < 4:
        images.append(images[-1].copy())
        times.append(times[-1])
        raw_pts.append(raw_pts[-1])
        valid.append(False)
        hashes.append(None)
    metadata = {"capsule_id": f"c{index:06d}", "source_id": source_id,
                "interval": [2.0 * index, min(2.0 * (index + 1), end) if end is not None else 2.0 * (index + 1)],
                "pts": times, "raw_pts": raw_pts, "valid_mask": valid,
                "frame_hashes": hashes, "decoded_frames": len(frames)}
    return Capsule(metadata, np.stack(images))


def _save_pixels(path: Path, images: np.ndarray, keys: np.ndarray | None = None) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("wb") as f:
        if keys is None:
            np.savez(f, images=images)
        else:
            np.savez(f, images=images, keys=keys)
    temp.replace(path)


def validate_snapshot_budget(snapshot_dir: Path, manifest: dict | None = None) -> dict:
    manifest = manifest or json.loads((snapshot_dir / "manifest.json").read_text())
    with np.load(snapshot_dir / manifest["pixels_file"], allow_pickle=False) as payload:
        images = payload["images"]
        keys = payload["keys"] if "keys" in payload else None
        if len(images) != len(manifest["capsules"]) or len(images) > manifest["k"]:
            raise ValueError("Snapshot slot count mismatch")
        for i, capsule in enumerate(manifest["capsules"]):
            key_bytes = keys[i].nbytes if keys is not None else 2048
            if images[i].nbytes + key_bytes + len(json_bytes(capsule)) > SLOT_BYTES:
                raise ValueError("Snapshot slot exceeds 640 KiB")
    global_data = {k: v for k, v in manifest.items() if k != "capsules"}
    if len(json_bytes(global_data)) > GLOBAL_BYTES:
        raise ValueError("Global metadata exceeds 64 KiB")
    actual = sum(p.stat().st_size for p in snapshot_dir.rglob("*") if p.is_file())
    limit = manifest["k"] * SLOT_BYTES + GLOBAL_BYTES
    if actual > limit:
        raise ValueError(f"Snapshot actual bytes {actual} exceed {limit}")
    return {"actual_bytes": actual, "byte_limit": limit, "slots": len(manifest["capsules"])}


def prepare_video(video_path: str | Path, video_id: str, out_dir: str | Path,
                  seed: int = 17, k: int = 64) -> dict:
    """Write <out>/snapshot/{manifest.json,pixels.npz} and privileged audit metadata."""
    video_path, out_dir = Path(video_path), Path(out_dir)
    snapshot_dir, audit_dir = out_dir / "snapshot", out_dir / "audit"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    writer = ReservoirWriter(video_id, k, seed)
    candidates, frame_times, prefix_hashes = [], [], []
    current, current_index, last_time = [], None, None
    duplicates = missing_pts = 0

    def consume(index, frames, end=None):
        capsule = _make_capsule(video_id, index, frames, end)
        writer.update(capsule)
        candidates.append(capsule.metadata)
        prefix_hashes.append({"capsule_id": capsule.metadata["capsule_id"], "writer_prefix_hash": writer.prefix_hash()})

    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        stream.thread_count = 2
        time_base = str(stream.time_base)
        metadata = {"width": stream.width, "height": stream.height,
                    "average_rate": str(stream.average_rate), "time_base": time_base,
                    "container_duration_seconds": container.duration / av.time_base if container.duration else None,
                    "stream_duration_seconds": float(stream.duration * stream.time_base) if stream.duration else None,
                    "codec": stream.codec_context.name}
        last_duration = 0.0
        for frame in container.decode(stream):
            if frame.pts is None:
                missing_pts += 1
                continue
            time = float(frame.pts * frame.time_base)
            if not math.isfinite(time) or time < 0:
                raise ValueError(f"Unsupported negative/nonfinite PTS: {time}")
            if last_time is not None and time < last_time:
                raise ValueError("Decoded frame PTS are not monotonic")
            if time == last_time:
                duplicates += 1
                continue
            index = math.floor(time / 2)
            if current and index != current_index:
                consume(current_index, current)
                current = []
            current_index = index
            current.append((time, int(frame.pts), frame))
            frame_times.append({"time": time, "pts": int(frame.pts)})
            last_time = time
            last_duration = float(frame.duration * frame.time_base) if frame.duration else 0.0
        if not current:
            raise ValueError("No usable decoded video frames")
        end = last_time + last_duration
        if end <= last_time:
            end = last_time + (1 / float(stream.average_rate) if stream.average_rate else 1e-6)
        consume(current_index, current, end)
    slots = sorted(writer.slots, key=lambda c: c.metadata["capsule_id"])
    images = np.stack([c.images for c in slots])
    source_hash = sha256_file(video_path)
    manifest = {"schema_version": 1, "video_id": video_id, "source_sha256": source_hash,
                "k": k, "seed": seed, "writer": "online_reservoir_algorithm_R_python_random",
                "seen_capsules": writer.seen, "capsule_seconds": 2, "image_shape": [4,224,224,3],
                "pixel_dtype": "uint8", "letterbox": "Pillow.BICUBIC_black_center_round",
                "pts_time_base": time_base, "pixels_file": "pixels.npz", "keys_status": "pending",
                "slot_byte_limit": SLOT_BYTES, "global_byte_limit": GLOBAL_BYTES,
                "capsules": [c.metadata for c in slots]}
    manifest["snapshot_hash"] = hashlib.sha256(json_bytes(manifest) + images.tobytes()).hexdigest()
    _save_pixels(snapshot_dir / "pixels.npz", images)
    write_json(snapshot_dir / "manifest.json", manifest)
    budget = validate_snapshot_budget(snapshot_dir, manifest)
    write_json(audit_dir / "candidates.json", candidates)
    write_json(audit_dir / "frame_times.json", frame_times)
    write_json(audit_dir / "prefix_hashes.json", prefix_hashes)
    probes = [frame_times[i] for i in sorted(set([0, len(frame_times)//2, len(frame_times)-1]))]
    report = {"video_id": video_id, "source_sha256": source_hash, "decode_status": "complete",
              "media": metadata, "unique_frames": len(frame_times), "duplicate_pts_dropped": duplicates,
              "missing_pts_dropped": missing_pts, "start_middle_end": probes,
              "actual_end_seconds": end, "candidate_capsules": writer.seen,
              "snapshot_hash_before_keys": manifest["snapshot_hash"], **budget}
    write_json(audit_dir / "decode_report.json", report)
    return report


def add_snapshot_keys(snapshot_dir: str | Path, keys: np.ndarray, encoder_metadata: dict) -> dict:
    snapshot_dir = Path(snapshot_dir)
    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    with np.load(snapshot_dir / "pixels.npz", allow_pickle=False) as f:
        images = f["images"]
    keys = np.asarray(keys, dtype=np.float32)
    if keys.shape != (len(images), 512) or not np.isfinite(keys).all():
        raise ValueError("Expected finite K x 512 CLIP-B/32 keys")
    if not np.allclose(np.linalg.norm(keys, axis=1), 1, atol=1e-4):
        raise ValueError("Keys must be normalized")
    manifest.update(keys_status="ready", encoder=encoder_metadata, key_dtype="float32", key_shape=list(keys.shape))
    manifest.pop("snapshot_hash", None)
    manifest["snapshot_hash"] = hashlib.sha256(json_bytes(manifest) + images.tobytes() + keys.tobytes()).hexdigest()
    _save_pixels(snapshot_dir / "pixels.npz", images, keys)
    write_json(snapshot_dir / "manifest.json", manifest)
    validate_snapshot_budget(snapshot_dir, manifest)
    return manifest


def _outside(time: float, intervals: list) -> bool:
    return not any(start <= time < end for start, end in intervals)


def plan_e1_question(question: dict, frame_times: list[dict], video_id: str) -> dict:
    """Select true PTS without using decoded pixels or model outcomes."""
    qid = str(question["question_id"])
    intervals = merge_evidence_intervals([x["timestamp"] for x in question["evidence"]])
    result = {"schema_version": 1, "frontend_revision": "e1-v2-disjoint-time-regions", "question_id": qid, "video_id": video_id,
              "gold_groups": intervals, "human_audit_status": "pending",
              "visual_resolution_status": "pending", "independent_facts_status": "pending",
              "distractor_validity_status": "pending", "construction_status": "invalid", "reasons": []}
    if not 2 <= len(intervals) <= 4:
        result["reasons"].append("merged_group_count_outside_2_to_4")
        return result
    times = [x["time"] for x in frame_times]
    groups = []
    for interval in intervals:
        available = [i for i,t in enumerate(times) if interval[0] <= t < interval[1]]
        if len(available) < 4:
            result["reasons"].append("evidence_group_has_fewer_than_four_distinct_pts")
            return result
        groups.append([available[i] for i in equidistant_indices(len(available))])
    # Candidate distractors have the same target span as a typical gold group.
    # Restrict all four real PTS to a single evidence-free contiguous region.
    target_span = float(np.median([b-a for a,b in intervals]))
    outside_runs, run = [], []
    for i,t in enumerate(times):
        if _outside(t, intervals):
            run.append(i)
        elif run:
            outside_runs.append(run); run=[]
    if run: outside_runs.append(run)
    distractors=[]
    remaining=[run for run in outside_runs if len(run)>=4]
    # Recompute after each choice, reserving sufficient *whole time regions*
    # for the remaining groups. A four-frame fallback makes enumeration complete
    # whenever these regions contain at least three groups of four real PTS.
    for choice_index in range(3):
        candidates=[]
        for run_index,run in enumerate(remaining):
            step=max(1,len(run)//64)
            for start in sorted(set(range(0,len(run)-3,step))|{0,len(run)-4}):
                stop=start+3
                while stop+1<len(run) and times[run[stop+1]]-times[run[start]]<=target_span:
                    stop+=1
                stops={stop,start+3,min(len(run)-1,start+max(4,len(run)//2)-1),
                       min(len(run)-1,start+max(4,len(run)//3)-1)}
                for end in stops:
                    leftover=remaining[:run_index]+remaining[run_index+1:]+[run[:start],run[end+1:]]
                    leftover=[part for part in leftover if len(part)>=4]
                    if sum(len(part)//4 for part in leftover)<2-choice_index:continue
                    window=run[start:end+1]
                    selected=[window[j] for j in equidistant_indices(len(window))]
                    rank=(abs(times[selected[-1]]-times[selected[0]]-target_span),
                          hashlib.sha256(json_bytes([17,qid,selected])).hexdigest())
                    candidates.append((rank,selected,leftover))
        if not candidates:break
        _,selected,remaining=min(candidates,key=lambda item:item[0])
        distractors.append(selected)
    if len(distractors) != 3:
        result["reasons"].append("fewer_than_three_disjoint_distractor_groups")
        return result
    groups += distractors
    rows=[]
    for image_index,indices in enumerate(groups):
        pts = [times[i] for i in indices]
        group_id = "g"+hashlib.sha256(json_bytes([video_id,qid,pts])).hexdigest()[:12]
        rows.append({"group_id":group_id,"source_id":video_id,"pts":pts,
                     "raw_pts":[frame_times[i]["pts"] for i in indices],"valid_mask":[True]*4,
                     "frame_indices":indices,"image_index":image_index})
    m=len(intervals); full=[r["group_id"] for r in rows[:-1]]; replacement=rows[-1]["group_id"]
    by_id={r["group_id"]:r for r in rows}
    def condition(ids,removed=None):
        ordered=sorted(ids,key=lambda x:(by_id[x]["pts"][0],x))
        return {"group_ids":ordered,"num_images":4*len(ordered),"replaced_group_id":removed,
                "replacement_group_id":replacement if removed else None}
    conditions={"Full":condition(full)}
    for i in range(m):
        conditions[f"Key-{i+1}"]=condition([replacement if x==full[i] else x for x in full],full[i])
    for j in range(2):
        old=full[m+j]
        conditions[f"Irrel-{j+1}"]=condition([replacement if x==old else x for x in full],old)
    conditions["Blind"]={"group_ids":[],"num_images":0,"replaced_group_id":None,"replacement_group_id":None}
    result.update(construction_status="constructed_pending_human_audit",groups=rows,conditions=conditions,
                  distractor_selection={"seed":17,"target_span":target_span,
                    "rule":"evidence_free_disjoint_time_regions_span_match_then_hash_with_capacity_reservation",
                    "visual_category_matching":"not_performed_human_audit_pending"})
    return result


def apply_e1_duplicate_gate(plan: dict) -> dict:
    """Reject mechanically detectable hidden copies; semantic audit stays pending."""
    if not plan.get("groups"):
        return plan
    groups={g["group_id"]:g for g in plan["groups"]}
    failures=[]
    for name,condition in plan["conditions"].items():
        removed=condition.get("replaced_group_id")
        if not removed:continue
        removed_hashes=set(groups[removed]["frame_hashes"])
        retained={h for gid in condition["group_ids"] for h in groups[gid]["frame_hashes"]}
        overlaps=sorted(removed_hashes.intersection(retained))
        if overlaps:failures.append({"condition":name,"surviving_removed_frame_hashes":overlaps})
    plan["mechanical_duplicate_check"]={"revision":"removed-frame-hash-v1",
                                         "status":"failed" if failures else "passed","failures":failures}
    if failures:
        plan["construction_status"]="invalid"
        if "removed_frame_hash_survives_intervention" not in plan["reasons"]:
            plan["reasons"].append("removed_frame_hash_survives_intervention")
    plan.pop("package_hash",None)
    plan["package_hash"]=hashlib.sha256(json_bytes(plan)).hexdigest()
    return plan


def prepare_e1_video(video_path: str | Path, video_id: str, questions: list[dict], out_dir: str | Path) -> list[dict]:
    """Separate privileged pass; never modifies or reads snapshot pixels/keys."""
    out_dir, video_path = Path(out_dir), Path(video_path)
    e1_dir=out_dir/"e1"
    existing=list(e1_dir.glob("*/manifest.json")) if e1_dir.exists() else []
    current_revision=all(json.loads(p.read_text()).get("frontend_revision")=="e1-v2-disjoint-time-regions" for p in existing)
    if existing and current_revision and len(existing)==len(questions):
        plans=[]
        for path in sorted(existing):
            plan=apply_e1_duplicate_gate(json.loads(path.read_text()))
            write_json(path,plan);plans.append(plan)
        return plans
    if existing and not current_revision:
        archive=out_dir/"e1-frontend-v1"
        if archive.exists():
            raise ValueError("Refusing to overwrite archived historical E1 preparation")
        e1_dir.rename(archive)
    frame_times = json.loads((out_dir / "audit/frame_times.json").read_text())
    plans=[plan_e1_question(q,frame_times,video_id) for q in questions]
    needed={idx for p in plans for row in p.get("groups",[]) for idx in row["frame_indices"]}
    images={}
    with av.open(str(video_path)) as container:
        stream=container.streams.video[0]; stream.thread_count=2
        last=None; index=-1
        for frame in container.decode(stream):
            if frame.pts is None: continue
            time=float(frame.pts*frame.time_base)
            if time==last: continue
            last=time; index+=1
            if index in needed:
                if time != frame_times[index]["time"] or int(frame.pts) != frame_times[index]["pts"]:
                    raise ValueError("PTS changed between writer and E1 decode")
                images[index]=letterbox(frame.to_image())
    if set(images) != needed:
        raise ValueError("Missing selected E1 frames")
    e1_dir.mkdir(parents=True,exist_ok=True)
    for plan in plans:
        qdir=e1_dir/plan["question_id"];qdir.mkdir(parents=True,exist_ok=True)
        if plan.get("groups"):
            payload=[]
            for row in plan["groups"]:
                group=np.stack([images[i] for i in row["frame_indices"]]);payload.append(group)
                row["frame_hashes"]=[hashlib.sha256(x.tobytes()).hexdigest() for x in group]
                row["distinct_pixel_hashes"]=len(set(row["frame_hashes"]))
                row.pop("frame_indices")
            _save_pixels(qdir/"pixels.npz",np.stack(payload))
            plan["pixels_file"]="pixels.npz"
            duplicate_pairs=[]
            for i,left in enumerate(plan["groups"]):
                for right in plan["groups"][i+1:]:
                    if set(left["frame_hashes"])==set(right["frame_hashes"]):
                        duplicate_pairs.append([left["group_id"],right["group_id"]])
            plan["exact_duplicate_visual_group_pairs"]=duplicate_pairs
            for name,condition in plan["conditions"].items():
                rows={r["group_id"]:r for r in plan["groups"]}
                condition["input_hash"]=hashlib.sha256(json_bytes([rows[x] for x in condition["group_ids"]])).hexdigest()
        apply_e1_duplicate_gate(plan)
        plan["package_hash"]=hashlib.sha256(json_bytes({k:v for k,v in plan.items() if k!="package_hash"})).hexdigest()
        write_json(qdir/"manifest.json",plan)
    return plans
