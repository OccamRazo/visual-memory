"""CPU protocol checks, with adversarial failures and independent toy oracles.

These do not validate model inference, OS isolation, image construction or human
grounding. Their narrow scope is intentional and recorded in test names.
"""

from itertools import combinations
import json
import math
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from egvqa_pilot.protocol import (BudgetExceeded, BudgetLedger, anonymous_judge_batch,
                                 capsule_coverage_mask, cosine, merge_evidence_intervals,
                                 packet_coverage_mask, parse_answer, parse_control, parse_judge,
                                 rank_topk, select_r2, select_rstar)
from egvqa_pilot.analysis import (aggregate_e1, aggregate_e2, e2_failure_category,
                                 video_cluster_paired_bootstrap)


class RetrievalAndCoverageTests(unittest.TestCase):
    def test_strict_overlap_merge_does_not_join_touching_events(self):
        self.assertEqual(merge_evidence_intervals([(5,7),(1,3),(2,4),(4,5)]), [(1.,4.),(4.,5.),(5.,7.)])
        self.assertEqual(merge_evidence_intervals([(1,3),(1,3),(2,2.5)]), [(1.,3.)])
        for interval in ((2,1), (1,1), (-1,2), (0,float("nan"))):
            with self.assertRaises(ValueError):
                merge_evidence_intervals([interval])

    def test_topk_cosine_ties_are_independent_of_storage_order_and_norm(self):
        ids, keys = ["c2","c1","c3"], [[9,0],[1,0],[0,1]]
        self.assertEqual(rank_topk(ids, keys, [2,0], 2), ["c1","c2"])
        self.assertEqual(rank_topk(ids[::-1], keys[::-1], [2,0], 9, ["c1"]), ["c2","c3"])
        with self.assertRaises(ValueError):
            rank_topk(["c1","c1"], [[1,0],[0,1]], [1,0], 1)
        with self.assertRaises(ValueError):
            cosine([0,0], [1,0])

    def test_r2_enumeration_matches_independent_exhaustive_objective(self):
        rng = random.Random(17)
        ids = [f"c{i:02}" for i in range(15)]
        keys = [[rng.uniform(-1,1) for _ in range(4)] for _ in ids]
        queries = [[1,0,0,0],[0,1,0,0]]
        initial = ids[:3]
        result = select_r2(ids,keys,queries,initial)
        self.assertLessEqual(len(result["candidate_ids"]),8)
        self.assertLessEqual(result["enumerated_combinations"],56)
        self.assertFalse(set(initial) & set(result["selected_ids"]))
        by_id = dict(zip(ids,keys))
        def dot_normalized(a,b):
            return sum(x*y for x,y in zip(a,b))/math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
        union = set()
        for query in queries:
            union.update(sorted(ids[3:], key=lambda i:(-dot_normalized(by_id[i],query),i))[:6])
        pool = sorted(union,key=lambda i:(-max(dot_normalized(by_id[i],q) for q in queries),i))[:8]
        scores = []
        for choice in combinations(sorted(pool),3):
            coverage = sum(max(dot_normalized(by_id[i],q) for i in choice) for q in queries)
            redundancy = sum(dot_normalized(by_id[a],by_id[b]) for a,b in combinations(choice,2))/3
            scores.append((coverage-.2*redundancy, choice))
        expected = min(scores,key=lambda x:(-x[0],x[1]))
        self.assertEqual(result["selected_ids"], list(expected[1]))
        self.assertAlmostEqual(result["score"],expected[0])
        reversed_result = select_r2(ids[::-1],keys[::-1],queries,initial)
        self.assertEqual(result,reversed_result)

    def test_r2_fewer_than_three_unread_uses_all_available_and_ties_use_ids(self):
        result = select_r2(["z","b","a"],[[1,0]]*3,[[1,0]],["z"])
        self.assertEqual(result["selected_ids"],["a","b"])
        self.assertEqual(result["enumerated_combinations"],1)
        self.assertEqual(select_r2(["a"],[[1,0]],[[1,0]],["a"])["selected_ids"],[])
        with self.assertRaises(ValueError):
            select_r2(["a"],[[1,0]],[],[])

    def test_distinct_valid_pts_in_same_capsule_required_for_coverage(self):
        groups = [(0,1),(1,2)]
        self.assertEqual(capsule_coverage_mask([0.2,0.2,1.1,1.4],[True]*4,groups),2)
        self.assertEqual(capsule_coverage_mask([0.2,0.5,1.1,1.4],[True,False,True,False],groups),0)
        self.assertEqual(capsule_coverage_mask([0.2,1.0],[True,True],groups),0)
        masks = {"a":capsule_coverage_mask([0.2],[True],groups),
                 "b":capsule_coverage_mask([0.5],[True],groups)}
        self.assertEqual(packet_coverage_mask(["a","b"],masks),0)
        with self.assertRaises(ValueError):
            packet_coverage_mask(["deleted"],masks)

    def test_rstar_minimal_cover_padding_and_maximum_coverage_diagnostic(self):
        ids = ["a","b","c","d","e"]
        masks = {"a":1,"b":2,"c":4,"d":3,"e":0}
        result = select_rstar(ids,masks,["e","a","b","c","d"],3,3)
        self.assertEqual(result["minimum_cover_size"],2)
        self.assertEqual(result["selected_ids"],["c","d","e"])
        self.assertTrue(result["access_ann"])
        limited = select_rstar(ids,masks,ids,3,1)
        self.assertTrue(limited["stored_ann"])
        self.assertFalse(limited["feasible_ann"])
        self.assertEqual(limited["selected_ids"],["d"])
        deleted = select_rstar(ids,{**masks,"c":0},ids,3)
        self.assertFalse(deleted["stored_ann"])
        self.assertIsNone(deleted["minimum_cover_size"])

    def test_rstar_dp_matches_bruteforce_over_random_small_live_banks(self):
        rng = random.Random(43)
        for _ in range(50):
            ids = [f"c{i}" for i in range(8)]
            masks = {i:rng.randrange(16) for i in ids}
            feasible_sets = [s for n in range(5) for s in combinations(ids,n)
                             if packet_coverage_mask(s,masks) == 15]
            expected = min(feasible_sets,key=lambda s:(len(s),s)) if feasible_sets else None
            result = select_rstar(ids,masks,ids,4)
            self.assertEqual(result["stored_ann"],expected is not None)
            self.assertEqual(result["minimum_cover_size"],len(expected) if expected is not None else None)
            self.assertEqual(result["stored_ann"],result["feasible_ann"])


