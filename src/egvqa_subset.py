"""Reproducible EG-VQA selection and HTTP Range extraction from its pinned tar."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import time
from typing import Any

import requests


REVISION = "24379571655174cc80e9c1a1603160e6783c6252"
BASE_URL = f"https://huggingface.co/datasets/lphuang33/EG-VQA/resolve/{REVISION}"
ARCHIVE = {
    "url": f"{BASE_URL}/videos.tar",
    "size": 13090641920,
    "sha256": "1e45a98396ef0b5f9e94b0db2b46205528c620be1b073d19cf064f4d7fecd9dc",
}
ANNOTATION_HASHES = {
    "train": "f4992b0d3e239dd3e809b2feecb7bef41f1507153a358c40e9e271ae010622e6",
    "test": "673560f4a3076321f9da8a2b57422fd04cf3645e0bd5aa0a6d8b92427a740f8b",
}
SOURCES = ("ActivityNet Captions", "HiREST", "YouCook2")
ROLES = ("dev", "eval", "train")
CHUNK_SIZE = 4 * 1024 * 1024


class DataError(RuntimeError):
    """An invalid input, incomplete transfer, or unsafe full-file response."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    atomic_bytes(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode())


def safe_video_path(name: str) -> str:
    p = PurePosixPath(name)
    if (len(p.parts) != 2 or p.parts[0] != "videos" or "\\" in name
            or not re.fullmatch(r"[A-Za-z0-9_-]+\.(mp4|mkv|webm|avi|mov)", p.name)):
        raise DataError(f"不支持的视频路径：{name!r}")
    return str(p)


def canonical_id(video: dict) -> str:
    key = video["video_id"]
    return key[2:] if video["data_source"] == "ActivityNet Captions" and key.startswith("v_") else key


def rank_key(seed: int, scope: str, key: str) -> str:
    return digest(f"{seed}:{scope}:{key}".encode())


def stratified_take(rows: list[dict], count: int, field: str, id_field: str,
                    seed: int, scope: str) -> list[dict]:
    """Round-robin strata; stable hashed order does not depend on input order."""
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        groups[row[field]].append(row)
    for group in groups.values():
        group.sort(key=lambda r: rank_key(seed, scope, r[id_field]))
    keys = sorted(groups, key=lambda k: rank_key(seed, scope, k))
    result = []
    while len(result) < count:
        added = False
        for key in keys:
            if groups[key] and len(result) < count:
                result.append(groups[key].pop(0))
                added = True
        if not added:
            raise DataError(f"{scope} 仅有 {len(result)} 个合格候选，少于请求的 {count} 个；请缩小规模或放宽筛选。")
    return result


def load_annotations(root: Path, split: str, annotations_dir: Path | None = None) -> list[dict]:
    path = (annotations_dir or root / "cache") / f"{split}.json"
    if not path.exists():
        if annotations_dir:
            raise DataError(f"缺少离线标注：{path}")
        # Only small annotation files are fetched whole. Never use this for videos.tar.
        print(f"下载 {split}.json 标注（固定版本 {REVISION[:12]}）", flush=True)
        try:
            with requests.get(f"{BASE_URL}/{split}.json", stream=True, timeout=(10, 60)) as response:
                response.raise_for_status()
                parts, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 16 * 1024 * 1024:
                        raise DataError("标注文件超过 16 MiB，停止下载。")
                    parts.append(chunk)
        except requests.RequestException as exc:
            raise DataError(f"标注下载失败（{type(exc).__name__}）；重跑可重试。") from None
        data = b"".join(parts)
        if digest(data) != ANNOTATION_HASHES[split]:
            raise DataError(f"{split}.json SHA-256 与固定版本不符。")
        atomic_bytes(path, data)
    if file_hash(path) != ANNOTATION_HASHES[split]:
        raise DataError(f"{path} SHA-256 与固定版本不符；不会覆盖已有文件。")
    records = read_json(path)
    if not isinstance(records, list):
        raise DataError("标注应为视频记录列表。")
    return records


def valid_evidence(question: dict, duration: float, config: dict) -> bool:
    evidence = question.get("evidence", [])
    if not config["min_evidence"] <= len(evidence) <= config["max_evidence"]:
        return False
    intervals = []
    for item in evidence:
        stamp = item.get("timestamp")
        if not isinstance(stamp, list) or len(stamp) != 2:
            return False
        if not all(isinstance(t, (int, float)) and math.isfinite(t) for t in stamp):
            return False
        start, end = stamp
        if not 0 <= start < end <= duration:
            return False
        intervals.append((start, end))
    # Use the maximum uncovered gap between merged evidence intervals.
    intervals.sort()
    end, gap = intervals[0][1], 0.0
    for start, stop in intervals[1:]:
        gap = max(gap, start - end)
        end = max(end, stop)
    return gap >= config["min_gap_seconds"]


