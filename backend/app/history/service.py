"""The Hunch pipeline in one place: care notes -> history check -> alerts -> similar cases.

    preview(resident_id)   compute only, writes nothing (cached until notes change)
    run(resident_id)       compute and save: alerts, evidence, plain-language summary,
                           similar historical cases
    add_note(...)          store a care note, have Gemini read it, then re-run that resident
    read_all_notes()       have Gemini read every note that has no reading yet (catch-up)

Where data lives is decided by app.store: Supabase when backend/.env is filled in,
otherwise an in-memory copy of test_data/ (demo mode).

Re-running is safe: observation ids come from (note, signal), a resident keeps one
alert that is updated in place, a review status survives re-runs, and a dismissed
alert only comes back when the evidence changes.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..store import get_store
from . import ai_read, narrative
from . import vitals as vt
from .check import LABELS, HistoryCheck, check_unit
from .match import SCORER_VERSION, build_run, match_cases, outcome_spread

# Text values written to constrained columns (see db/migrations).
ALERT_STATUSES = ("open", "reviewed", "needs_assessment", "dismissed")
ASSERTION_PRESENT = "present"
OBS_DIRECTION = "worsening"
TIER_ORDER = {"urgent": 0, "alert": 1, "watch": 2, "baseline_limited": 3, "quiet": 4}

_lock = threading.RLock()
_cache: Optional[List[HistoryCheck]] = None


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


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None


def preview(resident_id: Optional[str] = None, as_of: Optional[datetime] = None) -> List[HistoryCheck]:
    """History check for every resident (or one). Shared as_of = newest note on the unit."""
    global _cache
    with _lock:
        if as_of is not None or _cache is None:
            s = get_store()
            checks = check_unit(s.residents(), s.notes(), as_of, vitals=s.vitals())
            if as_of is None:
                _cache = checks
        else:
            checks = _cache
    return [c for c in checks if resident_id is None or c.resident_id == resident_id]


# ---------------------------------------------------------------------------
def _observation_rows(c: HistoryCheck) -> List[Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for f in c.findings:
        sub, change = (f.match_key.split(".") + [None, None])[1:3]
        for ev in f.evidence:
            if not ev.note_id:
                continue
            oid = narrative.observation_id(ev.note_id, f.match_key)
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
                # rules: matched or not. Gemini-only finding: quote verified, meaning not.
                "confidence": 0.9 if ev.read_by == "ai" else 1.0,
                "recorded_at": ev.recorded_at,
                "created_at": _now(),
            }
    return list(rows.values())


def evidence_fingerprint(observations: List[Dict[str, Any]], vital_ids: Optional[List[str]] = None) -> str:
    """sha256 of sorted evidence ids + scorer version (same formula as database.alert_fingerprint).
    Vitals readings behind a finding count too, so new out-of-line vitals reopen a reviewed alert."""
    body: Dict[str, Any] = {"evidence": sorted(o["id"] for o in observations), "scorer": SCORER_VERSION}
    if vital_ids:
        body["vitals"] = sorted(vital_ids)
    return hashlib.sha256(json.dumps(body).encode()).hexdigest()


def _alert_row(c: HistoryCheck, alert_id: str, fingerprint: str, story: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": alert_id,
        "resident_id": c.resident_id,
        "title": c.title,
        "summary": " ".join(c.reasons),
        "explanation": {**to_dict(c), "fingerprint": fingerprint, "narrative": story},
        "triggered_rules": [
            {"category": f.key, "signal": f.match_key, "persisting": f.persisting, "urgent": f.urgent,
             "recent_days": f.recent_days, "baseline_rate": f.baseline_rate,
             "recent_rate": f.recent_rate, "reason": f.reason}
            for f in c.findings if f.persisting or f.urgent
        ],
        "urgent": c.urgent,
    }


def _save(c: HistoryCheck, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    s = get_store()
    obs = _observation_rows(c)
    fp = evidence_fingerprint(obs, [ev.vital_id for f in c.findings if f.persisting or f.urgent
                                    for ev in f.evidence if ev.vital_id])
    latest = s.latest_alert(c.resident_id)
    prev = (latest or {}).get("explanation") or {}
    same_evidence = prev.get("fingerprint") == fp

    if latest and latest["status"] == "dismissed" and same_evidence:
        return {"alert_id": latest["id"], "suppressed": True}  # nurse said "not useful"; nothing new
    new = latest is None or latest["status"] == "dismissed"
    alert_id = str(uuid.uuid4()) if new else latest["id"]

    story = prev.get("narrative") if (not new and same_evidence and prev.get("narrative")) \
        else narrative.explain_check(c, obs)
    row = _alert_row(c, alert_id, fp, story)
    if new:
        row.update(status="open", created_at=_now())
    elif latest["status"] == "reviewed" and not same_evidence:
        row["status"] = "open"  # new evidence since the nurse's review
    s.save_alert(row, obs)

    matches = match_cases(c.match_weights, c.duration_days, cases)
    run_row = build_run(alert_id, fp, sorted(c.match_weights), c.duration_days,
                        f"{c.title} over {c.duration_days} day(s)", candidates_seen=len(cases))
    run_row["weights"] = {**run_row["weights"], "query_weights": c.match_weights}
    saved = s.save_matches(run_row, matches)
    by_id = {x["id"]: x for x in cases}
    return {"alert_id": alert_id, "new": new, "explanation_source": story.get("source"),
            "similar_cases": {"run_id": saved.get("id"), "matches": len(matches),
                              "outcomes": outcome_spread(matches, by_id)}}


def run(resident_id: Optional[str] = None, as_of: Optional[datetime] = None) -> Dict[str, Any]:
    """Check residents (all, or one) and save alerts + evidence + similar cases. Returns a summary."""
    s = get_store()
    with _lock:
        invalidate()
        checks = preview(resident_id, as_of=as_of)
        cases = s.cases()
        out = []
        for c in checks:
            row: Dict[str, Any] = {"resident_id": c.resident_id, "tier": c.tier,
                                   "title": c.title if c.alert else None, "reasons": c.reasons}
            if c.alert:
                row.update(_save(c, cases))
            out.append(row)
    return {"mode": s.mode, "as_of": checks[0].as_of if checks else None, "residents": out,
            "alerts": sum(1 for r in out if r.get("alert_id") and not r.get("suppressed"))}


# ---------------------------------------------------------------------------
# Read helpers used by the API
# ---------------------------------------------------------------------------
def resident_list(q: Optional[str] = None) -> List[Dict[str, Any]]:
    s = get_store()
    checks = {c.resident_id: c for c in preview()}
    latest: Dict[str, Dict[str, Any]] = {}
    for a in s.alerts():  # newest first
        latest.setdefault(a["resident_id"], a)
    last_note: Dict[str, Dict[str, Any]] = {}
    for n in s.notes():  # newest first
        last_note.setdefault(n["resident_id"], n)
    out = []
    for r in s.residents():
        if q and q.lower() not in f"{r['id']} {r.get('display_name', '')}".lower():
            continue
        c = checks.get(r["id"])
        n = last_note.get(r["id"])
        out.append({**r, "tier": c.tier if c else "baseline_limited",
                    "title": c.title if c and c.alert else None,
                    "urgent": bool(c and c.urgent), "reasons": c.reasons if c else [],
                    # plain labels of what changed (persisting or urgent), for the dashboard row
                    "changes": ([LABELS.get(f.key, f.key) for f in c.findings if f.persisting or f.urgent]
                                + (["Unread note"] if c.unread_notes else [])) if c else [],
                    "days": c.duration_days if c and (c.alert or any(f.persisting for f in c.findings)) else None,
                    "alert": latest.get(r["id"]),
                    "last_note_at": str(n["recorded_at"]) if n else None,
                    "last_note": {k: n.get(k) for k in ("note_text", "recorded_at", "author_role", "author_name")} if n else None})
    return sorted(out, key=lambda r: (TIER_ORDER.get(r["tier"], 9), r["id"]))


def timeline(resident_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    return get_store().notes(resident_id)[:limit]


def overview(resident_id: str) -> Optional[Dict[str, Any]]:
    s = get_store()
    resident = s.resident(resident_id)
    if not resident:
        return None
    checks = preview(resident_id)
    alert = s.latest_alert(resident_id)
    check = checks[0] if checks else None
    return {
        "resident": resident,
        "check": to_dict(check) if check else None,
        "alert": alert,
        "similar": similar_cases(alert["id"]) if alert else None,
        "notes": timeline(resident_id, 10),
        "vitals": vitals_table(resident_id, check.vitals_usual if check else {}),
    }


def vitals_table(resident_id: str, usuals: Dict[str, Optional[float]], limit: int = 10) -> Dict[str, Any]:
    """Recent charted vitals, each value marked when it's out of line, plus the resident's usual."""
    rows = []
    for v in get_store().vitals(resident_id)[:limit]:
        row = {k: v.get(k) for k in ("id", "recorded_at", "temp_c", "spo2", "pulse", "resp_rate",
                                     "bp_systolic", "bp_diastolic", "author_role", "author_name")}
        row["flags"] = vt.flags(v, usuals)
        rows.append(row)
    return {"usual": usuals, "readings": rows}


def add_vitals(resident_id: str, values: Dict[str, Any], author_name: Optional[str] = None,
               author_id: Optional[str] = None, recorded_at: Optional[str] = None) -> Dict[str, Any]:
    """Chart a set of vitals, then re-run the check for that resident."""
    row = {"resident_id": resident_id, **{k: values.get(k) for k in vt.FIELDS},
           "recorded_at": recorded_at or datetime.now().replace(microsecond=0).isoformat(),
           "author_role": "Nurse", "author_name": author_name, "author_id": author_id}
    saved = get_store().add_vital({k: v for k, v in row.items() if v is not None or k in vt.FIELDS})
    result = run(resident_id)
    return {"vitals": saved, "result": result["residents"][0] if result["residents"] else None}


def similar_cases(alert_id: str) -> Dict[str, Any]:
    return {"alert_id": alert_id,
            "note": "Fictional case library. Shows what happened in similar past cases; not a diagnosis.",
            **get_store().similar_cases(alert_id)}


def alerts(status: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = get_store().alerts(status)
    return sorted(rows, key=lambda a: not a["urgent"])  # urgent first, then newest (stable sort)


def get_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    return get_store().alert(alert_id)


def set_alert_status(alert_id: str, status: str) -> Optional[Dict[str, Any]]:
    if status not in ALERT_STATUSES:
        raise ValueError(f"status must be one of {', '.join(ALERT_STATUSES)}")
    return get_store().set_alert_status(alert_id, status)


UNIT_PREFIX = "2W-"


def next_resident_id(prefix: str = UNIT_PREFIX) -> str:
    """The next free unit ID: one more than the highest 2W-NNN in use."""
    nums = [int(r["id"][len(prefix):]) for r in get_store().residents()
            if r["id"].startswith(prefix) and r["id"][len(prefix):].isdigit()]
    return f"{prefix}{(max(nums) + 1 if nums else 1):03d}"


def add_resident(resident: Dict[str, Any]) -> Dict[str, Any]:
    """Create a resident. They show as "not enough history" until notes build a baseline."""
    row = get_store().add_resident({k: (str(v) if v is not None and k.startswith("baseline_") else v)
                                    for k, v in resident.items()})
    invalidate()
    return row


def add_note(resident_id: str, note_text: str, author_role: str = "PSW",
             recorded_at: Optional[str] = None, author_name: Optional[str] = None,
             author_id: Optional[str] = None) -> Dict[str, Any]:
    """Save a care note, then re-run the check for that resident. Returns the note and the new result."""
    s = get_store()
    row = {
        "resident_id": resident_id,
        "note_text": note_text.strip(),
        "author_role": author_role,
        # Local wall-clock time, no offset: matches how test_data/ timestamps are written.
        "recorded_at": recorded_at or datetime.now().replace(microsecond=0).isoformat(),
    }
    if author_name:  # signed-in nurse
        row.update(author_name=author_name, author_id=author_id)
    note = s.add_note(row)
    note["ai_reading"] = _read_new_note(note)
    result = run(resident_id)
    return {"note": note, "result": result["residents"][0] if result["residents"] else None}


# ---------------------------------------------------------------------------
# Gemini note reading
# ---------------------------------------------------------------------------
NEW_NOTE_WAIT_S = 20  # how long saving a note waits for Gemini before carrying on with the rules
_reader_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="note-reader")


def _read_new_note(note: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Have Gemini read a note that was just saved. Saving never fails because of Gemini:
    on an error or a slow answer the rules read the note, and a later catch-up reads it."""
    future = _reader_pool.submit(ai_read.ensure_read, [note], get_store(), max_wait=NEW_NOTE_WAIT_S)
    try:
        future.result(timeout=NEW_NOTE_WAIT_S)
    except FutureTimeout:
        pass
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("Reading the new note failed; the rules read it.")
    return note.get("ai_reading")


def read_all_notes(force: bool = False, progress: Any = None) -> Dict[str, Any]:
    """Catch-up: Gemini reads every note without a current reading, then alerts are refreshed.
    The whole history gets the same reader, so a resident's normal and recent days compare fairly."""
    s = get_store()
    counts = ai_read.ensure_read(s.notes(), s, force=force, progress=progress)
    invalidate()
    if counts.get("read") or counts.get("from_cache"):
        run()
    return counts


def reading_status() -> Dict[str, Any]:
    return ai_read.coverage(get_store().notes())
