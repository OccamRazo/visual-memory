"""Recomputable pilot summaries, explicit denominators and clustered intervals.

Input rows are *final logical conditions*, never raw physical attempts. Passing
duplicate condition rows raises an error: callers must resolve retries through
their persisted ledger, rather than letting an arbitrary last row win.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import math
import random
from statistics import mean
from typing import Any, Mapping, Sequence

from .protocol import fixed_hash_order, merge_evidence_intervals


CORE_CHECKS = ("snapshot_causality", "no_replay", "dual_budget", "paired_intervention",
               "cross_question_isolation", "scoring_aggregation")
SUCCESS_STATES = frozenset(("complete", "ok", "success"))
TERMINAL_STATES = SUCCESS_STATES | frozenset(("failed", "construction_failed", "terminated",
                                            "budget_exceeded", "unavailable", "decode_failed"))


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def video_cluster_paired_bootstrap(video_ids: Sequence[str], differences: Sequence[float],
                                   n_resamples: int = 2000, seed: int = 43) -> dict[str, Any]:
    """Resample whole videos; retain all paired question differences in a draw.

The point estimate is question-weighted. Each replicate samples N_video videos
with replacement and computes the question-weighted mean in those clusters.
This is not a question-level independent bootstrap.
"""
    if len(video_ids) != len(differences) or n_resamples < 1:
        raise ValueError("matching video/difference lengths and positive resamples required")
    grouped: dict[str, list[float]] = defaultdict(list)
    for video_id, difference in zip(video_ids, differences):
        if not isinstance(video_id, str) or not math.isfinite(float(difference)):
            raise ValueError("video IDs must be strings and differences finite")
        grouped[video_id].append(float(difference))
    if not grouped:
        return {"estimate": None, "ci95": None, "n_questions": 0, "n_videos": 0,
                "n_resamples": n_resamples, "seed": seed, "statistically_positive": False}
    clusters = [(sum(grouped[v]), len(grouped[v])) for v in sorted(grouped)]
    generator = random.Random(seed)
    draws = []
    for _ in range(n_resamples):
        selected = [clusters[generator.randrange(len(clusters))] for _ in clusters]
        draws.append(sum(total for total, _ in selected) / sum(count for _, count in selected))
    interval = [_quantile(draws, .025), _quantile(draws, .975)]
    return {"estimate": mean(differences), "ci95": interval, "n_questions": len(differences),
            "n_videos": len(clusters), "n_resamples": n_resamples, "seed": seed,
            "statistically_positive": interval[0] > 0,
            "limitation": "single video: interval has no between-video information" if len(clusters) < 2 else None}


def _score(row: Mapping[str, Any]) -> int:
    if row.get("abstained") is True or (isinstance(row.get("answer"), str) and not row["answer"].strip()):
        return 0
    return int(row.get("status") in SUCCESS_STATES and row.get("verdict") == "correct"
               and row.get("parse_ok", True) is not False and not row.get("truncated", False))


def _mean(values: Sequence[float]) -> float | None:
    return mean(values) if values else None


def _planned_index(planned: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {}
    for question in planned:
        question_id = question["question_id"]
        if question_id in result or not isinstance(question["video_id"], str):
            raise ValueError("planned question IDs must be globally unique and video IDs strings")
        result[question_id] = question
    return result


def _result_index(rows: Sequence[Mapping[str, Any]], planned: Mapping[str, Any],
                  condition_key: str, allowed: Mapping[str, Sequence[str]]) -> dict[tuple[str, str], dict[str, Any]]:
    index = {}
    for row in rows:
        question_id, condition = row["question_id"], row[condition_key]
        if question_id not in planned or condition not in allowed[question_id]:
            raise ValueError(f"unplanned final result: {(question_id, condition)}")
        key = (question_id, condition)
        if key in index:
            raise ValueError(f"duplicate logical result {key}; physical attempts must not enter aggregation")
        if "video_id" in row and row["video_id"] != planned[question_id]["video_id"]:
            raise ValueError("result video ID disagrees with frozen manifest")
        index[key] = dict(row)
    for question_id, conditions in allowed.items():
        for condition in conditions:
            index.setdefault((question_id, condition), {"question_id": question_id,
                             condition_key: condition, "status": "missing", "verdict": None,
                             "failure_reason": "missing_final_logical_result", "citations_legal": False})
    return index


def _condition_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    uncertain = [r for r in rows if r.get("verdict") == "uncertain"]
    resolved = [r for r in rows if r.get("verdict") != "uncertain"]
    return {"n_planned": len(rows), "n_correct": sum(_score(r) for r in rows),
            "accuracy": _mean([_score(r) for r in rows]),
            "n_execution_success": sum(r.get("status") in SUCCESS_STATES for r in rows),
            "n_missing": sum(r.get("status") == "missing" for r in rows),
            "n_uncertain": len(uncertain), "uncertain_rate": len(uncertain) / len(rows) if rows else None,
            "accuracy_excluding_uncertain": _mean([_score(r) for r in resolved]),
            "n_excluding_uncertain": len(resolved),
            "n_legal_citations": sum(r.get("citations_legal") is True for r in rows),
            "citations_legal_rate": _mean([int(r.get("citations_legal") is True) for r in rows]),
            "status_counts": dict(Counter(r.get("status", "missing_status") for r in rows)),
            "failure_reasons": dict(Counter(r.get("failure_reason") or r.get("error") or r.get("status", "missing_status")
                                    for r in rows if r.get("status") not in SUCCESS_STATES))}


def _checks_summary(checks: Mapping[str, Any] | None) -> dict[str, Any]:
    actual = checks or {}
    values = {name: actual.get(name, "未运行") for name in CORE_CHECKS}
    return {"checks": values, "all_passed": all(v is True or v == "PASS" for v in values.values())}


def _d0_calibration(calibration: Mapping[str, Any] | None) -> dict[str, Any]:
    values = dict(calibration or {})
    audited, agreement = values.get("n_audited", 0), values.get("n_agreed", 0)
    passed = (values.get("reviewer_type") == "human" and audited == 32
              and isinstance(agreement, int) and 28 <= agreement <= audited)
    return {**values, "passed": passed, "status": "PASS" if passed else "未通过或未运行",
            "required": "human agreement >=28 of the frozen 32 anonymous dev answers"}


def aggregate_e1(planned_questions: Sequence[Mapping[str, Any]],
                  condition_rows: Sequence[Mapping[str, Any]],
                  audits: Sequence[Mapping[str, Any]] = (),
                  protocol_checks: Mapping[str, Any] | None = None,
                  d0_calibration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return main E1 table and per-question records; automatic != human confirmed.

Planned rows require ``num_gold_groups`` (or ``m``), and optional
``intervention_valid``. A pair is valid only if all final rows explicitly say
``intervention_valid=True`` or the planned row says so, all conditions finish,
and all answers parse without truncation. Human confirmations require
``reviewer_type='human'`` and six explicit checks, never a generic ``confirmed``.
"""
    planned = _planned_index(planned_questions)
    groups = {}
    for q,row in planned.items():
        fallback_groups = row.get("gold_groups")
        if fallback_groups is None:
            fallback_groups = merge_evidence_intervals([e["timestamp"] for e in row.get("evidence", [])])
        groups[q] = int(row.get("num_gold_groups", row.get("m", len(fallback_groups))))
    if any(not 0 <= m <= 4 for m in groups.values()):
        raise ValueError("E1 num_gold_groups must be 0..4; <2 remains invalid in the planned denominator")
    allowed = {q: ["Full", *[f"Key-{i+1}" for i in range(m)], "Irrel-1", "Irrel-2", "Blind"]
               for q, m in groups.items()}
    index = _result_index(condition_rows, planned, "condition", allowed)
    audit_index = {}
    for audit in audits:
        if audit.get("kind", "e1_joint") != "e1_joint":
            continue
        q = audit["question_id"]
        if q not in planned or q in audit_index:
            raise ValueError("unplanned or duplicate E1 final audit")
        audit_index[q] = audit
    pairs = []
    human_checks = ("distinct_necessary_facts", "visually_resolved", "no_text_leakage",
                    "no_alternative_distractor_path", "reference_valid", "citation_and_format_valid")
    for q, question in planned.items():
        rows = [index[q, c] for c in allowed[q]]
        explicit_valid = all(r.get("intervention_valid", question.get("intervention_valid", False)) is True for r in rows)
        execution_complete = all(r.get("status") in SUCCESS_STATES and r.get("parse_ok", True) is not False
                                 and not r.get("truncated", False) for r in rows)
        valid = groups[q] >= 2 and explicit_valid and execution_complete
        scores = {c: _score(index[q, c]) for c in allowed[q]}
        full, blind = scores["Full"], scores["Blind"]
        key_scores = [scores[f"Key-{i+1}"] for i in range(groups[q])]
        irrel_scores = [scores["Irrel-1"], scores["Irrel-2"]]
        delta_key = full - mean(key_scores) if valid else None
        delta_irrel = full - mean(irrel_scores) if valid else None
        candidate = bool(valid and full == 1 and blind == 0 and irrel_scores == [1, 1]
                         and key_scores.count(0) >= 2
                         and all(r.get("verdict") in ("correct","incorrect") for r in rows)
                         and all(r.get("citations_legal") is True for r in rows))
        audit = audit_index.get(q, {})
        confirmed = candidate and audit.get("reviewer_type") == "human" and all(audit.get(k) is True for k in human_checks)
        reasons = []
        if groups[q] < 2:
            reasons.append("fewer_than_two_event_groups")
        if not explicit_valid:
            reasons.append(question.get("invalid_reason") or "intervention_not_validated")
        if not execution_complete:
            reasons.extend(sorted(set(r.get("failure_reason") or r.get("error") or r.get("status", "missing_status")
                                     for r in rows if r.get("status") not in SUCCESS_STATES)))
            if any(r.get("parse_ok") is False or r.get("truncated") for r in rows):
                reasons.append("parse_failure_or_truncation")
        pairs.append({"question_id": q, "video_id": question["video_id"], "num_gold_groups": groups[q],
                      "construction_available": groups[q] >= 2 and explicit_valid,
                      "valid_pair": valid, "invalid_reasons": reasons, "scores": scores,
                      "delta_key": delta_key, "delta_irrel": delta_irrel,
                      "D": delta_key - delta_irrel if valid else None,
                      "full_minus_blind": full - blind if valid else None,
                      "automatic_joint_candidate": candidate, "human_confirmed": bool(confirmed),
                      "audit_status": "human_confirmed" if confirmed else "pending" if not audit else "reviewed_unconfirmed",
                      "any_uncertain": any(r.get("verdict") == "uncertain" for r in rows)})
    valid = [p for p in pairs if p["valid_pair"]]
    available = [p for p in pairs if p["construction_available"]]
    confirmed = [p for p in pairs if p["human_confirmed"]]
    candidates = [p for p in pairs if p["automatic_joint_candidate"]]
    def boot(rows, key):
        return video_cluster_paired_bootstrap([r["video_id"] for r in rows], [r[key] for r in rows])
    primary = boot(valid, "D")
    full_blind = boot(valid, "full_minus_blind")
    checks = _checks_summary(protocol_checks)
    calibration = _d0_calibration(d0_calibration)
    nplan = len(planned)
    construction = len(valid) >= 36 and len({r["video_id"] for r in valid}) >= 10
    standard_size = len(available) >= 60 and len({q["video_id"] for q in available}) >= 15
    full_accuracy = _mean([p["scores"]["Full"] for p in valid])
    consumer_ok = full_accuracy is not None and full_accuracy >= .6 and full_blind["estimate"] >= .15
    joint_ok = (primary["estimate"] is not None and primary["estimate"] >= .15
                and len(confirmed) >= max(12, math.ceil(.15*nplan))
                and len({p["video_id"] for p in confirmed}) >= 6)
    effective = standard_size and construction and checks["all_passed"]
    conditions = sorted({c for seq in allowed.values() for c in seq})
    return {"experiment": "E1", "score_label": "local same-model judge pilot; not official scoring",
            "n_planned": nplan, "n_planned_videos": len({q["video_id"] for q in planned.values()}),
            "n_available_questions": len(available), "n_available_videos": len({q["video_id"] for q in available}),
            "n_valid_pairs": len(valid), "n_valid_videos": len({r["video_id"] for r in valid}),
            "condition_table": {c: _condition_summary([index[q,c] for q in planned if c in allowed[q]]) for c in conditions},
            "paired_full_accuracy": full_accuracy, "primary_D": primary,
            "mean_delta_key": _mean([r["delta_key"] for r in valid]),
            "mean_delta_irrel": _mean([r["delta_irrel"] for r in valid]),
            "full_minus_blind": full_blind,
            "sensitivity_excluding_uncertain_D": boot([r for r in valid if not r["any_uncertain"]], "D"),
            "n_automatic_candidates": len(candidates), "n_human_confirmed": len(confirmed),
            "n_human_confirmed_videos": len({p["video_id"] for p in confirmed}),
            "human_confirmed_rate_planned": len(confirmed)/nplan if nplan else None,
            "human_confirmed_rate_valid": len(confirmed)/len(valid) if valid else None,
            "audit_queue": fixed_hash_order([p["question_id"] for p in candidates])[:24],
            "scientific_protocol": checks,
            "d0_judge_calibration": calibration,
            "scientific_validity_passed": bool(effective and calibration["passed"]),
            "gates": {"standard_sample": standard_size, "valid_intervention_count": construction,
                      "consumer_visual_entry": bool(consumer_ok), "joint_signal": bool(joint_ok),
                      "strong_joint_signal": bool(joint_ok and len(confirmed) >= math.ceil(.3*nplan))},
            "engineering_status": "COMPLETE" if effective else "INCOMPLETE",
            "research_judgment": "CONTINUE" if effective and calibration["passed"] and consumer_ok and joint_ok else "INCONCLUSIVE",
            "pairs": pairs}