def select_subset(pilot_records: list[dict], train_records: list[dict], config: dict) -> dict:
    def candidates(records: list[dict], weak: bool, excluded: set[str]) -> list[dict]:
        found, seen = [], set(excluded)
        for video in sorted(records, key=lambda v: v["video_id"]):
            duration = video["duration"]
            if (video["data_source"] not in config["sources"]
                    or not config["min_duration"] <= duration <= config["max_duration"]
                    or canonical_id(video) in seen):
                continue
            if weak:
                # Selection and exports for weak training never inspect evidence or captions.
                questions = [q for q in video["questions"] if q.get("question") and q.get("answer")]
                wanted = config["train_questions_per_video"]
            else:
                questions = [q for q in video["questions"]
                             if q.get("question") and q.get("answer")
                             and q.get("type") in config["question_types"]
                             and valid_evidence(q, duration, config)]
                wanted = config["questions_per_video"]
            if len(questions) < wanted:
                continue
            safe_video_path(video["video_path"])
            chosen = copy.deepcopy(video)
            chosen["questions"] = stratified_take(questions, wanted, "type", "question_id",
                                                   config["seed"], video["video_id"])
            found.append(chosen)
            seen.add(canonical_id(video))
        return found

    pool = candidates(pilot_records, False, set())
    pilot = stratified_take(pool, config["num_videos"], "data_source", "video_id", config["seed"], "pilot")
    excluded = {canonical_id(v) for v in pilot}
    train_pool = candidates(train_records, True, excluded) if config["train_videos"] else []
    train = stratified_take(train_pool, config["train_videos"], "data_source", "video_id", config["seed"], "train")
    rows = []
    for i, video in enumerate(pilot):
        rows.append({"role": "dev" if i < config["dev_videos"] else "eval",
                     "source_split": config["split"], "record": video})
    for video in train:
        # Strip gold fields even in the downloadable manifest for this training subset.
        weak = {k: video[k] for k in ("video_id", "video_path", "duration", "data_source")}
        weak["questions"] = [{k: q[k] for k in ("question_id", "question", "answer", "type")}
                             for q in video["questions"]]
        rows.append({"role": "train", "source_split": "train", "record": weak})
    return {
        "schema_version": 1, "dataset": "lphuang33/EG-VQA", "revision": REVISION,
        "archive": ARCHIVE, "annotation_sha256": {
            split: ANNOTATION_HASHES[split] for split in sorted({row["source_split"] for row in rows})
        },
        "selection": config, "eligible_pilot_videos": len(pool), "videos": rows,
    }


def export_views(root: Path, manifest: dict, ready: set[str] | None = None) -> None:
    """Writer inputs contain no questions, titles, source captions, or evidence."""
    for role in ROLES:
        rows = [row["record"] for row in manifest["videos"]
                if row["role"] == role and (ready is None or row["record"]["video_id"] in ready)]
        base = root if ready is None else root / "ready"
        write_json(base / "annotations" / f"{role}.json", rows)
        ingest, questions = [], []
        for video in rows:
            ingest.append({k: video[k] for k in ("video_id", "video_path", "duration")})
            for q in video["questions"]:
                questions.append({"video_id": video["video_id"], **{
                    k: q[k] for k in ("question_id", "question", "type")
                }})
        write_jsonl(base / "inputs" / f"{role}_ingest.jsonl", ingest)
        write_jsonl(base / "inputs" / f"{role}_questions.jsonl", questions)


