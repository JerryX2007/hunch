"""Run the history check from the command line. From backend/:

    python -m scripts.run_history_check            # preview: prints results, writes nothing
    python -m scripts.run_history_check --save     # also saves alerts + similar cases
    python -m scripts.run_history_check --eval     # grade against test_data/eval_scenarios.json
"""

import argparse
import json

from app import database as db
from app.history import service

TIER_MARK = {"urgent": "!!", "alert": "! ", "watch": "~ ", "baseline_limited": "? ", "quiet": "  "}

p = argparse.ArgumentParser()
p.add_argument("--save", action="store_true", help="save alerts, evidence and case matches to Supabase")
p.add_argument("--eval", action="store_true", help="compare with test_data/eval_scenarios.json")
args = p.parse_args()

checks = service.preview()
print(f"As of {checks[0].as_of if checks else '-'}  ({len(checks)} residents)\n")
for c in checks:
    print(f"{TIER_MARK[c.tier]} {c.resident_id:<10} {c.tier.upper():<17} {c.title if c.alert else ''}")
    for r in c.reasons:
        print(f"      - {r}")
    if c.ruled_out:
        print(f"      (ruled out: {', '.join(c.ruled_out)})")

if args.eval:
    expected = {e["resident_id"]: e["expected"] for e in json.load(open(db.REPO_DIR / "test_data" / "eval_scenarios.json"))}
    print("\nEval:")
    passed = 0
    for c in checks:
        e = expected.get(c.resident_id)
        if not e:
            continue
        problems = []
        if c.alert != e["alert_created"]:
            problems.append(f"alert={c.alert}, expected {e['alert_created']}")
        missing = set(e.get("categories", [])) - set(c.categories)
        if missing:
            problems.append(f"missing categories {sorted(missing)}")
        if "urgent" in e and c.urgent != e["urgent"]:
            problems.append("urgent mismatch")
        if "baseline_limited" in e and c.baseline_limited != e["baseline_limited"]:
            problems.append("baseline_limited mismatch")
        passed += not problems
        print(f"  {'PASS' if not problems else 'FAIL'}  {c.resident_id}  {'; '.join(problems)}")
    print(f"  {passed}/{len(expected)} passed")

if args.save:
    print("\nSaving...")
    summary = service.run()
    for r in summary["residents"]:
        if "alert_id" in r:
            sc = r["similar_cases"]
            outs = ", ".join(f"{o['outcome_category']} x{o['n']}" for o in sc["outcomes"])
            print(f"  {r['resident_id']}: alert {r['alert_id'][:8]}, {sc['matches']} similar cases ({outs})")
    print(f"Saved {summary['alerts']} alert(s).")