class BudgetTests(unittest.TestCase):
    def reserve(self, ledger, request_id, **kwargs):
        return ledger.reserve(**{"request_id":request_id,"phase":"E2","question_id":"q1","method":"R2",
                                "input_tokens":1000,"max_output_tokens":96,**kwargs})

    def test_single_and_cumulative_limits_checked_before_request(self):
        ledger = BudgetLedger()
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"bad",input_tokens=8192,max_output_tokens=1)
        self.assertEqual(ledger.summary()["physical_calls"],0)
        self.reserve(ledger,"a",input_tokens=8096,max_output_tokens=96)
        ledger.finalize("a",output_tokens=96)
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"b",input_tokens=4001,max_output_tokens=96)
        self.reserve(ledger,"c",input_tokens=4000,max_output_tokens=96)
        self.assertEqual(ledger.method_cost("E2","q1","R2")["logical_tokens"],12288)

    def test_failed_control_and_retry_consume_both_call_opportunities(self):
        ledger = BudgetLedger()
        self.reserve(ledger,"first",role="control")
        ledger.finalize("first",output_tokens=None,error="OOM with unknown generation count")
        self.reserve(ledger,"retry",role="control")
        ledger.finalize("retry",output_tokens=12,error="parse_failure")
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"forbidden_third")
        costs = ledger.method_cost("E2","q1","R2")
        self.assertEqual(costs["logical_calls"],2)
        self.assertEqual(costs["failed_calls"],2)
        self.assertEqual(costs["logical_tokens"],1096+1012)

    def test_cross_method_cache_saves_physical_but_not_logical_tokens_or_calls(self):
        ledger = BudgetLedger()
        self.reserve(ledger,"r0",method="R0")
        ledger.finalize("r0",output_tokens=20)
        self.reserve(ledger,"rstar",method="R*",physical_request=False)
        ledger.finalize("rstar",output_tokens=20)
        self.assertEqual(ledger.summary()["physical_calls"],1)
        self.assertEqual(ledger.summary()["logical_calls"],2)
        self.assertEqual(ledger.summary()["logical_tokens"],2040)
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"again",method="Rstar",physical_request=False)

    def test_judge_is_offline_cost_but_does_not_bypass_physical_core_limit(self):
        ledger = BudgetLedger(core_physical_limit=2,total_physical_limit=3,e3_physical_limit=1)
        self.reserve(ledger,"reader",method="R0")
        ledger.finalize("reader",output_tokens=4)
        self.reserve(ledger,"judge",method="R0",role="judge")
        ledger.finalize("judge",output_tokens=40)
        self.assertEqual(ledger.method_cost("E2","q1","R0")["logical_calls"],1)
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"judge_extra",role="judge")
        self.reserve(ledger,"e3",phase="E3")
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"e3_extra",phase="E3")

    def test_pending_reservations_survive_resume_and_cannot_be_finalized_twice(self):
        ledger = BudgetLedger()
        self.reserve(ledger,"pending",role="control")
        restored = BudgetLedger.from_records(ledger.records())
        self.assertEqual(restored.records(),ledger.records())
        self.reserve(restored,"next")
        restored.finalize("next",output_tokens=96)
        with self.assertRaises(ValueError):
            restored.finalize("next",output_tokens=96)
        with self.assertRaises(BudgetExceeded):
            self.reserve(restored,"third")

    def test_unexpected_generation_overrun_preserves_violation_and_actual_cost(self):
        ledger = BudgetLedger()
        self.reserve(ledger,"overrun")
        with self.assertRaises(BudgetExceeded):
            ledger.finalize("overrun",output_tokens=97)
        self.assertEqual(ledger.summary()["budget_violations"],1)
        self.assertEqual(ledger.method_cost("E2","q1","R2")["logical_tokens"],1097)

    def test_d0_fifty_call_cap_is_separate_from_core_headroom(self):
        ledger = BudgetLedger(d0_physical_limit=1)
        self.reserve(ledger,"first",phase="D0")
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"second",phase="D0")
        self.reserve(ledger,"e1",phase="E1")

    def test_dev_reserve_retains_original_d0_quota_and_obeys_core_and_total_caps(self):
        ledger = BudgetLedger(d0_physical_limit=1,core_physical_limit=3,total_physical_limit=3)
        self.reserve(ledger,"d0",phase="D0")
        ledger.finalize("d0",output_tokens=12)
        original_d0 = ledger.records()[0].copy()
        for request_id,role in (("review_answer","answer"),("review_judge","judge")):
            self.reserve(ledger,request_id,phase="RESERVE",role=role)
            ledger.finalize(request_id,output_tokens=12)
        self.assertEqual(ledger.records()[0],original_d0)
        self.assertEqual(ledger.summary()["core_physical_calls"],3)
        self.assertEqual(ledger.summary()["physical_calls"],3)
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"extra_d0",phase="D0")
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"extra_reserve",phase="RESERVE")
        restored = BudgetLedger.from_records(ledger.records(),d0_physical_limit=1,
                                            core_physical_limit=3,total_physical_limit=3)
        self.assertEqual(restored.records(),ledger.records())

    def test_dev_reserve_cannot_bypass_core_cap_with_whole_run_headroom(self):
        ledger = BudgetLedger(core_physical_limit=1,total_physical_limit=3)
        self.reserve(ledger,"core_reserved",phase="RESERVE")
        with self.assertRaises(BudgetExceeded):
            self.reserve(ledger,"over_core",phase="RESERVE",role="judge")
        self.reserve(ledger,"optional",phase="E3")

    def test_reserve_101st_physical_call_rejected_but_cached_logic_still_charged(self):
        ledger = BudgetLedger()
        for i in range(100):
            request_id = f"reserve-{i}"
            self.reserve(ledger,request_id,phase="RESERVE")
            ledger.finalize(request_id,output_tokens=12)
        self.reserve(ledger,"cached-reserve",phase="RESERVE",physical_request=False)
        ledger.finalize("cached-reserve",output_tokens=12)
        cost = ledger.method_cost("RESERVE","q1","R2")
        self.assertEqual(cost["logical_calls"],101)
        self.assertEqual(cost["logical_tokens"],101*1012)
        self.assertEqual(cost["physical_calls"],100)
        self.assertEqual(cost["cache_saved_calls"],1)
        with self.assertRaisesRegex(BudgetExceeded,"core reserve physical request limit"):
            self.reserve(ledger,"forbidden-101st-physical",phase="RESERVE")
        self.assertEqual(ledger.summary()["physical_calls"],100)
        self.assertEqual(BudgetLedger.from_records(ledger.records()).records(),ledger.records())


