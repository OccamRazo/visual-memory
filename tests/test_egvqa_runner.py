"""Failure-path integration with a fake backend; no GPU or OS-isolation claim."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from egvqa_pilot.protocol import BudgetLedger, BudgetExceeded
from egvqa_pilot.runner import ExperimentRunner, append, rows, write_json


class FakeBackend:
    def __init__(self):
        self.requests=[]
        self.fail_r1_prepare=False
        self.error=None
        self.cached=None

    def prepare(self,role,text,images):
        if self.fail_r1_prepare and role=="control" and "exactly one short string" in text:
            raise ValueError("synthetic R1 preparation failure")
        return SimpleNamespace(role=role,text=text,images=images,input_tokens=1000,max_new_tokens=96)

    def cache_lookup(self,prepared):
        return self.cached

    def generate(self,*,prepared,request_id,metadata):
        self.requests.append((prepared,metadata))
        return {"request_id":request_id,"output_text":'{"queries":["look for event"]}' if prepared.role=="control"
                else '{"answer":"observed event","citations":[]}',"output_tokens":12,
                "output_tokens_complete":not bool(self.error),"total_tokens":1012,"error":self.error,
                "latency_s":.1,"physical_latency_s":.1,"cache_hit":self.cached is not None,
                "physical_request":self.cached is None,"truncated":False}


def minimal_runner(root):
    runner=ExperimentRunner.__new__(ExperimentRunner)
    runner.run=root;runner.prepared=root/"prepared"
    runner.config={"timing":{"model_deadline":"2099-01-01T00:00:00+00:00"}}
    runner.ledger=BudgetLedger();runner.ledger_path=root/"ledger.json"
    runner.calls={};runner.calls_path=root/"calls.jsonl"
    runner.backend=FakeBackend()
    runner.questions={"q":{"question_id":"q","video_id":"v","question":"What happened?",
                           "answer":"GOLD_ANSWER_MUST_STAY_IN_EVALUATOR",
                           "evidence":[{"timestamp":[0,1]},{"timestamp":[2,3]}]}}
    runner.planned=list(runner.questions.values())
    return runner


class RunnerFailureTests(unittest.TestCase):
    def test_unknown_failed_generation_is_charged_and_resume_does_not_repeat_it(self):
        with tempfile.TemporaryDirectory() as temporary,redirect_stdout(io.StringIO()):
            runner=minimal_runner(Path(temporary));runner.backend.error="synthetic generation OOM"
            first=runner.call("E2","q","R2","control","control","query")
            self.assertEqual(runner.ledger.method_cost("E2","q","R2")["logical_tokens"],1096)
            self.assertEqual(runner.ledger.summary()["pending_requests"],0)
            self.assertEqual(len(rows(runner.calls_path)),1)
            self.assertEqual(runner.call("E2","q","R2","control","control","query"),first)
            self.assertEqual(len(runner.backend.requests),1)
            restored=BudgetLedger.from_records(json.loads(runner.ledger_path.read_text()))
            self.assertEqual(restored.summary(),runner.ledger.summary())

    def test_judge_budget_failure_keeps_every_prediction_as_uncertain(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner=minimal_runner(Path(temporary));input_path=runner.run/"answers.jsonl";output_path=runner.run/"scored.jsonl"
            for i in range(5):
                append(input_path,{"result_id":f"E2:q:R{i}","question_id":"q","status":"complete","answer":"observed event"})
            append(input_path,{"result_id":"failed","question_id":"q","status":"failed","answer":""})
            with patch.object(runner,"call",side_effect=BudgetExceeded("synthetic exhausted budget")) as call:
                runner.score("E2",input_path,output_path)
                self.assertEqual(call.call_count,2)
                runner.score("E2",input_path,output_path)
                self.assertEqual(call.call_count,2)
            final=rows(output_path)
            self.assertEqual(len(final),6)
            self.assertEqual(sum(r["verdict"]=="uncertain" for r in final),5)
            self.assertEqual(sum(r["verdict"]=="incorrect" for r in final),1)

    def test_r1_failure_does_not_cancel_r2_or_privileged_reference_and_no_gold_prompts(self):
        with tempfile.TemporaryDirectory() as temporary,redirect_stdout(io.StringIO()):
            runner=minimal_runner(Path(temporary));runner.backend.fail_r1_prepare=True
            capsules=[{"capsule_id":f"c{i}","pts":[2*i+j*.2 for j in range(4)],"valid_mask":[True]*4}
                      for i in range(6)]
            snapshot=runner.prepared/"v"/"snapshot"
            write_json(snapshot/"manifest.json",{"capsules":capsules,"snapshot_hash":"frozen-snapshot"})
            write_json(snapshot.parent/"audit"/"candidates.json",capsules)
            ids=[c["capsule_id"] for c in capsules]
            normal_packets=[]
            def packet(selected):
                return {"capsules":[c for c in capsules if c["capsule_id"] in selected],
                        "images":np.zeros((len(selected),4,2,2,3),dtype=np.uint8),"snapshot_hash":"frozen-snapshot"}
            class FakeReader:
                identity={"abi":8}
                def __init__(self,*args):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def request(self,action,**kwargs):
                    if action=="rank":return [i for i in ids if i not in kwargs.get("exclude",[])][:kwargs["k"]]
                    if action=="r2":return {"selected_ids":ids[3:],"candidate_ids":ids[3:]}
                    if action=="packet":
                        normal_packets.append(kwargs["ids"])
                        return packet(kwargs["ids"])
                    raise AssertionError(action)
            def encode(texts):
                self.assertTrue(all("GOLD_ANSWER_MUST_STAY_IN_EVALUATOR" not in t for t in texts))
                return np.array([[1.,0.]]*len(texts)),[False]*len(texts)
            runner.clip=SimpleNamespace(texts=encode)
            with patch("egvqa_pilot.runner.SafeReader",FakeReader),patch("egvqa_pilot.runner.validate_snapshot_budget"),\
                 patch("egvqa_pilot.runner.privileged_packet",side_effect=lambda root,selected:packet(selected)) as privileged,\
                 patch.object(runner,"score"):
                runner.run_e2()
            final={r["method"]:r for r in rows(runner.run/"e2_answers.jsonl")}
            self.assertEqual(set(final),{"R0","R1","R2","R*"})
            self.assertEqual(final["R1"]["status"],"failed")
            self.assertTrue(final["R1"]["feasible_ann"])
            self.assertEqual(final["R2"]["status"],"complete")
            self.assertEqual(final["R*"]["status"],"complete")
            self.assertEqual(privileged.call_count,1)
            self.assertEqual(len(normal_packets),4)
            self.assertEqual(final["R2"]["logical_calls"],2)
            self.assertEqual(len(runner.backend.requests),4)
            for prepared,metadata in runner.backend.requests:
                self.assertNotIn("GOLD_ANSWER_MUST_STAY_IN_EVALUATOR",prepared.text)
                if prepared.role=="answer":
                    self.assertNotIn("look for event",prepared.text)


if __name__=="__main__":unittest.main()