class RangeReader:
    """Fail closed if Range is ignored; cache redirects only in memory."""

    def __init__(self, url: str, size: int, retries: int = 3, timeout: float = 60):
        self.url, self.size = url, size
        self.resolved_url = url
        self.retries, self.timeout = retries, timeout
        self.session = requests.Session()
        self.bytes_read = 0

    def close(self) -> None:
        self.session.close()

    def read(self, start: int, size: int) -> bytes:
        if start < 0 or size <= 0 or start + size > self.size or size > CHUNK_SIZE:
            raise DataError("非法或过大的字节范围。")
        end = start + size - 1
        expected_range = f"bytes {start}-{end}/{self.size}"
        for attempt in range(self.retries + 1):
            try:
                with self.session.get(self.resolved_url, headers={
                    "Range": f"bytes={start}-{end}", "Accept-Encoding": "identity",
                    "User-Agent": "visual-memory-egvqa-subset/1",
                }, stream=True, timeout=(10, self.timeout)) as response:
                    if response.status_code in (401, 403, 408, 429) or response.status_code >= 500:
                        raise requests.RequestException(f"HTTP {response.status_code}")
                    if response.status_code != 206:
                        raise DataError(f"服务器返回 HTTP {response.status_code} 而非 206；拒绝读取视频包正文。")
                    if response.headers.get("Content-Range") != expected_range:
                        raise DataError("Content-Range 不匹配；拒绝可能的整包或错误区间响应。")
                    if response.headers.get("Content-Encoding", "identity") != "identity":
                        raise DataError("服务器压缩了范围响应，无法保证原始 tar 字节位置。")
                    length = response.headers.get("Content-Length")
                    if length is not None and length != str(size):
                        raise DataError("Content-Length 与请求范围不匹配。")
                    parts, received = [], 0
                    for chunk in response.iter_content(65536):
                        received += len(chunk)
                        if received > size:
                            raise DataError("范围响应正文过长，已中止。")
                        parts.append(chunk)
                    if received != size:
                        raise requests.RequestException("incomplete range")
                    self.resolved_url = response.url
                    self.bytes_read += received
                    return b"".join(parts)
            except requests.RequestException as exc:
                # Signed CDN URLs expire. Refresh via the immutable HF URL on retry.
                self.resolved_url = self.url
                if attempt == self.retries:
                    raise DataError(f"范围下载失败（{type(exc).__name__}，已重试 {self.retries} 次）。") from None
                time.sleep(min(2 ** attempt, 8))
        raise AssertionError("unreachable")


def validate_index(index: dict, archive: dict) -> None:
    if index.get("archive") != archive or index.get("schema_version") != 1:
        raise DataError("视频索引与固定视频包版本不一致。")
    for name, item in index["members"].items():
        safe_video_path(name)
        offset, size = item["offset"], item["size"]
        if not (isinstance(offset, int) and isinstance(size, int)
                and offset >= 512 and offset % 512 == 0 and size > 0
                and offset + size <= archive["size"]):
            raise DataError(f"索引字节位置非法：{name}")


def build_index(reader: RangeReader, archive: dict, needed: set[str], cache_path: Path,
                bundled_path: Path | None = None) -> dict:
    if cache_path.exists():
        index = read_json(cache_path)
    elif bundled_path and bundled_path.exists():
        index = read_json(bundled_path)
    else:
        index = {"schema_version": 1, "archive": archive, "members": {},
                 "next_offset": 0, "complete": False}
    validate_index(index, archive)
    offset = index["next_offset"]
    if not isinstance(offset, int) or offset < 0 or offset % 512 or offset > reader.size:
        raise DataError("索引续扫位置非法。")
    scanned = 0
    try:
        while not needed.issubset(index["members"]) and not index["complete"]:
            if offset + 512 > reader.size:
                raise DataError("tar 缺少结束标记。")
            header = reader.read(offset, 512)
            if header == bytes(512):
                index["complete"] = True
                break
            try:
                member = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
            except (tarfile.HeaderError, UnicodeError) as exc:
                raise DataError("tar 头校验失败；仅支持固定版本的未压缩 videos.tar。") from exc
            # This pinned release has short regular filenames and directories.
            # Reject links, sparse files and extension headers rather than guess offsets.
            if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
                raise DataError(f"当前索引器不支持 tar 成员类型 {member.type!r}：{member.name}")
            if member.isfile():
                name = safe_video_path(member.name)
                if name in index["members"]:
                    raise DataError(f"tar 内有重复路径：{name}")
                if member.size <= 0 or offset + 512 + member.size > reader.size:
                    raise DataError(f"tar 文件长度非法：{name}")
                index["members"][name] = {"offset": offset + 512, "size": member.size}
            offset += 512 + (member.size + 511) // 512 * 512
            index["next_offset"] = offset
            scanned += 1
            if scanned % 25 == 0:
                write_json(cache_path, index)
                found = len(needed.intersection(index["members"]))
                print(f"已扫描 {len(index['members'])} 个视频头，定位所选视频 {found}/{len(needed)}；未读取其他视频正文。", flush=True)
    finally:
        write_json(cache_path, index)
    missing = needed.difference(index["members"])
    if missing:
        raise DataError(f"视频包缺少 {len(missing)} 个所选文件：{', '.join(sorted(missing)[:5])}")
    return index


