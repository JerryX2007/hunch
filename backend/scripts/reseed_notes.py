"""Replace the seed care notes in Supabase with the ones in test_data/notes.json.

Run from backend/ after regenerating the notes (test_data/generate_seed.py):

    python -m scripts.reseed_notes          # shows what will change, asks before deleting
    python -m scripts.reseed_notes --yes    # no question

For the 12 seed residents only, it:
1. deletes their notes from the seed period (up to the last seed day). That also removes
   what was found in those notes. Notes written after the seed period, by people using
   the app, are kept. Residents added in the app are not touched.
2. deletes their alerts (they're rebuilt in step 5) and the similar-case results saved with them,
3. adds the new notes,
4. links each note to its nurse's account (when the four demo nurses have accounts),
5. runs the history check again, so alerts match the new notes. With GEMINI_API_KEY set,
   Gemini reads the new notes first (otherwise run `python -m scripts.read_notes` later).
"""

import argparse
import json
import sys
from datetime import date, timedelta

from app import database as db
from app.store import DATA_DIR

BATCH = 500


def load(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed_cutoff(notes):
    """Midnight after the last seed day: seed notes are before it, notes written in the app after."""
    last = max(n["recorded_at"][:10] for n in notes)
    return (date.fromisoformat(last) + timedelta(days=1)).isoformat() + "T00:00:00"


def main(argv=None, sb=None, ask=input) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yes", action="store_true", help="don't ask before deleting")
    args = ap.parse_args(argv)
    sb = sb or db._require_admin()

    residents = [{k: v for k, v in r.items() if k != "scenario"} for r in load("residents.json")]
    notes = load("notes.json")
    nurses = [n["name"] for n in load("people.json")["nurses"]]
    ids = [r["id"] for r in residents]
    cutoff = seed_cutoff(notes)

    old = db._fetch_all(lambda: sb.table("care_notes").select("id, recorded_at")
                        .in_("resident_id", ids).order("id"))
    replace = [n for n in old if str(n["recorded_at"])[:19] < cutoff]
    print(f"Database: {db.SUPABASE_URL}")
    print(f"Seed residents: {len(ids)} ({ids[0]} to {ids[-1]}). Seed period ends {cutoff[:10]}.")
    print(f"  will delete {len(replace)} old seed notes and these residents' alerts")
    print(f"  will keep   {len(old) - len(replace)} notes written after the seed period")
    print(f"  will add    {len(notes)} new notes from test_data/notes.json")
    if not args.yes and ask("Go ahead? Type yes: ").strip().lower() != "yes":
        print("Nothing changed.")
        return 1

    sb.table("residents").upsert(residents).execute()
    sb.table("alerts").delete().in_("resident_id", ids).execute()
    sb.table("care_notes").delete().in_("resident_id", ids).lt("recorded_at", cutoff).execute()
    print(f"  deleted {len(replace)} notes and the alerts")

    rows = notes
    for i in range(0, len(rows), BATCH):
        try:
            sb.table("care_notes").insert(rows[i:i + BATCH]).execute()
        except Exception as e:  # noqa: BLE001
            if "author_name" not in str(e):
                raise
            # db/migrations/010_note_author.sql not run: keep the nurse's name in author_role
            rows = [{**{k: v for k, v in n.items() if k != "author_name"}, "author_role": n.get("author_name") or n["author_role"]}
                    for n in notes]
            sb.table("care_notes").insert(rows[i:i + BATCH]).execute()
    print(f"  added {len(notes)} notes")

    linked = 0
    try:
        profiles = sb.table("profiles").select("id, full_name").in_("full_name", nurses).execute().data or []
        for p in profiles:
            got = (sb.table("care_notes").update({"author_id": p["id"]}).eq("author_name", p["full_name"])
                   .in_("resident_id", ids).is_("author_id", "null").execute().data or [])
            linked += len(got)
        print(f"  linked {linked} notes to {len(profiles)} nurse accounts"
              + ("" if profiles else " (no accounts yet: python -m scripts.create_demo_nurses)"))
    except Exception as e:  # noqa: BLE001 - linking is a nice-to-have
        print(f"  notes not linked to nurse accounts ({type(e).__name__}); "
              "python -m scripts.create_demo_nurses links them later")

    from app.history import service
    from app.models.note_reader import ai_enabled
    service.invalidate()
    if ai_enabled():
        print("  Gemini is reading the new notes...")
        counts = service.read_all_notes()
        print(f"  Gemini read {counts['read']} notes ({counts['failed']} failed: run scripts.read_notes again for those)")
    summary = service.run()
    print(f"  history check: {summary['alerts']} alerts")
    for r in summary["residents"]:
        if r.get("alert_id"):
            print(f"    {r['resident_id']}: {r['title']}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
