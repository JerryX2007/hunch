"""Where Hunch's data lives. Two interchangeable stores with the same methods:

    SupabaseStore  the real database (backend/.env filled in)
    MemoryStore    an in-memory copy of test_data/ for demos and offline work;
                   alerts, notes and review statuses reset when the server restarts

HUNCH_MODE picks one: "supabase", "demo", or "auto" (default: Supabase when
backend/.env has a URL and key, otherwise demo).
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = REPO_DIR / "test_data"

load_dotenv(BACKEND_DIR / ".env")

ALERT_LIST_COLUMNS = "id, resident_id, title, summary, status, urgent, created_at"
_NOTE_NS = uuid.UUID("0b8f6a4e-3c1d-4f6a-9e2b-7d5c4a3b2a10")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def supabase_configured() -> bool:
    url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or ""
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
           or os.getenv("VITE_SUPABASE_ANON_KEY"))
    return bool(url and key) and "YOUR-PROJECT-REF" not in url


@lru_cache(maxsize=1)
def get_store():
    mode = os.getenv("HUNCH_MODE", "auto").strip().lower()
    if mode == "demo" or (mode == "auto" and not supabase_configured()):
        return MemoryStore()
    return SupabaseStore()


# ---------------------------------------------------------------------------
class SupabaseStore:
    mode = "supabase"

    def __init__(self) -> None:
        from . import database  # raises a clear error if backend/.env is incomplete
        self.db = database
        self.sb = database.supabase
        # Gemini readings kept in memory when care_notes has no ai_reading column yet
        # (db/migrations/012_note_ai_reading.sql not run).
        self._readings: Dict[str, Dict[str, Any]] = {}
        self._no_reading_column = False

    def ping(self) -> None:
        self.db.ping()

    # residents and notes
    def residents(self) -> List[Dict[str, Any]]:
        return self.db.get_residents()

    def resident(self, resident_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_resident(resident_id)

    def add_resident(self, resident: Dict[str, Any]) -> Dict[str, Any]:
        return self.db.upsert_resident(resident)

    def notes(self, resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self.db.get_care_notes(resident_id)  # newest first
        if self._readings:
            for n in rows:
                if n.get("id") in self._readings and not n.get("ai_reading"):
                    n["ai_reading"] = self._readings[n["id"]]
        return rows

    def save_note_reading(self, note_id: str, reading: Dict[str, Any]) -> None:
        """Keep Gemini's checked reading with the note, so it's read once."""
        if not self._no_reading_column:
            try:
                self.sb.table("care_notes").update(
                    {"ai_reading": reading, "extraction_status": "ai_read"}).eq("id", note_id).execute()
                return
            except Exception as e:  # noqa: BLE001
                if "ai_reading" not in str(e):
                    raise
                import logging
                logging.getLogger(__name__).warning(
                    "care_notes has no ai_reading column yet; run db/migrations/012_note_ai_reading.sql. "
                    "Readings are kept in memory until then.")
                self._no_reading_column = True
        self._readings[note_id] = reading

    def add_note(self, note: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.db.upsert_care_note(note)
        except Exception as e:  # noqa: BLE001
            # db/migrations/010_note_author.sql not run yet: keep the name in author_role.
            if "author_name" not in str(e) and "author_id" not in str(e):
                raise
            import logging
            logging.getLogger(__name__).warning(
                "care_notes has no author_name column yet; run db/migrations/010_note_author.sql")
            fallback = {k: v for k, v in note.items() if k not in ("author_name", "author_id")}
            if note.get("author_name"):
                fallback["author_role"] = note["author_name"]
            return self.db.upsert_care_note(fallback)

    # staff profiles
    def profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_profile(user_id)

    def save_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        return self.db.upsert_profile(profile)

    # case library
    def cases(self) -> List[Dict[str, Any]]:
        return self.db.get_cases_for_matching()

    # alerts
    def alerts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        q = self.sb.table("alerts").select(ALERT_LIST_COLUMNS)
        if status:
            q = q.eq("status", status)
        return q.order("created_at", desc=True).execute().data

    def alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_alert(alert_id)

    def latest_alert(self, resident_id: str) -> Optional[Dict[str, Any]]:
        rows = (self.sb.table("alerts").select("*").eq("resident_id", resident_id)
                .order("created_at", desc=True).limit(1).execute().data)
        return rows[0] if rows else None

    def save_alert(self, row: Dict[str, Any], observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        alert = self.sb.table("alerts").upsert(row).execute().data[0]
        if observations:
            self.sb.table("observations").upsert(observations).execute()
        self.sb.table("alert_evidence").delete().eq("alert_id", row["id"]).execute()
        if observations:
            self.sb.table("alert_evidence").insert(
                [{"alert_id": row["id"], "observation_id": o["id"]} for o in observations]).execute()
        return alert

    def set_alert_status(self, alert_id: str, status: str) -> Optional[Dict[str, Any]]:
        data = self.sb.table("alerts").update({"status": status}).eq("id", alert_id).execute().data
        return data[0] if data else None

    # similar cases
    def save_matches(self, run: Dict[str, Any], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.db.save_match_run(run, matches)

    def similar_cases(self, alert_id: str) -> Dict[str, Any]:
        return {"outcomes": self.db.get_outcome_spread(alert_id),
                "cases": self.db.get_latest_case_matches(alert_id)}


# ---------------------------------------------------------------------------
class MemoryStore:
    mode = "demo"

    def __init__(self) -> None:
        load = lambda name: json.loads((DATA_DIR / name).read_text(encoding="utf-8"))  # noqa: E731
        self._lock = threading.Lock()
        self._residents = [{k: v for k, v in r.items() if k != "scenario"} for r in load("residents.json")]
        self._notes: List[Dict[str, Any]] = []
        for n in load("notes.json"):
            nid = str(uuid.uuid5(_NOTE_NS, f"{n['resident_id']}|{n['recorded_at']}|{n['note_text']}"))
            self._notes.append({**n, "id": nid, "extraction_status": "pending", "created_at": _now()})
        self._cases = load("cases.json")
        self._case_by_id = {c["id"]: c for c in self._cases}
        self._alerts: Dict[str, Dict[str, Any]] = {}
        self._observations: Dict[str, Dict[str, Any]] = {}
        self._evidence: Dict[str, List[str]] = {}
        self._runs: Dict[str, Dict[str, Any]] = {}  # alert_id -> {"run": ..., "matches": [...]}
        self._profiles: Dict[str, Dict[str, Any]] = {}

    def ping(self) -> None:
        return None

    def residents(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._residents]

    def resident(self, resident_id: str) -> Optional[Dict[str, Any]]:
        return next((dict(r) for r in self._residents if r["id"] == resident_id), None)

    def add_resident(self, resident: Dict[str, Any]) -> Dict[str, Any]:
        row = {**resident, "created_at": _now()}
        with self._lock:
            self._residents.append(row)
        return dict(row)

    def notes(self, resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = [n for n in self._notes if resident_id is None or n["resident_id"] == resident_id]
        return sorted((dict(n) for n in rows), key=lambda n: (n["recorded_at"], n["id"]), reverse=True)

    def add_note(self, note: Dict[str, Any]) -> Dict[str, Any]:
        row = {**note, "id": str(uuid.uuid4()), "extraction_status": "pending", "created_at": _now()}
        with self._lock:
            self._notes.append(row)
        return dict(row)

    def save_note_reading(self, note_id: str, reading: Dict[str, Any]) -> None:
        with self._lock:
            for n in self._notes:
                if n["id"] == note_id:
                    n["ai_reading"] = reading
                    n["extraction_status"] = "ai_read"
                    return

    def profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        p = self._profiles.get(user_id)
        return dict(p) if p else None

    def save_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            row = {**self._profiles.get(profile["id"], {"created_at": _now()}), **profile}
            self._profiles[profile["id"]] = row
        return dict(row)

    def cases(self) -> List[Dict[str, Any]]:
        return self._cases

    def alerts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        keys = [k.strip() for k in ALERT_LIST_COLUMNS.split(",")]
        rows = [{k: a.get(k) for k in keys} for a in self._alerts.values()
                if status is None or a["status"] == status]
        return sorted(rows, key=lambda a: a["created_at"], reverse=True)

    def alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        a = self._alerts.get(alert_id)
        return dict(a) if a else None

    def latest_alert(self, resident_id: str) -> Optional[Dict[str, Any]]:
        rows = [a for a in self._alerts.values() if a["resident_id"] == resident_id]
        return dict(max(rows, key=lambda a: a["created_at"])) if rows else None

    def save_alert(self, row: Dict[str, Any], observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        with self._lock:
            merged = {**self._alerts.get(row["id"], {}), **row}
            self._alerts[row["id"]] = merged
            for o in observations:
                self._observations[o["id"]] = o
            self._evidence[row["id"]] = [o["id"] for o in observations]
        return dict(merged)

    def set_alert_status(self, alert_id: str, status: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if alert_id not in self._alerts:
                return None
            self._alerts[alert_id]["status"] = status
            return dict(self._alerts[alert_id])

    def save_matches(self, run: Dict[str, Any], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        with self._lock:
            cur = self._runs.get(run["alert_id"])
            if cur and cur["run"]["alert_fingerprint"] == run["alert_fingerprint"]:
                return cur["run"]
            saved = {**run, "id": str(uuid.uuid4()), "created_at": _now()}
            self._runs[run["alert_id"]] = {"run": saved, "matches": matches}
            return saved

    def similar_cases(self, alert_id: str) -> Dict[str, Any]:
        cur = self._runs.get(alert_id)
        if not cur:
            return {"outcomes": [], "cases": []}
        cases = []
        for m in cur["matches"]:
            c = self._case_by_id.get(m["historical_case_id"], {})
            cases.append({
                "alert_id": alert_id, **{k: c.get(k) for k in (
                    "case_summary", "documented_outcome", "outcome_category", "disposition",
                    "limitations", "duration_days", "timeline")},
                **m, "scorer_version": cur["run"]["scorer_version"], "matched_at": cur["run"]["created_at"],
            })
        n = Counter(c["outcome_category"] for c in cases)
        return {"outcomes": [{"outcome_category": k, "n": v} for k, v in n.most_common()], "cases": cases}
