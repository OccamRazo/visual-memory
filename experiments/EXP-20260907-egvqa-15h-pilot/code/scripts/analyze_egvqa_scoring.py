#!/usr/bin/env python3
"""Read-only, post-hoc audit of all frozen pilot answer/score conditions.

This does not rejudge answers or substitute a majority vote for a reference.
The exhaustive sensitivity analysis only imposes identical-text consistency.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egvqa_pilot.analysis import _score, aggregate_e1, video_cluster_paired_bootstrap


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def normalized(text):
    """Only case, punctuation and whitespace; no semantic equivalence claims."""
    return " ".join(re.findall(r"\w+", text.casefold()))


def word_count(text):
    return len(text.split())


def stat(values):
    return {"n": len(values), "min": min(values), "median": statistics.median(values),
            "mean": statistics.mean(values), "max": max(values),
            "above_30": sum(x > 30 for x in values)} if values else {"n": 0}


def score(row):
    return _score(row)


def duplicate_groups(rows, key):
    groups = defaultdict(list)
    for row in rows:
        if row["status"] == "complete" and row.get("answer", "").strip():
            groups[(row["question_id"], key(row["answer"]))].append(row)
    repeated = [group for group in groups.values() if len(group) > 1]
    conflicts = [group for group in repeated if len({r["verdict"] for r in group}) > 1]
    return repeated, conflicts


def brief(row):
    names = ["result_id", "phase", "condition", "answer", "verdict", "judge_reason",
             "judge_request_id", "selected_ids", "access_ann", "logical_tokens"]
    return {key: row.get(key) for key in names if key in row}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--annotations", type=Path,
                        default=ROOT / "data/downloads/egvqa-pilot/ready/annotations/eval.json")
    args = parser.parse_args()
    source_files = [args.run / name for name in
                    ["e1_pairs.jsonl", "e2_results.jsonl", "eval_manifest.json", "judge_batches.jsonl", "summary.json"]]
    source_files.append(args.annotations)
    source_hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    e1, e2 = (read_jsonl(args.run / name) for name in ["e1_pairs.jsonl", "e2_results.jsonl"])
    rows = e1 + e2
    assert len(rows) == 512 and len({r["result_id"] for r in rows}) == 512
    manifest = json.loads((args.run / "eval_manifest.json").read_text())
    planned = {q["question_id"]: q for q in manifest["questions"]}
    questions = {q["question_id"]: {**q, "video_id": video["video_id"]}
                 for video in json.loads(args.annotations.read_text()) for q in video["questions"]
                 if q["question_id"] in planned}
    assert len(questions) == 48
    judge_inputs = {}
    for batch in read_jsonl(args.run / "judge_batches.jsonl"):
        for item in batch["blinded_items"]:
            result_id = batch["mapping"][item["id"]]
            assert result_id not in judge_inputs
            judge_inputs[result_id] = item
    complete = [r for r in rows if r["status"] == "complete"]
    for row in complete:
        if row.get("answer", "").strip():
            item = judge_inputs[row["result_id"]]
            assert item["prediction"] == row["answer"]
            assert item["question"] == questions[row["question_id"]]["question"]
            assert item["reference"] == questions[row["question_id"]]["answer"]
    exact_repeated, exact_conflicts = duplicate_groups(rows, lambda s: s)
    norm_repeated, norm_conflicts = duplicate_groups(rows, normalized)
    duplicate_report = {}
    for name, repeated, conflicts in [("exact", exact_repeated, exact_conflicts),
                                      ("case_punctuation_whitespace", norm_repeated, norm_conflicts)]:
        duplicate_report[name] = {
            "repeated_groups": len(repeated), "repeated_rows": sum(map(len, repeated)),
            "conflicting_groups": len(conflicts), "conflicting_rows": sum(map(len, conflicts)),
            "conflicting_questions": len({g[0]["question_id"] for g in conflicts}),
            "groups": [{"question_id": g[0]["question_id"],
                        "question": questions[g[0]["question_id"]]["question"],
                        "reference": questions[g[0]["question_id"]]["answer"],
                        "rows": [brief(r) for r in g]} for g in conflicts]}
    e1_index = defaultdict(dict)
    for row in e1:
        e1_index[row["question_id"]][row["condition"]] = row
    # Reuse frozen parsing, truncation and mechanical-validity rules.
    canonical_e1 = aggregate_e1(manifest["questions"], e1)
    canonical_pairs = {r["question_id"]: r for r in canonical_e1["pairs"]}
    frozen_pairs = json.loads((args.run / "summary.json").read_text())["E1"]["pairs"]
    for frozen in frozen_pairs:
        for field in ["valid_pair", "scores", "D", "automatic_joint_candidate"]:
            assert canonical_pairs[frozen["question_id"]][field] == frozen[field]
    valid_e1 = {q: conditions for q, conditions in e1_index.items()
                if canonical_pairs[q]["valid_pair"]}
    e2_index = defaultdict(dict)
    for row in e2:
        e2_index[row["question_id"]][row["condition"]] = row
    assert all(set(cs) == {"R0", "R1", "R2", "R*"} for cs in e2_index.values())

    def e1_per_question(scores=None):
        scores = scores or {}
        out = []
        for qid, conditions in valid_e1.items():
            s = {c: scores.get(r["result_id"], score(r)) for c, r in conditions.items()}
            keys = [v for k, v in s.items() if k.startswith("Key-")]
            irrels = [v for k, v in s.items() if k.startswith("Irrel-")]
            out.append({"question_id": qid, "video_id": planned[qid]["video_id"],
                        "scores": s, "full_minus_key": s["Full"] - statistics.mean(keys),
                        "full_minus_irrel": s["Full"] - statistics.mean(irrels),
                        "D": statistics.mean(irrels) - statistics.mean(keys),
                        "key_incorrect_count": len(keys) - sum(keys),
                        "key_correct_count": sum(keys),
                        "all_irrel_correct": all(irrels),
                        "candidate": bool(s["Full"] and not s["Blind"] and all(irrels)
                                          and len(keys) - sum(keys) >= 2
                                          and all(r.get("verdict") in ("correct", "incorrect") for r in conditions.values())
                                          and all(r.get("citations_legal") is True for r in conditions.values()))})
        return out

    per_e1 = e1_per_question()
    for row in per_e1:
        canonical = canonical_pairs[row["question_id"]]
        assert row["scores"] == canonical["scores"]
        assert abs(row["D"] - canonical["D"]) < 1e-12
        assert row["candidate"] == canonical["automatic_joint_candidate"]
    e1_conditions = {}
    for name in ["Full", "Blind", "Key", "Irrel"]:
        selected = [r for cs in valid_e1.values() for c, r in cs.items()
                    if c == name or c.startswith(name + "-")]
        e1_conditions[name] = {"n": len(selected), "correct": sum(map(score, selected)),
                               "verdicts": dict(Counter(r["verdict"] for r in selected))}
    full_right = [p for p in per_e1 if p["scores"]["Full"]]
    e1_report = {
        "n_valid_questions": len(valid_e1), "condition_micro_counts": e1_conditions,
        "D_positive_zero_negative": dict(Counter("positive" if p["D"] > 0 else
                                                  "negative" if p["D"] < 0 else "zero" for p in per_e1)),
        "full_correct": len(full_right),
        "full_correct_with_any_key_failure": sum(p["key_incorrect_count"] > 0 for p in full_right),
        "full_correct_with_two_or_more_key_failures": sum(p["key_incorrect_count"] >= 2 for p in full_right),
        "full_correct_with_both_irrel_correct": sum(p["all_irrel_correct"] for p in full_right),
        "full_correct_both_irrel_correct_with_two_key_failures": sum(
            p["all_irrel_correct"] and p["key_incorrect_count"] >= 2 for p in full_right),
        "automatic_joint_candidates": sum(p["candidate"] for p in per_e1),
        "full_incorrect_any_key_correct": sum(not p["scores"]["Full"] and p["key_correct_count"] > 0 for p in per_e1),
        "all_visual_conditions_incorrect": sum(not any(v for c, v in p["scores"].items() if c != "Blind") for p in per_e1),
        "mean_full_minus_key": statistics.mean(p["full_minus_key"] for p in per_e1),
        "mean_full_minus_irrel": statistics.mean(p["full_minus_irrel"] for p in per_e1),
        "D": video_cluster_paired_bootstrap([p["video_id"] for p in per_e1], [p["D"] for p in per_e1]),
        "per_question": per_e1}
    e2_changes = []
    for qid, cs in e2_index.items():
        difference = score(cs["R2"]) - score(cs["R1"])
        if difference:
            q = questions[qid]
            e2_changes.append({"question_id": qid, "question": q["question"], "reference": q["answer"],
                               "difference": difference, "same_answer": cs["R1"]["answer"] == cs["R2"]["answer"],
                               "same_selected_ids": cs["R1"]["selected_ids"] == cs["R2"]["selected_ids"],
                               "R1": brief(cs["R1"]), "R2": brief(cs["R2"])})
    same_packets = defaultdict(list)
    for row in e2:
        same_packets[(row["question_id"], row["snapshot_hash"], tuple(row["selected_ids"]))].append(row)
    packet_groups = [rs for rs in same_packets.values() if len(rs) > 1]
    packet_report = {
        "identity_rule": "same question_id, snapshot_hash, and ordered selected_ids",
        "groups": len(packet_groups), "rows": sum(map(len, packet_groups)),
        "different_answer_groups": sum(len({r["answer"] for r in rs}) > 1 for rs in packet_groups),
        "different_verdict_groups": sum(len({r["verdict"] for r in rs}) > 1 for rs in packet_groups),
        "conflicts": [{"question_id": rs[0]["question_id"], "rows": [brief(r) for r in rs]}
                      for rs in packet_groups if len({r["verdict"] for r in rs}) > 1]}

    def e2_boot(scores=None):
        scores = scores or {}
        vids, diffs = [], []
        for qid, cs in e2_index.items():
            vids.append(planned[qid]["video_id"])
            diffs.append(scores.get(cs["R2"]["result_id"], score(cs["R2"]))
                         - scores.get(cs["R1"]["result_id"], score(cs["R1"])))
        return video_cluster_paired_bootstrap(vids, diffs)

    sensitivities = []
    # Only resolve proven identical-text conflicts. Every binary assignment is
    # considered; no reference verdict is treated as objectively known here.
    for assignment in itertools.product([0, 1], repeat=len(exact_conflicts)):
        scores = {row["result_id"]: s for group, s in zip(exact_conflicts, assignment) for row in group}
        alt_e1 = e1_per_question(scores)
        sensitivities.append({"assignment": list(assignment), "e2_R2_minus_R1": e2_boot(scores),
                              "e1_D": video_cluster_paired_bootstrap(
                                  [p["video_id"] for p in alt_e1], [p["D"] for p in alt_e1]),
                              "e1_joint_candidates": sum(p["candidate"] for p in alt_e1)})
    sensitivity = {"rule": "all binary assignments to each of six exact-text conflicting groups; original scores untouched",
                   "n_assignments": len(sensitivities), "original_R2_minus_R1": e2_boot(),
                   "assignments": sensitivities}
    for metric in ["e2_R2_minus_R1", "e1_D"]:
        sensitivity[metric + "_estimate_range"] = [min(s[metric]["estimate"] for s in sensitivities),
                                                     max(s[metric]["estimate"] for s in sensitivities)]
        sensitivity[metric + "_ci_endpoint_envelope"] = [min(s[metric]["ci95"][0] for s in sensitivities),
                                                           max(s[metric]["ci95"][1] for s in sensitivities)]
    sensitivity["e1_joint_candidate_range"] = [min(s["e1_joint_candidates"] for s in sensitivities),
                                                max(s["e1_joint_candidates"] for s in sensitivities)]
    equal_r1_r2 = [cs for cs in e2_index.values() if cs["R1"]["answer"] == cs["R2"]["answer"]]
    forced_equal = {r["result_id"]: 0 for cs in equal_r1_r2 if score(cs["R1"]) != score(cs["R2"])
                    for r in [cs["R1"], cs["R2"]]}
    sensitivity["only_force_equal_R1_R2_pairs"] = e2_boot(forced_equal)
    references = [word_count(q["answer"]) for q in questions.values()]
    length_report = {"word_count_rule": "Python str.split; lexical whitespace words, not tokenizer tokens",
                     "references": stat(references),
                     "by_phase_condition": {},
                     "reference_over_30_question_ids": [q for q, item in questions.items() if word_count(item["answer"]) > 30],
                     "longest_references": sorted([{"question_id": q, "words": word_count(item["answer"]),
                                                     "reference": item["answer"]} for q, item in questions.items()],
                                                   key=lambda x: -x["words"])[:8]}
    by_condition = defaultdict(list)
    for row in complete:
        label = row["condition"].split("-")[0] if row["phase"] == "E1" else row["condition"]
        by_condition[(row["phase"], label)].append(row)
    for (phase, condition), group in sorted(by_condition.items()):
        length_report["by_phase_condition"][phase + ":" + condition] = {
            **stat([word_count(r["answer"]) for r in group]),
            "empty": sum(not r["answer"].strip() for r in group),
            "citation_ids_inside_answer": sum(bool(re.search(r"\b(?:g[0-9a-f]{12}|c\d{6})\b", r["answer"])) for r in group),
            "insufficient_phrase": sum("insufficient" in r["answer"].lower() for r in group)}
    report = {"audit_type": "posthoc_text_and_score_consistency_not_independent_visual_reanswer_not_human",
              "source_hashes": source_hashes, "total_conditions": len(rows),
              "complete_conditions": len(complete),
              "status_counts": dict(Counter(r["status"] for r in rows)),
              "invalid_conditions_separate": [brief(r) | {"status": r["status"], "error": r.get("error")}
                                               for r in rows if r["status"] != "complete"],
              "invalid_questions": sorted({r["question_id"] for r in rows if r["status"] != "complete"}),
              "judge_input_equality_checks": {"n_checked_nonempty": len(judge_inputs), "passed": True},
              "duplicates": duplicate_report, "lengths": length_report, "e1": e1_report,
              "e2": {"R2_gain": sum(x["difference"] == 1 for x in e2_changes),
                     "R2_loss": sum(x["difference"] == -1 for x in e2_changes),
                     "R1_R2_exact_equal_questions": len(equal_r1_r2),
                     "same_packet_conditions": packet_report, "changes": e2_changes},
              "identical_text_consistency_sensitivity": sensitivity}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "scoring_diagnostics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    lines = ["# EG-VQA 判分与答案文本诊断", "",
             "这是事后文本审计：没有重跑视觉模型、没有修改原分数，也不构成人工盲审或独立视觉重答。", "",
             f"全量检查 512 个条件：483 个正常完成，29 个构造失败（4 题）单列。所有非空答案传给 judge 的问题、参考、预测与原记录完全一致。", "",
             "## 确定存在的评分不一致", "",
             f"同题完全相同非空答案有 {len(exact_repeated)} 个重复组；其中 {len(exact_conflicts)} 组、{sum(map(len, exact_conflicts))} 条记录出现不一致评分。仅规范化大小写、标点和空白仍得到相同冲突数。", ""]
    lines += [f"E2 有 {packet_report['groups']} 组／{packet_report['rows']} 个条件拥有相同问题、快照哈希和有序单元 ID；生成答案全部完全一致，但其中 {packet_report['different_verdict_groups']} 组评分不同：种植题 J3Kg76JODsk_q01 的 R0/R1，以及相扑题 v_0zjA3KPnLK8_q02 的 R0/R2。这些差异发生在评分阶段。", ""]
    for group in duplicate_report["exact"]["groups"]:
        lines += [f"### {group['question_id']}", "", f"问题：{group['question']}", "",
                  f"参考：{group['reference']}", "", f"完全相同预测：{group['rows'][0]['answer']}", "",
                  "| 条件 | 判分 | 原 judge 理由 |", "|---|---|---|"]
        lines += [f"| {r['phase']} {r['condition']} | {r['verdict']} | {r['judge_reason']} |" for r in group["rows"]]
        lines += [""]
    lines += ["## 同答统一评分的敏感性（不替代主结果）", "",
              "把每个已证实冲突的完全相同答案组统一成 0 或 1，穷举 64 种赋值；组的真值未知，禁止以多数票充当金标。其他记录一律保留原分数。", "",
              f"- 仅让 R1/R2 完全相同的预测同分：R2−R1 从 −6/48 变为 −5/48，即 {sensitivity['only_force_equal_R1_R2_pairs']['estimate']:.2%}；95% CI {sensitivity['only_force_equal_R1_R2_pairs']['ci95']}。",
              f"- 对全部 6 组强制一致，R2−R1 点估计范围 {sensitivity['e2_R2_minus_R1_estimate_range']}，各方案 CI 端点总包络 {sensitivity['e2_R2_minus_R1_ci_endpoint_envelope']}。这是情景包络，不是新置信区间。",
              f"- E1 的 D 点估计范围 {sensitivity['e1_D_estimate_range']}；联合候选数范围 {sensitivity['e1_joint_candidate_range']}。", "",
              "能确定至少一个 R2 退步来自 judge 不一致，但该缺陷不能单独解释全部净退步；统一其他冲突也可能降低 R1 漏判带来的表观劣势，不能只修正有利于 R2 的一题。", "",
              "## E1 失败分布", "",
              f"44 题中 Full 正确 {len(full_right)} 题；{e1_report['all_visual_conditions_incorrect']} 题所有有图条件均不正确。D 的正/零/负计数：{e1_report['D_positive_zero_negative']}。", "",
              f"Full 正确题中，至少一次 Key 变错 {e1_report['full_correct_with_any_key_failure']} 题，至少两次变错 {e1_report['full_correct_with_two_or_more_key_failures']} 题；两次 Irrel 均正确 {e1_report['full_correct_with_both_irrel_correct']} 题。Full 错但至少一个 Key 对有 {e1_report['full_incorrect_any_key_correct']} 题。", "",
              f"逐题宏平均 Full−Key={e1_report['mean_full_minus_key']:.4f}，Full−Irrel={e1_report['mean_full_minus_irrel']:.4f}。D 的 Full 项会代数相消，D 本身衡量 Irrel 与 Key 的差；需要同时看 Full 的低可答率和个案条件。", "",
              "## 30 词限制", "",
              f"按空白分词，48 条参考长度：{length_report['references']}。所有参考均不超过 30 词，因此不能把总体失败简单归因为参考本身装不进 30 词。", "",
              "| 条件 | 答案数 | 平均词数 | 超过 30 词 | 空字符串 | 文本内引用 ID | insufficient |", "|---|---:|---:|---:|---:|---:|---:|"]
    for label, s in length_report["by_phase_condition"].items():
        lines.append(f"| {label} | {s['n']} | {s['mean']:.2f} | {s['above_30']} | {s['empty']} | {s['citation_ids_inside_answer']} | {s['insufficient_phrase']} |")
    lines += ["", "短答案约束、文本内额外复述引用 ID 可能占用可表达事实的空间；但本分析没有做解除长度限制的对照，无法量化因果贡献。", "",
              "## E2 全部 8 个 loss 与 2 个 gain", "",
              "这里只报告文本和原 judge 差异，不把参考之外的视觉描述自动当成幻觉。参考是不穷尽的文字，判分器不能看视频。", ""]
    for case in e2_changes:
        lines += [f"### {case['question_id']} ({'gain' if case['difference'] > 0 else 'loss'})", "",
                  f"问题：{case['question']}", "", f"参考：{case['reference']}", "",
                  f"R1 ({case['R1']['verdict']}): {case['R1']['answer']}", "",
                  f"R1 理由：{case['R1']['judge_reason']}", "",
                  f"R2 ({case['R2']['verdict']}): {case['R2']['answer']}", "",
                  f"R2 理由：{case['R2']['judge_reason']}", "",
                  f"相同预测={case['same_answer']}；相同选中单元={case['same_selected_ids']}。", ""]
    lines += ["## 事实与待验证解释", "",
              "事实：相同 question/reference/prediction 在不同四题 judge batch 中被不同判分；若干理由把‘参考未提及’直接当成错误，另一些又宽松接受省略。这使原始差值混入评价噪声。", "",
              "假说：批次上下文、答案简化与额外描述的处理不一致可能造成该现象。本审计没有更换批次顺序复判，不能拆分各因素。", "",
              "事实：部分 R1/R2 差异是明确动作或食材变化，另一些只是近义措辞、额外画面描述。这些需要逐设置独立视觉重答，再与参考比对；仅看文本不能判断谁更忠实画面。", "",
              "限制：只有 12 视频；这里所有敏感性均事后设计；同答统一只修复可证明的不一致，不保证其他分数正确。原置信区间只描述视频抽样波动，不能覆盖 judge 系统性偏差。", ""]
    (args.output / "scoring_diagnostics.md").write_text("\n".join(lines))
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in source_hashes.items())
    print(json.dumps({"conditions": len(rows), "exact_conflicts": len(exact_conflicts),
                      "e1": {k: v for k, v in e1_report.items() if k != "per_question"},
                      "lengths": length_report,
                      "sensitivity": {k: v for k, v in sensitivity.items() if k != "assignments"}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