def download_member(reader: RangeReader, root: Path, name: str, member: dict,
                    archive: dict) -> dict:
    """Resume at verified chunk boundaries; publish only complete files."""
    name = safe_video_path(name)
    path = root / name
    partial = path.with_name(path.name + ".part")
    marker_path = root / "cache" / "receipts" / (path.name + ".json")
    identity = {"archive": archive, "path": name, **member}
    marker = read_json(marker_path) if marker_path.exists() else None
    if marker and marker.get("identity") != identity:
        raise DataError(f"已有文件收据的源版本不符：{name}")
    if path.exists():
        if not marker or "sha256" not in marker:
            raise DataError(f"已有视频缺少校验收据：{name}；请移走该文件后重跑。")
        if path.stat().st_size != member["size"] or file_hash(path) != marker["sha256"]:
            raise DataError(f"已有视频校验失败：{name}；请移走损坏文件后重跑。")
        return {"status": "ok", "path": name, "bytes": member["size"],
                "sha256": marker["sha256"], "reused": True}
    if partial.exists() and not marker:
        raise DataError(f"已有部分文件缺少来源收据：{partial.name}；请移走后重跑。")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not marker:
        write_json(marker_path, {"identity": identity})
    completed = partial.stat().st_size if partial.exists() else 0
    if completed > member["size"]:
        raise DataError(f"部分文件长度超过标注大小：{name}")
    with partial.open("ab") as output:
        while completed < member["size"]:
            # A failed HTTP request cannot append an unverified half chunk.
            chunk = reader.read(member["offset"] + completed,
                                min(CHUNK_SIZE, member["size"] - completed))
            output.write(chunk)
            output.flush()
            completed += len(chunk)
    sha = file_hash(partial)
    write_json(marker_path, {"identity": identity, "sha256": sha})
    partial.replace(path)
    return {"status": "ok", "path": name, "bytes": completed, "sha256": sha, "reused": False}


