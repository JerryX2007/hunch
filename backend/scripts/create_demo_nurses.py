"""Create the unit's four fictional nurses (test_data/people.json) as real accounts on
live Supabase data, and link each existing note to the nurse who wrote it. Run from backend/:

    python -m scripts.create_demo_nurses

Run db/migrations/011_named_residents_and_nurses.sql first (it puts the nurses' names on
the notes). Asks for one password for all four (8+ characters). Safe to run again: it
updates the accounts and only fills in links that are missing.
"""

import json

from app import database as db
from app.store import DATA_DIR

from .create_nurse import ask_password, upsert_nurse


def main() -> None:
    nurses = json.loads((DATA_DIR / "people.json").read_text(encoding="utf-8"))["nurses"]
    print(f"Creating {len(nurses)} nurse accounts on {db.SUPABASE_URL}")
    password = ask_password("Password for all four nurses (8+ characters): ")

    linked = 0
    for n in nurses:
        user_id = upsert_nurse(n["email"], n["name"], password)
        try:
            rows = (db._require_admin().table("care_notes").update({"author_id": user_id})
                    .eq("author_name", n["name"]).is_("author_id", "null").execute().data)
        except Exception as e:  # noqa: BLE001
            if "author_id" in str(e) or "author_name" in str(e):
                raise SystemExit("Notes have no author columns yet: run "
                                 "db/migrations/011_named_residents_and_nurses.sql first, then run this again.")
            raise
        linked += len(rows)
        print(f"    linked {len(rows)} notes")

    print(f"\nDone. {linked} notes linked. Sign in at /nurse with any of:")
    for n in nurses:
        print(f"  {n['email']}")
    print("and the password you just chose.")


if __name__ == "__main__":
    main()
