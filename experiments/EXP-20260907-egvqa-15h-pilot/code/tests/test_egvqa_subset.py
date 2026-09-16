"""Network tests use an in-process HTTP server, never the full EG-VQA tar."""

from contextlib import contextmanager, redirect_stderr, redirect_stdout
import copy
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import egvqa_subset as eg


def record(key, source="HiREST"):
    return {
        "video_id": key, "video_path": f"videos/{key}.mp4", "duration": 100,
        "data_source": source, "metadata": {"title": "gold title", "segments": ["gold caption"]},
        "questions": [{"question_id": f"{key}_q{i}", "question": f"question {i}", "answer": "answer",
                       "type": "temporal" if i % 2 else "descriptive",
                       "evidence": [{"timestamp": [1, 10], "description": "gold"},
                                    {"timestamp": [20, 30], "description": "gold"}]}
                      for i in range(5)],
    }


def config(**overrides):
    values = {
        "split": "train", "num_videos": 4, "questions_per_video": 4, "dev_videos": 1,
        "train_videos": 3, "train_questions_per_video": 5, "seed": 17,
        "min_evidence": 2, "max_evidence": 4, "min_gap_seconds": 0,
        "min_duration": 60, "max_duration": 600,
        "question_types": ["temporal", "descriptive"], "sources": list(eg.SOURCES),
    }
    return {**values, **overrides}


