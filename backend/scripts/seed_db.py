"""Load test_data/ into Supabase. Run from backend/:

    python -m scripts.seed_db              # residents, care notes, cases, eval scenarios
    python -m scripts.seed_db --results    # ...then run the history check and save its alerts

Safe to re-run: residents, cases and eval scenarios are upserted by id, and only
care notes that aren't already there are added (existing notes keep their ids,
so saved alerts keep their evidence).
"""

import argparse
import json
import os

import httpx
from postgrest.exceptions import APIError

from app import database as db

DATA = db.REPO_DIR / "test_data"


def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def step(label, fn):
    try:
        result = fn()
        if str(result).startswith("SKIPPED"):
            print(f"  SKIP  {label:<18} {result[10:]}")
            return True
        print(f"  OK    {label:<18} {result}")
        return True
    except APIError as e:
        print(f"  FAIL  {label:<18} {e.message}")
        if e.hint:
            print(f"        hint: {e.hint}")
        return False


# Test labels, not resident data: the scorer must never see the expected outcome.
LABEL_FIELDS = {"scenario"}


def table_columns():
    """{table: {column, ...}} from the REST API's OpenAPI spec (needs the secret key)."""
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
    headers = {"apikey": key}
    if key.startswith("eyJ"):  # legacy JWT keys also go in Authorization
        headers["Authorization"] = f"Bearer {key}"
    try:
        spec = httpx.get(f"{db.SUPABASE_URL}/rest/v1/", headers=headers, timeout=15).json()
        return {t: set(d.get("properties", {})) for t, d in spec["definitions"].items()}
    except Exception:  # noqa: BLE001 - fall back to sending every field
        return {}


COLUMNS = table_columns()
print(f"Seeding {db.SUPABASE_URL}  (columns read: {'yes' if COLUMNS else 'no'})\n")


def fit(table, rows, drop=()):
    """Drop fields the table doesn't have, and say which ones were dropped."""
    cols = COLUMNS.get(table)
    keep = (lambda k: k in cols and k not in drop) if cols else (lambda k: k not in drop)
    skipped = sorted({k for r in rows for k in r if not keep(k)})
    if skipped:
        print(f"        {table}: skipping fields: {', '.join(skipped)}")
    return [{k: v for k, v in r.items() if keep(k)} for r in rows]


residents = fit("residents", load("residents.json"), drop=LABEL_FIELDS)
notes = fit("care_notes", load("notes.json"))
ids = [r["id"] for r in residents]


def seed_residents():
    db.supabase.table("residents").upsert(residents).execute()
    return f"{len(residents)} residents"


def seed_notes():
    existing = db._fetch_all(lambda: db.supabase.table("care_notes")
                             .select("id, resident_id, recorded_at, note_text").in_("resident_id", ids).order("id"))
    have = {(n["resident_id"], str(n["recorded_at"])[:19], n["note_text"]) for n in existing}
    new = [n for n in notes if (n["resident_id"], n["recorded_at"][:19], n["note_text"]) not in have]
    for i in range(0, len(new), 500):  # keep request bodies small
        db.supabase.table("care_notes").insert(new[i:i + 500]).execute()
    return f"{len(notes)} care notes ({len(new)} added, {len(notes) - len(new)} already there)"


def seed_cases():
    return f"{db.seed_historical_cases_from_file()} historical cases"


def seed_eval():
    if COLUMNS and "eval_scenarios" not in COLUMNS:
        return "SKIPPED - table missing: run db/migrations/005_eval_scenarios.sql (and 006) in the Supabase SQL Editor"
    rows = [{"resident_id": e["resident_id"], "scenario": e["scenario"], "expected": e["expected"]}
            for e in load("eval_scenarios.json")]
    db._require_admin().table("eval_scenarios").upsert(rows).execute()
    return f"{len(rows)} eval scenarios"


parser = argparse.ArgumentParser()
parser.add_argument("--results", action="store_true", help="also run the history check and save alerts")
args = parser.parse_args()

ok = step("residents", seed_residents)
ok = (step("care_notes", seed_notes) if ok else False) and ok  # notes need residents first
ok = step("historical_cases", seed_cases) and ok
ok = (step("eval_scenarios", seed_eval) if ok else False) and ok  # needs residents

if ok and args.results:
    from app.history import service
    summary = service.run()
    print(f"  OK    {'alerts':<18} {summary['alerts']} alerts saved with evidence and similar cases")
    for r in summary["residents"]:
        if "alert_id" in r:
            print(f"        {r['resident_id']}: {r['title']}")
print("\nDone." if ok else "\nSome steps failed: the table's columns don't match test_data (see messages above).")
raise SystemExit(0 if ok else 1)
