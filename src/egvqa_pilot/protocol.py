"""CPU-only scientific protocol for the preregistered EG-VQA pilot.

No function in this module opens videos, model files, or gold annotations.
Reader selection consumes only supplied live IDs and embeddings. Coverage and
R-star are evaluator-only helpers and must not run in a normal reader process.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence


def merge_evidence_intervals(intervals: Iterable[Sequence[float]]) -> list[tuple[float, float]]:
    """Merge strict overlaps; distinct intervals that only touch stay separate."""
    clean = []
    for interval in intervals:
        if len(interval) != 2:
            raise ValueError("evidence intervals must contain start and end")
        start, end = map(float, interval)
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            raise ValueError(f"invalid evidence interval: {interval!r}")
        clean.append((start, end))
    merged: list[tuple[float, float]] = []
    for start, end in sorted(clean):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not len(left):
        raise ValueError("embedding dimensions must match and be nonzero")
    a, b = [float(x) for x in left], [float(x) for x in right]
    if not all(math.isfinite(x) for x in a + b):
        raise ValueError("embedding contains nonfinite values")
    na, nb = math.sqrt(sum(x*x for x in a)), math.sqrt(sum(x*x for x in b))
    if not na or not nb:
        raise ValueError("zero embedding is not a valid normalized retrieval key")
    return sum(x*y for x, y in zip(a, b)) / (na * nb)


def _key_map(ids: Sequence[str], keys: Sequence[Sequence[float]]) -> dict[str, Sequence[float]]:
    if len(ids) != len(keys) or len(set(ids)) != len(ids):
        raise ValueError("IDs must be unique and match the number of embeddings")
    if any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("capsule IDs must be nonempty strings")
    return dict(zip(ids, keys))


def rank_topk(ids: Sequence[str], keys: Sequence[Sequence[float]], query: Sequence[float],
              k: int, exclude: Iterable[str] = ()) -> list[str]:
    """Cosine descending, exact ties broken by ascending capsule ID."""
    if k < 0:
        raise ValueError("k must be nonnegative")
    by_id, blocked = _key_map(ids, keys), set(exclude)
    ranked = sorted(((cosine(key, query), i) for i, key in by_id.items() if i not in blocked),
                    key=lambda item: (-item[0], item[1]))
    return [i for _, i in ranked[:k]]


def select_r2(ids: Sequence[str], keys: Sequence[Sequence[float]],
              gap_keys: Sequence[Sequence[float]], initial_ids: Sequence[str]) -> dict[str, Any]:
    """Top-6 per gap, max-relevance pool <=8, exhaustive 3-item complement.

The caller parses/falls back to the original question *before* encoding. One or
two valid query embeddings are required. If fewer than three unread entries
exist, the same all-available rule used by R1 applies.
"""
    if not 1 <= len(gap_keys) <= 2:
        raise ValueError("R2 needs one or two valid (possibly fallback) query embeddings")
    by_id = _key_map(ids, keys)
    if len(set(initial_ids)) != len(initial_ids) or not set(initial_ids) <= set(ids):
        raise ValueError("initial IDs must be unique live capsule IDs")
    pool = set()
    for query in gap_keys:
        pool.update(rank_topk(ids, keys, query, 6, initial_ids))
    relevance = {i: max(cosine(by_id[i], q) for q in gap_keys) for i in pool}
    candidates = sorted(pool, key=lambda i: (-relevance[i], i))[:8]
    n_select = min(3, len(candidates))
    choices = []
    for selected in combinations(sorted(candidates), n_select):
        coverage = sum(max((cosine(by_id[i], q) for i in selected), default=0.) for q in gap_keys)
        pairs = list(combinations(selected, 2))
        redundancy = sum(cosine(by_id[i], by_id[j]) for i, j in pairs) / len(pairs) if pairs else 0.
        choices.append((coverage - 0.2 * redundancy, selected))
    score, selected = min(choices, key=lambda item: (-item[0], item[1]))
    return {"selected_ids": list(selected), "candidate_ids": candidates, "score": score,
            "enumerated_combinations": len(choices), "query_count": len(gap_keys)}


def capsule_coverage_mask(pts: Sequence[float | None], valid_mask: Sequence[bool],
                          groups: Sequence[Sequence[float]]) -> int:
    """Conservative annotation proxy: >=2 distinct real PTS in one capsule.