def download_subset(root: Path, manifest: dict, retries: int = 3, timeout: float = 60,
                    bundled_path: Path | None = None) -> int:
    archive = manifest["archive"]
    reader = RangeReader(archive["url"], archive["size"], retries, timeout)
    status = {"revision": manifest["revision"], "manifest_sha256": file_hash(root / "manifest.json"),
              "requests_version": requests.__version__, "python_version": sys.version.split()[0], "videos": {}}
    ready: set[str] = set()
    # Clear stale ready exports before validating files on each invocation.
    export_views(root, manifest, ready)
    try:
        needed = {safe_video_path(row["record"]["video_path"]) for row in manifest["videos"]}
        index = build_index(reader, archive, needed, root / "cache" / "videos.index.json", bundled_path)
        total_bytes = sum(index["members"][name]["size"] for name in needed)
        print(f"只下载 {len(needed)} 个完整视频，共 {total_bytes / 1024**2:.1f} MiB；整包 {reader.size / 1024**3:.2f} GiB。", flush=True)
        status["planned_bytes"] = total_bytes
        for i, row in enumerate(manifest["videos"], 1):
            video = row["record"]
            key, name = video["video_id"], video["video_path"]
            print(f"[{i}/{len(needed)}] {row['role']} {name}", flush=True)
            try:
                if not (root / name).exists():
                    item = index["members"][name]
                    try:
                        header = tarfile.TarInfo.frombuf(reader.read(item["offset"] - 512, 512), "utf-8", "strict")
                    except (tarfile.HeaderError, UnicodeError) as exc:
                        raise DataError(f"所选视频的 tar 头校验失败：{name}") from exc
                    if not header.isfile() or header.name != name or header.size != item["size"]:
                        raise DataError(f"索引与实际 tar 头不一致：{name}")
                result = download_member(reader, root, name, index["members"][name], archive)
                ready.add(key)
            except (DataError, OSError) as exc:
                result = {"status": "error", "path": name, "error": str(exc)}
                print(f"  失败：{exc}", file=sys.stderr, flush=True)
            status["videos"][key] = result
            write_json(root / "download_status.json", status)
    finally:
        status["planned_videos"] = len(manifest["videos"])
        status["ready_videos"] = len(ready)
        status["missing_video_ids"] = [r["record"]["video_id"] for r in manifest["videos"]
                                       if r["record"]["video_id"] not in ready]
        status["range_payload_bytes_this_run"] = reader.bytes_read
        write_json(root / "download_status.json", status)
        export_views(root, manifest, ready)
        reader.close()
    print(f"可用视频 {len(ready)}/{len(manifest['videos'])}；状态：{root / 'download_status.json'}", flush=True)
    return 0 if len(ready) == len(manifest["videos"]) else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="下载 EG-VQA 验证子集；通过 HTTP Range 提取所选视频，绝不回退整包下载。")
    p.add_argument("--output", type=Path, default=Path("data/downloads/egvqa-pilot"))
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true", help="只下载小标注并冻结子集，不读取视频包")
    mode.add_argument("--download-only", action="store_true", help="按已有 manifest 下载/重试，不重新选样")
    p.add_argument("--split", choices=("train", "test"), default="train", help="pilot 来源；默认保留官方 test")
    p.add_argument("--num-videos", type=int, default=24)
    p.add_argument("--questions-per-video", type=int, default=4)
    p.add_argument("--dev-videos", type=int, default=6, help="pilot 内用于提示/阈值调试的视频数")
    p.add_argument("--train-videos", type=int, default=0, help="额外 QA 弱监督训练视频数；默认不下载")
    p.add_argument("--train-questions-per-video", type=int, default=5)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--min-evidence", type=int, default=2)
    p.add_argument("--max-evidence", type=int, default=4)
    p.add_argument("--min-gap-seconds", type=float, default=0)
    p.add_argument("--min-duration", type=float, default=60)
    p.add_argument("--max-duration", type=float, default=600)
    p.add_argument("--question-types", nargs="+", choices=("temporal", "descriptive", "causal", "counterfactual"),
                   default=["temporal", "descriptive"])
    p.add_argument("--sources", nargs="+", choices=SOURCES, default=list(SOURCES))
    p.add_argument("--annotations-dir", type=Path, help="读取已下载的官方 JSON（仍校验固定版本 SHA-256）")
    p.add_argument("--index-file", type=Path, help="复用另一次下载生成的 cache/videos.index.json，避免从头扫描")
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--timeout", type=float, default=60, help="每次网络读取的超时秒数")
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    config = {key: getattr(args, key) for key in (
        "split", "num_videos", "questions_per_video", "dev_videos", "train_videos", "train_questions_per_video",
        "seed", "min_evidence", "max_evidence", "min_gap_seconds", "min_duration", "max_duration", "question_types", "sources",
    )}
    if (args.num_videos <= 0 or args.questions_per_video <= 0 or args.train_questions_per_video <= 0
            or not 0 <= args.dev_videos < args.num_videos or args.train_videos < 0
            or not 1 <= args.min_evidence <= args.max_evidence
            or not 0 <= args.min_duration <= args.max_duration
            or args.min_gap_seconds < 0 or args.retries < 0 or args.timeout <= 0
            or not all(math.isfinite(v) for v in (args.min_duration, args.max_duration, args.min_gap_seconds, args.timeout))):
        p.error("样本数、划分、证据数、时长或重试参数非法。")
    root = args.output.resolve()
    try:
        manifest_path = root / "manifest.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            if manifest.get("revision") != REVISION or manifest.get("archive") != ARCHIVE:
                raise DataError("已有 manifest 不是脚本固定的 EG-VQA 版本。")
            if not args.download_only and manifest.get("selection") != config:
                raise DataError("输出目录已有不同选样配置；请使用新的 --output，或 --download-only 续传原子集。")
        else:
            if args.download_only:
                raise DataError("缺少 manifest.json；先运行 --prepare-only 或默认命令。")
            records = load_annotations(root, args.split, args.annotations_dir)
            train = (records if args.split == "train" else load_annotations(root, "train", args.annotations_dir)) if args.train_videos else []
            manifest = select_subset(records, train, config)
            write_json(manifest_path, manifest)
        export_views(root, manifest)
        counts = Counter(row["role"] for row in manifest["videos"])
        questions = sum(len(row["record"]["questions"]) for row in manifest["videos"])
        print(f"子集已冻结：{dict(counts)}，共 {questions} 道 QA；{manifest_path}", flush=True)
        if args.prepare_only:
            return 0
        if args.index_file and not args.index_file.is_file():
            raise DataError(f"找不到索引：{args.index_file}")
        return download_subset(root, manifest, args.retries, args.timeout, args.index_file)
    except (DataError, OSError, ValueError, KeyError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已中断；原命令或 --download-only 可续传。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
