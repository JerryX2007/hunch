"""Have Gemini read the care notes that don't have a reading yet, then refresh alerts.

Run from backend/ (needs GEMINI_API_KEY in backend/.env):

    python -m scripts.read_notes          # notes without a reading
    python -m scripts.read_notes --all    # read every note again (e.g. after a prompt change)

Works on whichever data run.py would use (Supabase, or demo data with HUNCH_MODE=demo).
On Supabase, run db/migrations/012_note_ai_reading.sql first so readings are saved with
the notes; then the website (including Vercel) uses them. Safe to run again: notes that
already have a reading are skipped, and a local cache (backend/.cache/) means the same
note text is never sent twice.
"""

import argparse
import logging
import sys

from app.history import service
from app.models.note_reader import ai_enabled, models


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="read every note again")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="  %(message)s")  # shows rate-limit waits
    if not ai_enabled():
        print("GEMINI_API_KEY is not set in backend/.env (or HUNCH_AI_READ=0). Nothing to do.")
        return 1
    status = service.reading_status()
    print(f"Model: {models()[0]}. {status['read_by_ai']} of {status['notes']} notes already read.")

    def progress(c):
        print(f"  read {c['read']}, from cache {c['from_cache']}, failed {c['failed']}", flush=True)

    counts = service.read_all_notes(force=args.all, progress=progress)
    status = service.reading_status()
    print(f"Done: {counts['read']} read by Gemini, {counts['from_cache']} from the cache, "
          f"{counts['failed']} failed. {status['read_by_ai']} of {status['notes']} notes now read.")
    if counts["failed"]:
        print("Run it again to retry the ones that failed (often a rate limit).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