Time intervals use [start,end), consistently with capsule ownership. Padding
and duplicate PTS never create a second piece of evidence.
"""
    if len(pts) != len(valid_mask):
        raise ValueError("PTS and valid-mask lengths differ")
    effective = set()
    for timestamp, valid in zip(pts, valid_mask):
        if valid:
            if timestamp is None or not math.isfinite(float(timestamp)):
                raise ValueError("valid frame requires a finite actual PTS")
            effective.add(float(timestamp))
    result = 0
    for j, (start, end) in enumerate(groups):
        if not 0 <= start < end:
            raise ValueError("invalid coverage group")
        if sum(start <= t < end for t in effective) >= 2:
            result |= 1 << j
    return result


def packet_coverage_mask(selected_ids: Sequence[str], coverage_masks: Mapping[str, int]) -> int:
    result = 0
    for capsule_id in selected_ids:
        if capsule_id not in coverage_masks:
            raise ValueError(f"unknown capsule ID: {capsule_id}")
        result |= coverage_masks[capsule_id]
    return result


def select_rstar(ids: Sequence[str], coverage_masks: Mapping[str, int],
                 relevance_ids: Sequence[str], num_groups: int,
                 max_items: int = 6) -> dict[str, Any]:
    """Evaluator-only minimal full cover, else maximum coverage; pad by R0.

Ties among equal-size covers use sorted ID tuples. An infeasible reference
remains a diagnostic row, never a claimed upper bound. ``minimum_cover_size``
is computed without the packet cap to separate storage and read-budget loss.
"""
    if not 1 <= num_groups <= 4 or max_items < 0:
        raise ValueError("R-star requires 1..4 annotation groups and a nonnegative cap")
    if len(set(ids)) != len(ids) or set(ids) != set(coverage_masks):
        raise ValueError("coverage must describe exactly the live capsule IDs")
    if len(set(relevance_ids)) != len(relevance_ids) or set(relevance_ids) != set(ids):
        raise ValueError("relevance order must be a permutation of live IDs")
    target = (1 << num_groups) - 1
    if any(not isinstance(m, int) or m < 0 or m & ~target for m in coverage_masks.values()):
        raise ValueError("coverage masks have unknown group bits")
    dp: dict[int, tuple[str, ...]] = {0: ()}
    for capsule_id in sorted(ids):
        for mask, chosen in list(dp.items()):
            new_mask = mask | coverage_masks[capsule_id]
            new_chosen = chosen + (capsule_id,)
            if new_mask not in dp or (len(new_chosen), new_chosen) < (len(dp[new_mask]), dp[new_mask]):
                dp[new_mask] = new_chosen
    stored = target in dp
    minimum = len(dp[target]) if stored else None
    feasible = stored and minimum <= max_items
    if feasible:
        selected = list(dp[target])
    else:
        mask, chosen = min(((mask, chosen) for mask, chosen in dp.items() if len(chosen) <= max_items),
                           key=lambda item: (-item[0].bit_count(), len(item[1]), item[1]))
        selected = list(chosen)
    selected.extend(i for i in relevance_ids if i not in selected)
    selected = selected[:max_items]
    covered = packet_coverage_mask(selected, coverage_masks)
    return {"selected_ids": selected, "stored_ann": stored, "feasible_ann": feasible,
            "covered_mask": covered, "target_mask": target,
            "minimum_cover_size": minimum, "access_ann": covered == target}


def _json_object(text: str) -> dict[str, Any]:
    # Permit one surrounding JSON fence, never salvage arbitrary fragments.
    clean = text.strip()
    if clean.startswith("```json\n") and clean.endswith("```"):
        clean = clean[len("```json\n"):-3].strip()
    elif clean.startswith("```\n") and clean.endswith("```"):
        clean = clean[len("```\n"):-3].strip()
    value = json.loads(clean)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def parse_answer(text: str, allowed_ids: Iterable[str]) -> dict[str, Any]:
    """Empty text is a valid abstention; malformed fields remain parse failures.