@contextmanager
def range_server(data, mode="range"):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            header = self.headers.get("Range")
            if header is None:
                self.send_error(400)
                return
            start, end = map(int, header.removeprefix("bytes=").split("-"))
            calls.append((start, end))
            body = data[start:end + 1]
            self.send_response(200 if mode == "full" else 206)
            self.send_header("Connection", "close")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Range", f"bytes {start + (mode == 'wrong')}-{end}/{len(data)}")
            self.end_headers()
            try:
                self.wfile.write(body[:len(body) // 2] if mode == "truncated" else body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/videos.tar", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def archive_fixture():
    stream = io.BytesIO()
    payloads = {"videos/unused.mp4": b"DO NOT DOWNLOAD" * 1000,
                "videos/chosen.mp4": b"selected-video" * 100}
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, data in payloads.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return stream.getvalue(), payloads


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [record(f"video{i:02d}", eg.SOURCES[i % 3]) for i in range(15)]

    def test_deterministic_split_and_no_weak_gold(self):
        first = eg.select_subset(self.rows, self.rows, config())
        second = eg.select_subset(list(reversed(self.rows)), list(reversed(self.rows)), config())
        self.assertEqual(first, second)
        self.assertEqual(len(first["videos"]), 7)
        ids = [r["record"]["video_id"] for r in first["videos"]]
        self.assertEqual(len(ids), len(set(ids)))
        train = [r for r in first["videos"] if r["role"] == "train"]
        self.assertNotIn("evidence", json.dumps(train))
        self.assertNotIn("metadata", json.dumps(train))
        self.assertNotIn("description", json.dumps(train))

    def test_weak_selection_does_not_require_evidence(self):
        train_rows = [record(f"train{i:02d}") for i in range(5)]
        for row in train_rows:
            row.pop("metadata")
            for question in row["questions"]:
                question.pop("evidence")
        manifest = eg.select_subset(self.rows, train_rows, config())
        self.assertEqual(sum(r["role"] == "train" for r in manifest["videos"]), 3)

    def test_ingest_and_queries_do_not_leak_gold(self):
        manifest = eg.select_subset(self.rows, self.rows, config())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            eg.export_views(root, manifest)
            for role in eg.ROLES:
                for line in (root / "inputs" / f"{role}_ingest.jsonl").read_text().splitlines():
                    self.assertEqual(set(json.loads(line)), {"video_id", "video_path", "duration"})
                for line in (root / "inputs" / f"{role}_questions.jsonl").read_text().splitlines():
                    self.assertEqual(set(json.loads(line)), {"video_id", "question_id", "question", "type"})
            keep = {manifest["videos"][0]["record"]["video_id"]}
            eg.export_views(root, manifest, keep)
            self.assertEqual(len(eg.read_json(root / "ready/annotations/dev.json")), 1)
            self.assertEqual(eg.read_json(root / "ready/annotations/eval.json"), [])

    def test_insufficient_pool_is_error_not_silent_shrink(self):
        with self.assertRaises(eg.DataError):
            eg.select_subset(self.rows[:2], self.rows, config())

    def test_invalid_and_overlapping_timestamps(self):
        q = copy.deepcopy(self.rows[0]["questions"][0])
        q["evidence"][0]["timestamp"] = [float("nan"), 10]
        self.assertFalse(eg.valid_evidence(q, 100, config()))
        q["evidence"] = [{"timestamp": [0, 90]}, {"timestamp": [5, 10]}, {"timestamp": [20, 30]}]
        self.assertFalse(eg.valid_evidence(q, 100, config(min_gap_seconds=1)))
        q["evidence"] = [{"timestamp": [0, 10]}, {"timestamp": [20, 30]}]
        self.assertTrue(eg.valid_evidence(q, 100, config(min_gap_seconds=10)))

    def test_mismatched_annotation_checksum_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "train.json").write_text("[]")
            with self.assertRaises(eg.DataError):
                eg.load_annotations(root, "train", root)

    def test_path_traversal_refused(self):
        for name in ("../bad.mp4", "/videos/good.mp4", "videos/../bad.mp4", "videos/a/b.mp4", "videos\\a.mp4"):
            with self.subTest(name=name), self.assertRaises(eg.DataError):
                eg.safe_video_path(name)

    def test_existing_manifest_cannot_be_silently_reselected(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(eg, "load_annotations", return_value=self.rows), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            argv = ["--prepare-only", "--num-videos", "4", "--dev-videos", "1", "--output", temp]
            self.assertEqual(eg.main(argv), 0)
            path = Path(temp) / "manifest.json"
            before = path.read_bytes()
            self.assertEqual(eg.main([*argv, "--seed", "99"]), 1)
            self.assertEqual(path.read_bytes(), before)


class DownloadTests(unittest.TestCase):
    def test_range_index_and_only_selected_payload(self):
        data, payloads = archive_fixture()
        with tempfile.TemporaryDirectory() as temp, range_server(data) as (url, calls):
            root = Path(temp)
            archive = {"url": url, "size": len(data), "sha256": eg.digest(data)}
            reader = eg.RangeReader(url, len(data), retries=0)
            try:
                index = eg.build_index(reader, archive, {"videos/chosen.mp4"}, root / "index.json")
                self.assertEqual(len(index["members"]), 2)
                # Index requests contain only 512-byte headers, jumping over the unwanted video.
                self.assertTrue(all(end - start + 1 == 512 for start, end in calls))
                unwanted = index["members"]["videos/unused.mp4"]
                for start, end in calls:
                    self.assertFalse(start < unwanted["offset"] + unwanted["size"] and end >= unwanted["offset"])
                item = index["members"]["videos/chosen.mp4"]
                result = eg.download_member(reader, root, "videos/chosen.mp4", item, archive)
                self.assertEqual((root / "videos/chosen.mp4").read_bytes(), payloads["videos/chosen.mp4"])
                self.assertFalse((root / "videos/unused.mp4").exists())
                self.assertEqual(result["sha256"], eg.digest(payloads["videos/chosen.mp4"]))
                before = len(calls)
                self.assertTrue(eg.download_member(reader, root, "videos/chosen.mp4", item, archive)["reused"])
                self.assertEqual(len(calls), before)
                (root / "videos/chosen.mp4").write_bytes(b"x" * item["size"])
                with self.assertRaises(eg.DataError):
                    eg.download_member(reader, root, "videos/chosen.mp4", item, archive)
            finally:
                reader.close()

    def test_ignored_or_wrong_range_is_rejected_before_body_iteration(self):
        for mode in ("full", "wrong"):
            with self.subTest(mode=mode), range_server(b"x" * 2048, mode) as (url, _):
                reader = eg.RangeReader(url, 2048, retries=0)
                try:
                    with patch("requests.Response.iter_content", side_effect=AssertionError("body must not be read")):
                        with self.assertRaises(eg.DataError):
                            reader.read(512, 512)
                    self.assertEqual(reader.bytes_read, 0)
                finally:
                    reader.close()

    def test_truncated_response_does_not_become_verified_payload(self):
        with range_server(b"x" * 2048, "truncated") as (url, _):
            reader = eg.RangeReader(url, 2048, retries=0)
            try:
                with self.assertRaises(eg.DataError):
                    reader.read(512, 512)
                self.assertEqual(reader.bytes_read, 0)
            finally:
                reader.close()

    def test_index_scan_resumes_after_network_failure(self):
        data, _ = archive_fixture()
        with tempfile.TemporaryDirectory() as temp, range_server(data) as (url, calls):
            root = Path(temp)
            archive = {"url": url, "size": len(data), "sha256": eg.digest(data)}
            reader = eg.RangeReader(url, len(data), retries=0)
            original = reader.read

            def interrupt(start, size):
                if start != 0:
                    raise eg.DataError("fixture interrupted scan")
                return original(start, size)

            try:
                with patch.object(reader, "read", side_effect=interrupt), self.assertRaises(eg.DataError):
                    eg.build_index(reader, archive, {"videos/chosen.mp4"}, root / "index.json")
                saved = eg.read_json(root / "index.json")
                self.assertEqual(len(saved["members"]), 1)
                calls.clear()
                result = eg.build_index(reader, archive, {"videos/chosen.mp4"}, root / "index.json")
                self.assertIn("videos/chosen.mp4", result["members"])
                self.assertEqual(calls[0][0], saved["next_offset"])
            finally:
                reader.close()

    def test_resume_after_verified_chunk_and_no_success_on_failure(self):
        payload = b"a" * 25
        archive = {"url": "https://example.invalid/videos.tar", "size": 2048, "sha256": "fixture"}
        item = {"offset": 512, "size": len(payload)}

        class Reader:
            def __init__(self):
                self.calls = []
                self.fail = True

            def read(self, start, size):
                self.calls.append((start, size))
                if start == 520 and self.fail:
                    raise eg.DataError("fixture interruption")
                return payload[start - 512:start - 512 + size]

        with tempfile.TemporaryDirectory() as temp, patch.object(eg, "CHUNK_SIZE", 8):
            root, reader = Path(temp), Reader()
            with self.assertRaises(eg.DataError):
                eg.download_member(reader, root, "videos/chosen.mp4", item, archive)
            self.assertFalse((root / "videos/chosen.mp4").exists())
            self.assertEqual((root / "videos/chosen.mp4.part").stat().st_size, 8)
            reader.calls, reader.fail = [], False
            eg.download_member(reader, root, "videos/chosen.mp4", item, archive)
            self.assertEqual(reader.calls[0], (520, 8))
            self.assertEqual((root / "videos/chosen.mp4").read_bytes(), payload)

    def test_partial_failure_exports_only_verified_videos_and_returns_one(self):
        data, payloads = archive_fixture()
        with tempfile.TemporaryDirectory() as temp, range_server(data) as (url, _), redirect_stdout(io.StringIO()):
            root = Path(temp)
            archive = {"url": url, "size": len(data), "sha256": eg.digest(data)}
            manifest = {"revision": "fixture", "archive": archive, "videos": [
                {"role": "eval", "record": record("unused")},
                {"role": "eval", "record": record("chosen")},
            ]}
            eg.write_json(root / "manifest.json", manifest)
            original = eg.download_member

            def fail_one(reader, root, name, item, archive):
                if name == "videos/unused.mp4":
                    raise eg.DataError("fixture download failure")
                return original(reader, root, name, item, archive)

            with patch.object(eg, "download_member", side_effect=fail_one):
                self.assertEqual(eg.download_subset(root, manifest, retries=0), 1)
            status = eg.read_json(root / "download_status.json")
            self.assertEqual(status["ready_videos"], 1)
            self.assertEqual(status["missing_video_ids"], ["unused"])
            ready = eg.read_json(root / "ready/annotations/eval.json")
            self.assertEqual([v["video_id"] for v in ready], ["chosen"])


if __name__ == "__main__":
    unittest.main()