class ParsingAndAggregationTests(unittest.TestCase):
    def test_illegal_citation_reported_and_malformed_answer_not_salvaged(self):
        parsed = parse_answer('{"answer":"opened","citations":["deleted"]}',["live"])
        self.assertTrue(parsed["parse_ok"])
        self.assertFalse(parsed["citations_legal"])
        self.assertEqual(parsed["illegal_citations"],["deleted"])
        self.assertFalse(parse_answer('preface {"answer":"ok","citations":[]}',[])["parse_ok"])
        self.assertTrue(parse_answer('{"answer":"opened","citations":[]}',[])["citations_legal"])

    def test_empty_answer_is_valid_abstention_but_wrong_field_types_still_fail(self):
        for answer in ("", "   "):
            parsed = parse_answer(json.dumps({"answer":answer,"citations":[]}),[])
            self.assertTrue(parsed["parse_ok"])
            self.assertTrue(parsed["abstained"])
            self.assertTrue(parsed["citations_legal"])
            self.assertEqual(parsed["answer"],"")
        self.assertFalse(parse_answer('{"answer":"opened","citations":[]}',[])["abstained"])
        for value in ({"citations":[]},{"answer":None,"citations":[]},{"answer":0,"citations":[]},
                      {"answer":[],"citations":[]},{"answer":"","citations":None}):
            self.assertFalse(parse_answer(json.dumps(value),[])["parse_ok"])

    def test_control_invalid_empty_and_excess_queries_use_original_question_only(self):
        for text in ('not json','{"queries":[]}','{"queries":["a","b","c"]}'):
            parsed = parse_control(text,"original question","R2")
            self.assertTrue(parsed["fallback"])
            self.assertEqual(parsed["queries"],["original question"])
        self.assertTrue(parse_control('{"queries":["a","b"]}',"question","R1")["fallback"])
        self.assertFalse(parse_control('{"queries":["a","b"]}',"question","R2")["fallback"])

    def test_single_string_control_normalizes_for_both_methods_without_fallback(self):
        for method in ("R1","R2"):
            string = parse_control('{"queries":"  find the later event  "}',"original",method)
            array = parse_control('{"queries":["find the later event"]}',"original",method)
            self.assertEqual(string["queries"],array["queries"])
            self.assertTrue(string["parse_ok"])
            self.assertFalse(string["fallback"])
            self.assertTrue(string["normalized_from_string"])
            self.assertFalse(array["normalized_from_string"])
            self.assertIsNone(string["parse_error"])

    def test_empty_string_or_invalid_query_list_still_falls_back(self):
        invalid_values = ("", "   ", None, 7, [], [""], ["valid",None], {"query":"valid"})
        for method in ("R1","R2"):
            for queries in invalid_values:
                result = parse_control(json.dumps({"queries":queries}),"original",method)
                self.assertFalse(result["parse_ok"])
                self.assertTrue(result["fallback"])
                self.assertFalse(result["normalized_from_string"])
                self.assertEqual(result["queries"],["original"])

    def test_judge_anonymization_removes_method_and_missing_result_is_uncertain(self):
        items = [{"item_id":f"q/{m}","method":m,"question":"q?","reference":"x","prediction":"x"}
                 for m in ("R0","R2")]
        blinded,mapping = anonymous_judge_batch(items)
        self.assertEqual(set(mapping.values()),{"q/R0","q/R2"})
        self.assertNotIn("R0",json.dumps(blinded))
        self.assertNotIn("R2",json.dumps(blinded))
        parsed = parse_judge('{"results":[{"id":"a0","verdict":"correct","reason":"matches"}]}',["a0","a1"])
        self.assertEqual([r["verdict"] for r in parsed],["correct","uncertain"])
        duplicate = '{"results":[{"id":"a0","verdict":"correct","reason":"x"},{"id":"a0","verdict":"incorrect","reason":"x"}]}'
        self.assertTrue(all(r["verdict"] == "uncertain" for r in parse_judge(duplicate,["a0","a1"])))

    def test_video_bootstrap_keeps_perfectly_correlated_questions_together(self):
        result = video_cluster_paired_bootstrap(["a"]*20+["b"]*20,[1]*20+[-1]*20)
        self.assertEqual(result["estimate"],0)
        self.assertEqual(result["ci95"],[-1,1])
        self.assertEqual(result["n_resamples"],2000)
        self.assertEqual(result,video_cluster_paired_bootstrap(["b"]*20+["a"]*20,[-1]*20+[1]*20))
        weighted = video_cluster_paired_bootstrap(["a"]*3+["b"],[1,1,1,-1])
        self.assertEqual(weighted["estimate"],.5)
        self.assertIsNone(video_cluster_paired_bootstrap([],[])["estimate"])

    def e1_fixture(self):
        planned = [{"question_id":"q1","video_id":"v1","num_gold_groups":2,"intervention_valid":True},
                   {"question_id":"q2","video_id":"v2","num_gold_groups":2,"intervention_valid":True}]
        rows = []
        for q in planned:
            for c in ("Full","Key-1","Key-2","Irrel-1","Irrel-2","Blind"):
                rows.append({"question_id":q["question_id"],"condition":c,"status":"complete",
                             "verdict":"correct" if c in ("Full","Irrel-1","Irrel-2") else "incorrect",
                             "citations_legal":True,"parse_ok":True})
        return planned,rows

    def test_e1_joint_candidate_cannot_be_mislabeled_human_confirmed(self):
        planned,rows = self.e1_fixture()
        result = aggregate_e1(planned,rows,[{"question_id":"q1","reviewer_type":"ai","confirmed":True}])
        self.assertEqual(result["n_automatic_candidates"],2)
        self.assertEqual(result["n_human_confirmed"],0)
        self.assertEqual(result["primary_D"]["estimate"],1)
        self.assertEqual(result["full_minus_blind"]["estimate"],1)
        self.assertFalse(result["scientific_protocol"]["all_passed"])
        self.assertEqual(result["engineering_status"],"INCOMPLETE")

    def test_e1_missing_condition_invalidates_pair_preserves_planned_denominator(self):
        planned,rows = self.e1_fixture()
        rows = [r for r in rows if not (r["question_id"] == "q2" and r["condition"] == "Key-2")]
        result = aggregate_e1(planned,rows)
        self.assertEqual(result["n_planned"],2)
        self.assertEqual(result["n_valid_pairs"],1)
        self.assertEqual(result["condition_table"]["Key-2"]["n_missing"],1)
        self.assertIn("missing_final_logical_result",result["pairs"][1]["invalid_reasons"])
        with self.assertRaises(ValueError):
            aggregate_e1(planned,rows+[rows[0]])

    def test_e1_empty_blind_retains_complete_pair_and_scores_zero_despite_judge_error(self):
        planned,rows = self.e1_fixture()
        for row in rows:
            if row["condition"] == "Blind":
                row.update(parse_answer('{"answer":"","citations":[]}',[]))
                row["verdict"] = "correct"  # Deliberate judge error cannot make abstention correct.
        result = aggregate_e1(planned,rows)
        self.assertEqual(result["n_valid_pairs"],2)
        self.assertEqual(result["condition_table"]["Blind"]["n_execution_success"],2)
        self.assertEqual(result["condition_table"]["Blind"]["n_correct"],0)
        self.assertEqual(result["primary_D"]["estimate"],1)
        self.assertEqual(result["full_minus_blind"]["estimate"],1)

    def test_e1_uncertain_scores_zero_main_and_is_reported_in_sensitivity(self):
        planned,rows = self.e1_fixture()
        for row in rows:
            if row["question_id"] == "q1" and row["condition"] == "Full":
                row["verdict"] = "uncertain"
        result = aggregate_e1(planned,rows)
        self.assertEqual(result["condition_table"]["Full"]["accuracy"],.5)
        self.assertEqual(result["condition_table"]["Full"]["accuracy_excluding_uncertain"],1)
        self.assertEqual(result["sensitivity_excluding_uncertain_D"]["n_questions"],1)

    def e2_fixture(self):
        planned = [{"question_id":f"q{i}","video_id":f"v{i}"} for i in range(3)]
        rows = [{"question_id":q["question_id"],"method":m,"status":"complete",
                 "verdict":"correct" if m in ("R2","R*") else "incorrect",
                 "citations_legal":True,"access_ann":m in ("R2","R*"),
                 "feasible_ann":True,"stored_ann":True,"snapshot_hash":f"snapshot-{q['video_id']}",
                 "logical_tokens":1000,"logical_calls":2 if m in ("R1","R2") else 1}
                for q in planned for m in ("R0","R1","R2","R*")]
        return planned,rows

    def test_e2_missing_failure_and_illegal_citation_preserve_common_denominators(self):
        planned,rows = self.e2_fixture()
        rows = [r for r in rows if not (r["question_id"] == "q0" and r["method"] == "R2")]
        for row in rows:
            if row["question_id"] == "q1" and row["method"] == "R2":
                row["citations_legal"] = False
        result = aggregate_e2(planned,rows)
        self.assertEqual(result["method_table"]["R2"]["n_planned"],3)
        self.assertEqual(result["method_table"]["R2"]["n_correct"],2)
        self.assertAlmostEqual(result["method_table"]["R2"]["J_ann"],1/3)
        self.assertEqual(result["primary_R2_minus_R1"]["net_gain_questions"],2)
        self.assertEqual(result["method_table"]["R2"]["n_missing"],1)
        self.assertFalse(result["cost_records_complete"])
        self.assertFalse(result["gates"]["token_fairness"])
        with self.assertRaises(ValueError):
            aggregate_e2(planned,rows+[rows[0]])

    def test_e2_abstention_flag_or_empty_answer_cannot_be_judged_correct(self):
        planned,rows = self.e2_fixture()
        for row in rows:
            if row["method"] == "R2":
                if row["question_id"] == "q0":
                    row["abstained"] = True
                elif row["question_id"] == "q1":
                    row["answer"] = ""  # Supports stored rows without the new explicit flag.
        result = aggregate_e2(planned,rows)
        self.assertEqual(result["method_table"]["R2"]["n_correct"],1)
        self.assertEqual(result["method_table"]["R2"]["n_execution_success"],3)
        self.assertEqual(result["method_table"]["R2"]["n_planned"],3)

    def test_e2_cost_fairness_does_not_use_cache_discount_and_mismatch_is_exposed(self):
        planned,rows = self.e2_fixture()
        for row in rows:
            if row["method"] == "R2":
                row["logical_tokens"],row["physical_tokens"] = 1060,0
        result = aggregate_e2(planned,rows)
        self.assertAlmostEqual(result["relative_mean_logical_token_gap"],.06)
        self.assertFalse(result["gates"]["token_fairness"])
        self.assertEqual(result["n_human_audited_gains"],0)
        self.assertFalse(result["gates"]["human_grounding"])
        for row in rows:
            if row["method"] == "R2":
                row["logical_tokens"] = 1050
        self.assertTrue(aggregate_e2(planned,rows)["gates"]["token_fairness"])

    def test_e2_different_snapshots_or_inconsistent_feasibility_are_rejected(self):
        planned,rows = self.e2_fixture()
        rows[0]["snapshot_hash"] = "different"
        with self.assertRaises(ValueError):
            aggregate_e2(planned,rows)
        planned,rows = self.e2_fixture()
        rows[0]["feasible_ann"] = False
        with self.assertRaises(ValueError):
            aggregate_e2(planned,rows)

    def test_e2_missing_feasibility_and_bad_costs_never_become_valid_defaults(self):
        planned,rows = self.e2_fixture()
        for row in rows:
            del row["feasible_ann"]
        self.assertEqual(aggregate_e2(planned,rows)["n_unknown_feasibility"],3)
        rows[0]["logical_tokens"] = -1
        with self.assertRaises(ValueError):
            aggregate_e2(planned,rows)

    def test_d0_calibration_requires_actual_human_agreement_not_ai_claim(self):
        planned,rows = self.e2_fixture()
        claimed = {"reviewer_type":"ai","n_audited":32,"n_agreed":32}
        result = aggregate_e2(planned,rows,d0_calibration=claimed)
        self.assertFalse(result["d0_judge_calibration"]["passed"])
        self.assertFalse(result["scientific_validity_passed"])
        result = aggregate_e2(planned,rows,d0_calibration={**claimed,"reviewer_type":"human","n_agreed":28})
        self.assertTrue(result["d0_judge_calibration"]["passed"])

    def test_pending_method_is_not_an_explicit_terminal_record(self):
        planned,rows = self.e2_fixture()
        rows[0]["status"] = "pending"
        self.assertEqual(aggregate_e2(planned,rows)["n_recorded_questions"],2)

    def test_e2_failure_attribution_obeys_order_and_does_not_infer_from_absent_answer(self):
        row = {"status":"complete","verdict":"incorrect","full_candidates_ann":False,
               "stored_ann":False,"feasible_ann":False,"access_ann":False}
        self.assertEqual(e2_failure_category(row,{"status":"complete","verdict":"correct"}),
                         "frontend_or_data_not_captured")
        row["full_candidates_ann"] = True
        self.assertEqual(e2_failure_category(row,{}),"known_path_not_stored")
        self.assertEqual(e2_failure_category({"status":"missing"},{}),"method_execution_or_parse_failure")
        self.assertEqual(e2_failure_category({"status":"complete","verdict":"incorrect"},{}),
                         "insufficient_diagnostic_information")


if __name__ == "__main__":
    unittest.main()