Illegal citations are reported separately and do not erase a parsed answer.
"""
    try:
        obj = _json_object(text)
        answer, citations = obj["answer"], obj["citations"]
        if not isinstance(answer, str):
            raise ValueError("answer must be text")
        if not isinstance(citations, list) or any(not isinstance(i, str) for i in citations):
            raise ValueError("citations must be a list of ID strings")
        allowed = set(allowed_ids)
        illegal = sorted(set(citations) - allowed)
        return {"parse_ok": True, "answer": answer.strip(), "citations": citations,
                "citations_legal": not illegal, "illegal_citations": illegal, "parse_error": None,
                "abstained": not bool(answer.strip())}
    except (ValueError, KeyError, TypeError) as exc:
        return {"parse_ok": False, "answer": "", "citations": [],
                "citations_legal": False, "illegal_citations": [], "parse_error": str(exc),
                "abstained": False}


def parse_control(text: str, question: str, method: str) -> dict[str, Any]:
    """Parse one R1 or up to two R2 queries; normalize a single JSON string.

Both a nonempty string and a one-element list express one retrieval statement.
Normalization is recorded explicitly; invalid or empty values still fall back.
"""
    if method not in ("R1", "R2") or not question.strip():
        raise ValueError("method must be R1/R2 and fallback question nonempty")
    limit = 1 if method == "R1" else 2
    try:
        obj = _json_object(text)
        queries = obj["queries"]
        normalized_from_string = isinstance(queries, str)
        if normalized_from_string:
            queries = [queries]
        if not isinstance(queries, list) or not 1 <= len(queries) <= limit:
            raise ValueError(f"queries must contain 1..{limit} strings")
        if any(not isinstance(q, str) or not q.strip() for q in queries):
            raise ValueError("queries must be nonempty text")
        unique = list(dict.fromkeys(q.strip() for q in queries))
        return {"queries": unique, "parse_ok": True, "fallback": False, "parse_error": None,
                "normalized_from_string": normalized_from_string}
    except (ValueError, KeyError, TypeError) as exc:
        return {"queries": [question.strip()], "parse_ok": False,
                "fallback": True, "parse_error": str(exc), "normalized_from_string": False}


def parse_judge(text: str, expected_ids: Sequence[str]) -> list[dict[str, Any]]:
    """At most four anonymous answers; missing/invalid verdicts remain uncertain.

Unknown or duplicate IDs invalidate the entire batch, preventing silent answer
permutation. A missing ID only invalidates that item and remains in the result.
"""
    if not 1 <= len(expected_ids) <= 4 or len(set(expected_ids)) != len(expected_ids):
        raise ValueError("judge batches require 1..4 unique anonymous IDs")
    found: dict[str, dict[str, Any]] = {}
    batch_error = None
    try:
        rows = _json_object(text)["results"]
        if not isinstance(rows, list):
            raise ValueError("judge results must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("judge item must be an object")
            item_id = row.get("id")
            if not isinstance(item_id, str) or item_id not in expected_ids or item_id in found:
                raise ValueError("unknown or duplicate anonymous judge ID")
            verdict, reason = row.get("verdict"), row.get("reason")
            if verdict not in ("correct", "incorrect", "uncertain") or not isinstance(reason, str) or not reason.strip():
                found[item_id] = {"id": item_id, "verdict": "uncertain", "reason": "invalid judge item", "parse_ok": False}
            else:
                found[item_id] = {"id": item_id, "verdict": verdict, "reason": reason.strip(), "parse_ok": True}
    except (ValueError, KeyError, TypeError) as exc:
        batch_error = str(exc)
    return [({"id": i, "verdict": "uncertain", "reason": batch_error or "missing judge item", "parse_ok": False}
             if batch_error or i not in found else found[i]) for i in expected_ids]


def anonymous_judge_batch(items: Sequence[Mapping[str, str]], seed: int = 43) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Construct rubric inputs without condition/method labels (<=4 items).

``item_id`` maps back to the evaluator's result ID; only question, reference,
prediction and a fresh anonymous ID enter the judge prompt.
"""
    import random
    if not 1 <= len(items) <= 4 or len({r["item_id"] for r in items}) != len(items):
        raise ValueError("one to four distinct answer items required")
    order = list(items)
    random.Random(seed).shuffle(order)
    blinded, mapping = [], {}
    for j, row in enumerate(order):
        anon = f"a{j}"
        mapping[anon] = row["item_id"]
        blinded.append({"id": anon, "question": row["question"], "reference": row["reference"],
                        "prediction": row["prediction"]})
    return blinded, mapping


