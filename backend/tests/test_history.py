"""History check against test_data/eval_scenarios.json. No database needed.

Run from backend/:  python -m pytest -q
"""

import json
from pathlib import Path

import pytest

from app.history.check import check_unit
from app.history.extract import extract
from app.history.match import match_cases

DATA = Path(__file__).resolve().parents[2] / "test_data"
load = lambda name: json.loads((DATA / name).read_text())  # noqa: E731

RESIDENTS, NOTES, CASES = load("residents.json"), load("notes.json"), load("cases.json")
VITALS = load("vitals.json")
EVAL = load("eval_scenarios.json")
CHECKS = {c.resident_id: c for c in check_unit(RESIDENTS, NOTES, vitals=VITALS)}


@pytest.mark.parametrize("scenario", EVAL, ids=lambda e: f"{e['resident_id']}-{e['scenario']}")
def test_eval_scenario(scenario):
    c, e = CHECKS[scenario["resident_id"]], scenario["expected"]
    assert c.alert == e["alert_created"], c.reasons
    assert set(e.get("categories", [])) <= set(c.categories)
    if "urgent" in e:
        assert c.urgent == e["urgent"]
    if "baseline_limited" in e:
        assert c.baseline_limited == e["baseline_limited"]
    if "min_similar_cases" in e:
        assert len(match_cases(c.match_weights, c.duration_days, CASES)) >= e["min_similar_cases"]
    for bad in e.get("must_not_extract", []):
        for n in NOTES:
            if n["resident_id"] != c.resident_id:
                continue
            for s in extract(n).signals:
                assert not (s.category == bad["category"]
                            and s.subcategory == bad.get("subcategory")
                            and (bad.get("direction") in (None, s.direction))
                            and (bad.get("change") in (None, s.change))), (n["note_text"], s)


@pytest.mark.parametrize("text,expected", [
    ("Denies pain.", set()),
    ("Not tired today, joined exercise class.", set()),
    ("No diarrhea, no complaints of pain.", set()),
    ("No BM for 4 days.", {"toileting.bowel.decreased"}),
    ("Sleepy but walked to dining room with standby assist as usual.", {"energy"}),
    ("Voided only once this shift, urine dark.", {"toileting.urine.decreased"}),
    ("Found on floor beside bed at 0300.", {"mobility"}),
])
def test_extract_phrases(text, expected):
    got = {s.match_key for s in extract({"note_text": text, "recorded_at": "2026-10-15T08:00:00"}).signals}
    assert got == expected


def test_low_eater_is_judged_against_own_baseline():
    assert not CHECKS["2W-020"].alert


def test_alert_explains_itself():
    c = CHECKS["2W-014"]
    assert c.reasons and all(f.evidence for f in c.findings)
    assert any("usual" in r for r in c.reasons)
