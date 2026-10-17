"""Find past cases that looked like this resident's current pattern.

Transparent scoring, no embeddings needed:

    structured = weighted overlap of signals (weighted Jaccard): a resident's
                 persisting or urgent signals weigh 1, one-off notes weigh 0.5
    temporal   = 1 - |case days - resident days| / max(both)
    total      = 0.8 * structured + 0.2 * temporal

Only cases whose signals are worsening are compared (improving cases are
recovery records, not look-alikes). The output says what's shared, what
differs, and what happened in each case. It is context for the nurse,
not a diagnosis: the case library is fictional.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

SCORER_VERSION = "history-match-v1"
WEIGHTS = {"structured": 0.8, "temporal": 0.2, "one_off_signal": 0.5, "min_structured": 0.25, "top_k": 5}


def case_signal(o: Dict[str, Any]) -> str:
    key = o["category"]
    if o.get("subcategory"):
        key += f".{o['subcategory']}"
        if o.get("change"):
            key += f".{o['change']}"
    return key


def _label(key: str) -> str:
    return key.replace("toileting.", "").replace(".", " (") + (")" if key.count(".") >= 2 else "")


def _weights(query) -> Dict[str, float]:
    """Accept a plain list (all weight 1) or {signal: weight}."""
    return dict(query) if isinstance(query, dict) else {k: 1.0 for k in query}


def score_case(query, days: int, case: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    obs = case.get("observations") or []
    if not obs or any(o.get("direction") != "worsening" for o in obs):
        return None
    c = {case_signal(o) for o in obs}
    w = _weights(query)
    q = set(w)
    shared = q & c
    if not shared:
        return None
    union = sum(max(w.get(k, 0.0), 1.0 if k in c else 0.0) for k in q | c)
    structured = sum(w[k] for k in shared) / union
    cd = int(case.get("duration_days") or 1)
    temporal = 1 - abs(cd - days) / max(cd, days, 1)
    total = WEIGHTS["structured"] * structured + WEIGHTS["temporal"] * temporal

    differences = []
    if c - q:
        differences.append({"kind": "case_only", "text": "That case also had: " + ", ".join(_label(k) for k in sorted(c - q))})
    if q - c:
        differences.append({"kind": "resident_only", "text": "This resident also has: " + ", ".join(_label(k) for k in sorted(q - c))})
    if cd != days:
        differences.append({"kind": "duration", "text": f"That case was recorded over {cd} days; this resident's change is {days} days so far."})
    return {
        "historical_case_id": case["id"],
        "structured_score": round(structured, 4),
        "temporal_score": round(temporal, 4),
        "semantic_score": None,
        "total_score": round(total, 4),
        "shared_signals": sorted(shared),
        "case_only_signals": sorted(c - q),
        "resident_only_signals": sorted(q - c),
        "differences": differences,
    }


def match_cases(query, days: int, cases: List[Dict[str, Any]],
                top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    """Ranked look-alike cases (best first), each with rank 1..k."""
    scored = [s for s in (score_case(query, days, c) for c in cases) if s]
    scored = [s for s in scored if s["structured_score"] >= WEIGHTS["min_structured"]]
    scored.sort(key=lambda s: (-s["total_score"], -s["structured_score"], s["historical_case_id"]))
    out = scored[: top_k or WEIGHTS["top_k"]]
    for i, s in enumerate(out, 1):
        s["rank"] = i
    return out


def outcome_spread(matches: List[Dict[str, Any]], cases_by_id: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    n = Counter(cases_by_id[m["historical_case_id"]].get("outcome_category") or "unknown" for m in matches)
    return [{"outcome_category": k, "n": v} for k, v in n.most_common()]


def build_run(alert_id: str, fingerprint: str, query: List[str], days: int,
              query_text: str, candidates_seen: int) -> Dict[str, Any]:
    """Row for case_match_runs."""
    return {
        "alert_id": alert_id,
        "alert_fingerprint": fingerprint,
        "query_signals": query,
        "query_duration_days": days,
        "query_text": query_text,
        "scorer_version": SCORER_VERSION,
        "weights": WEIGHTS,
        "candidates_seen": candidates_seen,
    }