def fixed_hash_order(ids: Iterable[str], seed: int = 43) -> list[str]:
    return sorted(ids, key=lambda x: (hashlib.sha256(f"{seed}:{x}".encode()).hexdigest(), x))


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class BudgetEntry:
    request_id: str
    phase: str
    question_id: str
    method: str
    condition: str
    role: str
    attempt: int
    input_tokens: int
    max_output_tokens: int
    physical_request: bool
    state: str = "reserved"
    output_tokens: int | None = None
    error: str | None = None
    measured_output: bool = False

    @property
    def charged_tokens(self) -> int:
        return self.input_tokens + (self.max_output_tokens if self.output_tokens is None else self.output_tokens)


class BudgetLedger:
    """Reservation-first ledger; retries and cache hits both consume logical cost.

The VLM is called only after ``reserve`` succeeds. Pending/unknown outputs are
conservatively charged at their full generation cap. Offline judge requests use
``role='judge'`` and never consume a reader's per-question tokens/calls. They
    still consume physical global quotas. Persist ``records()`` after reservation
    and after finalization, so a crashed request cannot disappear on resume.
    ``RESERVE`` records up to 100 physical core contingency/dev verification
    calls separately from the original 50-call D0 profiling quota; core and
    whole-run caps still apply.
"""

    def __init__(self, *, request_token_limit: int = 8192, e2_token_limit: int = 12288,
                 core_physical_limit: int = 1400, total_physical_limit: int = 1800,
                 e3_physical_limit: int = 400, d0_physical_limit: int = 50,
                 reserve_physical_limit: int = 100):
        self.request_token_limit = request_token_limit
        self.e2_token_limit = e2_token_limit
        self.core_physical_limit = core_physical_limit
        self.total_physical_limit = total_physical_limit
        self.e3_physical_limit = e3_physical_limit
        self.d0_physical_limit = d0_physical_limit
        self.reserve_physical_limit = reserve_physical_limit
        self.entries: dict[str, BudgetEntry] = {}

    def _method_entries(self, phase: str, question_id: str, method: str) -> list[BudgetEntry]:
        method = "R*" if method == "Rstar" else method
        return [e for e in self.entries.values() if (e.phase, e.question_id, e.method) ==
                (phase, question_id, method) and e.role != "judge"]

    def reserve(self, *, request_id: str, phase: str, question_id: str, method: str,
                input_tokens: int, max_output_tokens: int, role: str = "answer",
                condition: str = "", physical_request: bool = True) -> BudgetEntry:
        method = "R*" if method == "Rstar" else method
        if request_id in self.entries:
            raise ValueError("request ID already exists; retry requires a new request ID")
        if phase not in ("D0", "RESERVE", "E1", "E2", "E3") or role not in ("answer", "control", "judge"):
            raise ValueError("invalid phase or model role")
        if any(not isinstance(n, int) or isinstance(n, bool) or n < 0 for n in (input_tokens, max_output_tokens)):
            raise ValueError("token counts must be nonnegative integers")
        reserved = input_tokens + max_output_tokens
        if reserved > self.request_token_limit:
            raise BudgetExceeded("single request input + full output reservation exceeds 8192-token budget")
        prior = self._method_entries(phase, question_id, method)
        if phase == "E2" and role != "judge":
            caps = {"R0": 1, "R*": 1, "Rstar": 1, "R1": 2, "R2": 2}
            if method not in caps:
                raise ValueError("E2 method must be R0/R1/R2/R*")
            if len(prior) >= caps[method]:
                raise BudgetExceeded("E2 per-method call cap includes retries and cached logical requests")
            if sum(e.charged_tokens for e in prior) + reserved > self.e2_token_limit:
                raise BudgetExceeded("E2 cumulative input/output reservation exceeds 12288-token budget")
        if physical_request:
            physical = [e for e in self.entries.values() if e.physical_request]
            if len(physical) >= self.total_physical_limit:
                raise BudgetExceeded("whole-run physical request limit reached")
            if phase == "E3":
                if sum(e.phase == "E3" for e in physical) >= self.e3_physical_limit:
                    raise BudgetExceeded("E3 physical request limit reached")
            elif sum(e.phase != "E3" for e in physical) >= self.core_physical_limit:
                raise BudgetExceeded("core physical request limit reached")
            if phase == "D0" and sum(e.phase == "D0" for e in physical) >= self.d0_physical_limit:
                raise BudgetExceeded("D0 profiling physical request limit reached")
            if phase == "RESERVE" and sum(e.phase == "RESERVE" for e in physical) >= self.reserve_physical_limit:
                raise BudgetExceeded("core reserve physical request limit reached")
        attempt = 1 + sum((e.phase, e.question_id, e.method, e.condition, e.role) ==
                          (phase, question_id, method, condition, role) for e in self.entries.values())
        entry = BudgetEntry(request_id, phase, question_id, method, condition, role, attempt,
                            input_tokens, max_output_tokens, bool(physical_request))
        self.entries[request_id] = entry
        return entry

    def finalize(self, request_id: str, *, output_tokens: int | None,
                 error: str | None = None) -> BudgetEntry:
        entry = self.entries[request_id]
        if entry.state != "reserved":
            raise ValueError("request already finalized")
        if output_tokens is not None and (not isinstance(output_tokens, int) or isinstance(output_tokens, bool) or output_tokens < 0):
            raise ValueError("output count must be a nonnegative integer or unknown")
        entry.output_tokens, entry.error = output_tokens, error
        entry.measured_output = output_tokens is not None
        entry.state = "failed" if error else "complete"
        if output_tokens is not None and output_tokens > entry.max_output_tokens:
            entry.state, entry.error = "budget_violation", "actual output exceeded generation reservation"
            raise BudgetExceeded(entry.error)
        return entry

    def method_cost(self, phase: str, question_id: str, method: str) -> dict[str, Any]:
        rows = self._method_entries(phase, question_id, method)
        return {"logical_calls": len(rows), "logical_tokens": sum(e.charged_tokens for e in rows),
                "physical_calls": sum(e.physical_request for e in rows),
                "physical_tokens": sum(e.charged_tokens for e in rows if e.physical_request),
                "cache_saved_calls": sum(not e.physical_request for e in rows),
                "unknown_output_calls": sum(e.output_tokens is None for e in rows),
                "failed_calls": sum(e.state in ("failed", "budget_violation") for e in rows)}

    def summary(self) -> dict[str, Any]:
        rows = list(self.entries.values())
        return {"logical_calls": len(rows), "physical_calls": sum(e.physical_request for e in rows),
                "core_physical_calls": sum(e.physical_request and e.phase != "E3" for e in rows),
                "e3_physical_calls": sum(e.physical_request and e.phase == "E3" for e in rows),
                "logical_tokens": sum(e.charged_tokens for e in rows),
                "physical_tokens": sum(e.charged_tokens for e in rows if e.physical_request),
                "judge_logical_tokens": sum(e.charged_tokens for e in rows if e.role == "judge"),
                "budget_violations": sum(e.state == "budget_violation" for e in rows),
                "pending_requests": sum(e.state == "reserved" for e in rows)}

    def records(self) -> list[dict[str, Any]]:
        return [{**asdict(e), "charged_tokens": e.charged_tokens} for e in self.entries.values()]

    @classmethod
    def from_records(cls, records: Sequence[Mapping[str, Any]], **limits: int) -> "BudgetLedger":
        ledger = cls(**limits)
        for row in records:
            entry = ledger.reserve(**{k: row[k] for k in ("request_id", "phase", "question_id", "method",
                                                         "input_tokens", "max_output_tokens", "role",
                                                         "condition", "physical_request")})
            if entry.attempt != row["attempt"]:
                raise ValueError("attempt sequence is inconsistent with persisted calls")
            if row["state"] != "reserved":
                ledger.finalize(row["request_id"], output_tokens=row["output_tokens"], error=row["error"])
        return ledger