def paired_method_difference(planned_questions: Sequence[Mapping[str, Any]],
                              rows: Mapping[tuple[str, str], Mapping[str, Any]],
                              left: str, right: str, metric: str = "A",
                              question_ids: Sequence[str] | None = None) -> dict[str, Any]:
    planned = _planned_index(planned_questions)
    selected = list(planned) if question_ids is None else list(question_ids)
    videos, differences, gains, losses = [], [], [], []
    for q in selected:
        a, b = rows[q,left], rows[q,right]
        av = _score(a) if metric == "A" else int(a.get(metric) is True)
        bv = _score(b) if metric == "A" else int(b.get(metric) is True)
        videos.append(planned[q]["video_id"])
        differences.append(av-bv)
        if av > bv:
            gains.append(q)
        elif av < bv:
            losses.append(q)
    return {**video_cluster_paired_bootstrap(videos, differences), "left": left, "right": right,
            "metric": metric, "net_gain_questions": len(gains)-len(losses),
            "n_gain_questions": len(gains), "n_loss_questions": len(losses),
            "gain_question_ids": gains, "loss_question_ids": losses,
            "n_gain_videos": len({planned[q]["video_id"] for q in gains})}


def e2_failure_category(row: Mapping[str, Any], rstar: Mapping[str, Any]) -> str:
    """Ordered attribution against known annotation paths only."""
    if row.get("full_candidates_ann") is False:
        return "frontend_or_data_not_captured"
    if row.get("full_candidates_ann") is True and row.get("stored_ann") is False:
        return "known_path_not_stored"
    if row.get("stored_ann") is True and row.get("feasible_ann") is False:
        return "read_budget_infeasible"
    if row.get("status") not in SUCCESS_STATES or row.get("parse_ok") is False or row.get("truncated"):
        return "method_execution_or_parse_failure"
    if not _score(row) and _score(rstar) and row.get("access_ann") is False:
        return "observed_repairable_read_gap"
    rstar_failed_answer = rstar.get("status") in SUCCESS_STATES and rstar.get("verdict") in ("incorrect", "uncertain")
    if not _score(row) and (row.get("access_ann") is True or rstar_failed_answer):
        return "consumer_representation_or_injection_unresolved"
    return "success" if _score(row) else "insufficient_diagnostic_information"


