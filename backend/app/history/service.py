"""Run the history check against Supabase and save the results.

    preview()  -> compute only, writes nothing (safe to call any time)
    run()      -> compute, then for each flagged resident:
                    observations   one row per (note, signal) that supports the alert
                    alerts         one open alert per resident, updated in place on re-runs
                    alert_evidence links the alert to those observations
                    case_match_runs / case_matches  look-alike historical cases

Re-running is safe: observation ids are derived from (note, signal), the open
alert is reused, and a case-match run is reused when its evidence is unchanged.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .check import HistoryCheck, check_unit
from .match import SCORER_VERSION, build_run, match_cases, outcome_spread

# Text values written to constrained columns. Change here if your CHECK constraints differ.
ALERT_STATUS_OPEN = "open"
ASSERTION_PRESENT = "present"
OBS_DIRECTION = "worsening"

_NS = uuid.UUID("6f1c3a52-6a2b-4c55-9d43-1f0d8f0c2b7e")  # fixed namespace for stable observation ids


def _db():
    # Imported lazily so the API still starts when Supabase isn't configured.
    from .. import database
    return database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_dict(c: HistoryCheck, include_evidence: bool = True) -> Dict[str, Any]:
    d = asdict(c)
    for f in d["findings"]:
        f.pop("signals", None)
        if not include_evidence:
            f.pop("evidence", None)
    d.update(title=c.title, categories=c.categories, match_signals=c.match_signals,
             duration_days=c.duration_days)
    return d


def preview(resident_id: Optional[str] = None, as_of: Optional[datetime] = None) -> List[HistoryCheck]:
    db = _db()
    residents = db.get_residents()
    notes = db.get_care_notes()
    if resident_id:
        residents = [r for r in residents if r["id"] == resident_id]
    return check_unit(residents, notes, as_of)


# ---------------------------------------------------------------------------
def _observation_rows(c: HistoryCheck) -> List[Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for f in c.findings:
        sub, change = (f.match_key.split(".") + [None, None])[1:3]
        for ev in f.evidence:
            if not ev.note_id:
                continue
            oid = str(uuid.uuid5(_NS, f"{ev.note_id}|{f.match_key}"))
            rows[oid] = {
                "id": oid,
                "note_id": ev.note_id,
                "resident_id": c.resident_id,
                "category": f.key.split(".")[0],
                "subcategory": sub,
                "change": change,
                "direction": OBS_DIRECTION,
                "observation_text": f.reason[:500],
                "evidence_span": ev.phrase,
                "assertion": ASSERTION_PRESENT,
                "confidence": 1.0,  # rule-based extraction: matched or not
                "recorded_at": ev.recorded_at,
                "created_at": _now(),
            }
    return list(rows.values())


def _alert_row(c: HistoryCheck, alert_id: str) -> Dict[str, Any]:
    return {
        "id": alert_id,
        "resident_id": c.resident_id,
        "title": c.title,
        "summary": " ".join(c.reasons),
        "explanation": to_dict(c),
        "triggered_rules": [
            {"category": f.key, "signal": f.match_key, "persisting": f.persisting, "urgent": f.urgent,
             "recent_days": f.recent_days, "baseline_rate": f.baseline_rate,
             "recent_rate": f.recent_rate, "reason": f.reason}
            for f in c.findings if f.persisting or f.urgent
        ],
        "status": ALERT_STATUS_OPEN,
        "urgent": c.urgent,
    }


def _save_alert(c: HistoryCheck) -> Dict[str, Any]:
    db = _db()
    existing = (db.supabase.table("alerts").select("id").eq("resident_id", c.resident_id)
                .eq("status", ALERT_STATUS_OPEN).order("created_at", desc=True).limit(1).execute().data)
    alert_id = existing[0]["id"] if existing else str(uuid.uuid4())
    row = _alert_row(c, alert_id)
    if not existing:
        row["created_at"] = _now()
    alert = db.supabase.table("alerts").upsert(row).execute().data[0]

    obs = _observation_rows(c)
    if obs:
        db.supabase.table("observations").upsert(obs).execute()
    db.supabase.table("alert_evidence").delete().eq("alert_id", alert_id).execute()
    if obs:
        db.supabase.table("alert_evidence").insert(
            [{"alert_id": alert_id, "observation_id": o["id"]} for o in obs]).execute()
    return alert


def _save_matches(c: HistoryCheck, alert_id: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    db = _db()
    query = c.match_weights
    matches = match_cases(query, c.duration_days, cases)
    fingerprint = db.alert_fingerprint(alert_id, SCORER_VERSION)
    run = build_run(alert_id, fingerprint, sorted(query), c.duration_days,
                    f"{c.title} over {c.duration_days} day(s)", candidates_seen=len(cases))
    run["weights"] = {**run["weights"], "query_weights": query}
    saved = db.save_match_run(run, matches)
    by_id = {x["id"]: x for x in cases}
    return {"run_id": saved["id"], "matches": len(matches), "outcomes": outcome_spread(matches, by_id)}


def run(as_of: Optional[datetime] = None) -> Dict[str, Any]:
    """Check every resident, save alerts + evidence + similar cases. Returns a summary."""
    db = _db()
    checks = preview(as_of=as_of)
    cases = db.get_cases_for_matching()
    out = []
    for c in checks:
        row = {"resident_id": c.resident_id, "tier": c.tier, "title": c.title if c.alert else None,
               "reasons": c.reasons}
        if c.alert:
            alert = _save_alert(c)
            row["alert_id"] = alert["id"]
            row["similar_cases"] = _save_matches(c, alert["id"], cases)
        out.append(row)
    return {"as_of": checks[0].as_of if checks else None, "residents": out,
            "alerts": sum(1 for c in checks if c.alert)}
