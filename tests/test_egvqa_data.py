"""Scientific front-end invariants, using a real synthetic PyAV stream."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from unittest.mock import patch

import av
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from egvqa_pilot.data import (Capsule,ReservoirWriter,add_snapshot_keys,letterbox,
    apply_e1_duplicate_gate,plan_e1_question,prepare_video,validate_snapshot_budget)
from egvqa_subset import transport_url,ARCHIVE,build_index,download_member,DataError


class FrontEndTests(unittest.TestCase):
    def test_mirror_preserves_archive_identity(self):
        original=ARCHIVE.copy()
        with patch.dict("os.environ",{"HF_ENDPOINT":"https://hf-mirror.com/"}):
            self.assertTrue(transport_url(ARCHIVE["url"]).startswith("https://hf-mirror.com/"))
        self.assertEqual(original,ARCHIVE)

    def test_empty_unselected_tar_member_does_not_block_index(self):
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode="w") as archive:
            archive.addfile(tarfile.TarInfo("videos/empty.mp4"))
            info=tarfile.TarInfo("videos/selected.mp4");info.size=3
            archive.addfile(info,io.BytesIO(b"abc"))
        data=buffer.getvalue()
        class Reader:
            size=len(data)
            def read(self,start,size):return data[start:start+size]
        reader=Reader();identity={"url":"fixture","size":len(data),"sha256":"fixture"}
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            index=build_index(reader,identity,{"videos/selected.mp4"},root/"index.json")
            self.assertEqual(index["members"]["videos/empty.mp4"]["size"],0)
            self.assertEqual(index["members"]["videos/selected.mp4"]["size"],3)
            with self.assertRaises(DataError):
                download_member(reader,root,"videos/empty.mp4",index["members"]["videos/empty.mp4"],identity)

    def test_letterbox_fixed_pixels(self):
        image=np.full((40,80,3),255,dtype=np.uint8)
        result=letterbox(image)
        self.assertEqual(result.shape,(224,224,3))
        self.assertFalse(result[:56].any())
        self.assertTrue((result[56:168]==255).all())

    def test_online_reservoir_prefix_causality(self):
        pixels=np.zeros((4,224,224,3),dtype=np.uint8)
        left,right=ReservoirWriter("video"),ReservoirWriter("video")
        for i in range(90):
            cap=Capsule({"capsule_id":str(i),"pts":[i*2+j/3 for j in range(4)],"valid_mask":[True]*4},pixels)
            left.update(cap);right.update(copy.copy(cap))
            self.assertEqual(left.prefix_hash(),right.prefix_hash())
        prefix=left.prefix_hash()
        left.update(Capsule({"capsule_id":"future_original"},pixels))
        right.update(Capsule({"capsule_id":"future_changed"},pixels))
        self.assertNotEqual(prefix,left.prefix_hash())
        self.assertEqual(len(left.slots),64)
        self.assertEqual(left.seen,91)
        with self.assertRaises(ValueError):
            left.update(Capsule({"oversized":"x"*655360},pixels))

    def test_real_decode_pts_masks_and_persistent_budget(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);video=root/"input.mkv"
            with av.open(str(video),"w") as c:
                stream=c.add_stream("ffv1",rate=3);stream.width=80;stream.height=40;stream.pix_fmt="yuv420p"
                for i in range(13):
                    frame=av.VideoFrame.from_ndarray(np.full((40,80,3),i*10,dtype=np.uint8),format="rgb24")
                    for packet in stream.encode(frame):c.mux(packet)
                for packet in stream.encode():c.mux(packet)
            report=prepare_video(video,"synthetic",root/"prepared")
            self.assertEqual(report["unique_frames"],13)
            snapshot=root/"prepared/snapshot"
            manifest=json.loads((snapshot/"manifest.json").read_text())
            self.assertEqual(len(manifest["capsules"]),3)
            final=manifest["capsules"][-1]
            self.assertEqual(final["valid_mask"],[True,False,False,False])
            self.assertTrue(all(4<=p<6 for p in final["pts"]))
            self.assertNotIn("video_path",json.dumps(manifest))
            before=manifest["snapshot_hash"]
            keys=np.zeros((3,512),dtype=np.float32);keys[:,0]=1
            sealed=add_snapshot_keys(snapshot,keys,{"id":"synthetic-test"})
            self.assertNotEqual(before,sealed["snapshot_hash"])
            self.assertLessEqual(validate_snapshot_budget(snapshot)["actual_bytes"],42008576)
            with (snapshot/"illegal-cache.bin").open("wb") as f:f.truncate(42008576)
            with self.assertRaises(ValueError):validate_snapshot_budget(snapshot)

    def test_e1_touching_groups_hidden_ids_and_matched_differences(self):
        frames=[{"time":i/3,"pts":i} for i in range(180)]
        q={"question_id":"test_q1","evidence":[{"timestamp":[10,15]},{"timestamp":[15,20]}]}
        plan=plan_e1_question(q,frames,"test")
        self.assertEqual(len(plan["gold_groups"]),2)
        self.assertEqual(plan["construction_status"],"constructed_pending_human_audit")
        self.assertEqual(plan["human_audit_status"],"pending")
        full=set(plan["conditions"]["Full"]["group_ids"])
        for condition,row in plan["conditions"].items():
            if condition=="Blind":self.assertEqual(row["num_images"],0);continue
            self.assertEqual(row["num_images"],16)
            selected=set(row["group_ids"])
            if condition!="Full":
                self.assertEqual(full-selected,{row["replaced_group_id"]})
                self.assertEqual(selected-full,{row["replacement_group_id"]})
        for group in plan["groups"]:
            self.assertEqual(len(set(group["pts"])),4)
            self.assertTrue(group["group_id"].startswith("g"))
        distractors=plan["groups"][-3:]
        self.assertEqual(len({p for g in distractors for p in g["pts"]}),12)
        self.assertTrue(all(not 10<=p<20 for g in distractors for p in g["pts"]))

    def test_e1_short_outside_region_still_constructs_three_groups(self):
        # Only one evidence-free region, shorter than either gold group's span.
        frames=[{"time":i/3,"pts":i} for i in range(132)]
        q={"question_id":"short_outside","evidence":[{"timestamp":[0,20]},{"timestamp":[20,40]}]}
        plan=plan_e1_question(q,frames,"test")
        self.assertEqual(plan["construction_status"],"constructed_pending_human_audit")
        distractors=sorted(plan["groups"][-3:],key=lambda g:g["pts"][0])
        self.assertTrue(all(a["pts"][-1]<b["pts"][0] for a,b in zip(distractors,distractors[1:])))

    def test_e1_hidden_removed_pixel_copy_invalidates_entire_question(self):
        frames=[{"time":i/3,"pts":i} for i in range(180)]
        q={"question_id":"duplicate","evidence":[{"timestamp":[10,15]},{"timestamp":[15,20]}]}
        plan=plan_e1_question(q,frames,"test")
        for i,group in enumerate(plan["groups"]):group["frame_hashes"]=[f"{i}_{j}" for j in range(4)]
        self.assertEqual(apply_e1_duplicate_gate(plan)["mechanical_duplicate_check"]["status"],"passed")
        plan["groups"][-1]["frame_hashes"][0]=plan["groups"][0]["frame_hashes"][0]
        apply_e1_duplicate_gate(plan)
        self.assertEqual(plan["construction_status"],"invalid")
        self.assertIn("removed_frame_hash_survives_intervention",plan["reasons"])


if __name__=="__main__":unittest.main()