def aggregate_e2(planned_questions: Sequence[Mapping[str, Any]],
                  method_rows: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] = (),
                  protocol_checks: Mapping[str, Any] | None = None,
                  d0_calibration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """All frozen questions remain in all-method accuracy, including failures.

Missing costs/feasibility are reported as unknown and block fairness/sample
gates; they are never filled with plausible zeros. R-star uses method ``R*``.
"""
    planned = _planned_index(planned_questions)
    methods = ("R0", "R1", "R2", "R*")
    index = _result_index(method_rows, planned, "method", {q: methods for q in planned})
    table, feasible, unknown_feasible = {}, [], []
    for q in planned:
        values = [index[q,m].get("feasible_ann") for m in methods]
        known = [v for v in values if isinstance(v, bool)]
        if len(set(known)) > 1:
            raise ValueError(f"methods disagree on snapshot feasibility: {q}")
        if known:
            if known[0]:
                feasible.append(q)
        else:
            unknown_feasible.append(q)
        for field in ("snapshot_hash", "stored_ann"):
            known_values = [index[q,m][field] for m in methods if field in index[q,m]]
            if len(set(known_values)) > 1:
                raise ValueError(f"methods do not share {field}: {q}")
    for method in methods:
        rows = [index[q,method] for q in planned]
        for row in rows:
            for field in ("logical_tokens", "logical_calls", "physical_tokens", "physical_calls", "latency_s", "logical_latency_s", "physical_latency_s"):
                if field in row and (not isinstance(row[field], (int,float)) or isinstance(row[field], bool)
                                     or not math.isfinite(row[field]) or row[field] < 0):
                    raise ValueError(f"invalid cost field {field}: {row[field]!r}")
        costs = [r["logical_tokens"] for r in rows if isinstance(r.get("logical_tokens"), (int,float))]
        table[method] = {**_condition_summary(rows),
                         "n_access_ann": sum(r.get("access_ann") is True for r in rows),
                         "access_ann": _mean([int(r.get("access_ann") is True) for r in rows]),
                         "n_unknown_access_ann": sum(not isinstance(r.get("access_ann"), bool) for r in rows),
                         "access_ann_feasible": _mean([int(index[q,method].get("access_ann") is True) for q in feasible]),
                         "n_feasible_denominator": len(feasible),
                         "J_ann": _mean([_score(r)*int(r.get("access_ann") is True)*int(r.get("citations_legal") is True) for r in rows]),
                         "n_known_costs": len(costs), "mean_logical_tokens": _mean(costs),
                         "total_logical_tokens_known": sum(costs),
                         "total_logical_calls_known": sum(r.get("logical_calls", 0) for r in rows),
                         "total_physical_calls_known": sum(r.get("physical_calls", 0) for r in rows),
                         "total_physical_tokens_known": sum(r.get("physical_tokens", 0) for r in rows),
                         "control_fallback_count": sum(r.get("control_fallback",(r.get("control") or {}).get("fallback")) is True for r in rows),
                         "control_parse_failure_count": sum(r.get("control_parse_ok",(r.get("control") or {}).get("parse_ok")) is False for r in rows),
                         "mean_latency_s_known": _mean([r.get("logical_latency_s",r.get("latency_s")) for r in rows
                                                       if isinstance(r.get("logical_latency_s",r.get("latency_s")), (int,float))]),
                         "physical_latency_s_known": sum(r.get("physical_latency_s",0) for r in rows),
                         "peak_cuda_reserved_bytes": max((r.get("peak_cuda_reserved_bytes",0) for r in rows), default=0),
                         "failure_categories": dict(Counter(e2_failure_category(index[q,method], index[q,"R*"]) for q in planned))}
    def diff(left, right, metric="A", ids=None):
        return paired_method_difference(planned_questions, index, left, right, metric, ids)
    primary, read_space = diff("R2","R1"), diff("R*","R1",ids=feasible)
    access = diff("R2","R1","access_ann",feasible)
    vs_r0 = diff("R2","R0")
    paired_resolved = [q for q in planned if all(index[q,m].get("verdict") != "uncertain" for m in ("R1","R2"))]
    r1, r2 = table["R1"]["mean_logical_tokens"], table["R2"]["mean_logical_tokens"]
    # Freeze an explicit conservative denominator: relative to the cheaper mean.
    cost_complete = table["R1"]["n_known_costs"] == len(planned) == table["R2"]["n_known_costs"] and bool(planned)
    relative_gap = abs(r2-r1)/min(r1,r2) if cost_complete and r1 and r2 else None
    fairness = relative_gap is not None and relative_gap <= .05
    audit_map = {}
    for audit in audits:
        if audit.get("kind", "e2_gain") != "e2_gain":
            continue
        q = audit["question_id"]
        if q not in primary["gain_question_ids"] or q in audit_map:
            raise ValueError("E2 audit must identify a unique R2 gain question")
        audit_map[q] = audit
    audit_queue = fixed_hash_order(primary["gain_question_ids"])[:12]
    human_audited = [q for q in audit_queue if audit_map.get(q,{}).get("reviewer_type") == "human"
                     and isinstance(audit_map[q].get("new_evidence_explains_gain"), bool)]
    explained = [q for q in human_audited if audit_map[q]["new_evidence_explains_gain"]]
    grounding = len(human_audited) >= 8 and len(human_audited) == len(audit_queue) and len(explained)/len(human_audited) >= .8
    n_recorded_questions = sum(all(index[q,m].get("status") in TERMINAL_STATES for m in methods) for q in planned)
    completed_videos = {planned[q]["video_id"] for q in planned if all(index[q,m].get("status") in TERMINAL_STATES for m in methods)}
    standard_size = n_recorded_questions >= 60 and len(completed_videos) >= 15
    checks = _checks_summary(protocol_checks)
    calibration = _d0_calibration(d0_calibration)
    violations = sum(r.get("budget_violation", False) is True or r.get("logical_tokens", 0) > 12288
                     or r.get("logical_calls", 0) > (2 if r["method"] in ("R1","R2") else 1)
                     for r in index.values())
    complete = standard_size and checks["all_passed"] and violations == 0
    space_ok = (len(feasible) >= 24 and len({planned[q]["video_id"] for q in feasible}) >= 8
                and read_space["estimate"] is not None and read_space["estimate"] >= .1
                and read_space["net_gain_questions"] >= 4)
    signal = (primary["estimate"] is not None and primary["estimate"] >= .05 and primary["net_gain_questions"] >= 4
              and primary["n_gain_videos"] >= 3 and access["estimate"] is not None and access["estimate"] >= .1
              and vs_r0["estimate"] >= -.02)
    return {"experiment": "E2", "score_label": "local same-model judge pilot; not official scoring",
            "coverage_label": "annotation time-group proxy; J_ann is not proven grounded success",
            "rstar_label": "annotation-assisted injection reference; not a mathematical upper bound",
            "n_planned": len(planned), "n_planned_videos": len({q["video_id"] for q in planned.values()}),
            "n_recorded_questions": n_recorded_questions, "n_recorded_videos": len(completed_videos),
            "n_feasible_ann": len(feasible), "n_feasible_videos": len({planned[q]["video_id"] for q in feasible}),
            "n_unknown_feasibility": len(unknown_feasible), "method_table": table,
            "primary_R2_minus_R1": primary, "Rstar_minus_R1_feasible": read_space,
            "access_R2_minus_R1_feasible": access, "R2_minus_R0": vs_r0,
            "sensitivity_R2_minus_R1_excluding_uncertain": diff("R2","R1",ids=paired_resolved),
            "relative_mean_logical_token_gap": relative_gap,
            "token_gap_denominator": "min(mean_R1,mean_R2)", "cost_records_complete": cost_complete,
            "audit_queue": audit_queue, "n_human_audited_gains": len(human_audited),
            "n_human_evidence_explained_gains": len(explained),
            "scientific_protocol": checks, "budget_violations": violations,
            "d0_judge_calibration": calibration,
            "scientific_validity_passed": bool(complete and calibration["passed"] and fairness),
            "gates": {"standard_sample": standard_size, "read_space": bool(space_ok),
                      "combination_signal": bool(signal), "token_fairness": bool(fairness), "human_grounding": bool(grounding)},
            "engineering_status": "COMPLETE" if complete else "INCOMPLETE",
            "research_judgment": "CONTINUE" if complete and calibration["passed"] and space_ok and signal and fairness and grounding else "INCONCLUSIVE",
            "results": [index[q,m] for q in planned for m in methods]}
