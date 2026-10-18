"""Read-only check that every Supabase table and view is reachable. Run from backend/:

    python -m scripts.check_db
"""

from postgrest.exceptions import APIError

from app import database as db

TABLES = ["profiles", "residents", "care_notes", "observations", "alerts", "alert_evidence",
          "historical_cases", "case_match_runs", "case_matches", "latest_case_matches",
          "latest_outcome_spread", "eval_scenarios"]

client = db.supabase_admin or db.supabase
print(f"Checking {db.SUPABASE_URL} with the {'service-role' if db.supabase_admin else 'anon'} key\n")
ok = True
for t in TABLES:
    try:
        resp = client.table(t).select("*", count="exact").limit(0).execute()
        print(f"  OK    {t:<24} {resp.count if resp.count is not None else '?'} rows")
    except APIError as e:
        ok = False
        print(f"  FAIL  {t:<24} {e.message}")
    except Exception as e:  # noqa: BLE001 - network errors etc.
        ok = False
        print(f"  FAIL  {t:<24} {type(e).__name__}: {e}")
print("\nAll reachable." if ok else "\nSome tables are missing or unreachable: see db/README.md.")
raise SystemExit(0 if ok else 1)
