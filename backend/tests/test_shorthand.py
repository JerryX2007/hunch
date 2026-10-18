"""The rules read notes the way staff actually write them: shorthand, fractions, no capitals."""

import pytest

from app.history.extract import extract


def read(text):
    f = extract({"note_text": text, "recorded_at": "2026-10-10T08:00:00"})
    return ({s.key for s in f.signals}, {s.key for s in f.signals if s.urgent},
            [m.pct for m in f.meals], {s.key for s in f.negated}, f)


@pytest.mark.parametrize("text,pct", [
    ("B/F 50%. quiet this am", 50), ("ate ~1/2 bkfst", 50), ("lunch ~3/4", 75), ("ate ~2/3 brkfst", 67),
    ("supper 1/4 only", 25), ("refused bkfst", 0), ("poor intake @ supper", 15), ("good appetite @ lunch", 90),
    ("ate fair amt of B/F", 65), ("Resident ate ~3/4 lunch", 75),
])
def test_meal_amounts(text, pct):
    assert read(text)[2] == [pct]


@pytest.mark.parametrize("text", ["good fluid intake", "poor fluid intake today", "drank approx 1/3 of am fluids",
                                  "No BM since 10/12", "fluids ~250ml"])
def test_drinks_and_dates_are_not_meals(text):
    assert read(text)[2] == []


@pytest.mark.parametrize("text,keys", [
    ("Needed hands on assist amb to DR (usually SBA only)", {"mobility"}),
    ("1 person assist w/ amb today", {"mobility"}),
    ("v. sleepy during am care", {"energy"}),
    ("napping in w/c most of pm", {"energy"}),
    ("drank approx 1/3 of am fluids", {"fluids"}),
    ("voided x1 only this shift, urine dark", {"toileting.urine"}),
    ("c/o L knee pain", {"pain"}),
    ("abd firm, holding her stomach", {"pain"}),
    ("refused bingo this pm", {"social"}),
])
def test_changes(text, keys):
    assert read(text)[0] == keys


def test_days_without_a_bowel_movement():
    for text, days in [("No BM x4 days.", 4), ("No BM x5d. few bites of bkfst", 5), ("no BM for 3 days", 3)]:
        f = read(text)[4]
        assert [s.stated_days for s in f.signals if s.key == "toileting.bowel"] == [days]


@pytest.mark.parametrize("text,key", [
    ("Unwitnessed fall - res found on floor beside bed @0300", "mobility"),
    ("Unable to WB on R leg", "mobility"),
    ("Transferred to ED via EMS for assessment of R hip", "event"),
    ("SOB on exertion, O2 sat 89%", "breathing"),
])
def test_urgent_shorthand(text, key):
    assert key in read(text)[1]


@pytest.mark.parametrize("text,ruled_out", [
    ("Denies SOB. Ate well.", {"breathing"}),
    ("nil c/o pain", {"pain"}),
    ("Denies pain/fatigue. Not confused, A&Ox3.", {"pain", "energy", "confusion"}),
    ("No difficulty walking, didn't need extra help to DR.", {"mobility"}),
])
def test_denials(text, ruled_out):
    signals, _, _, negated, _ = read(text)
    assert negated == ruled_out and not signals


def test_fell_asleep_is_not_a_fall():
    assert read("fell asleep in w/c after lunch")[0] == set()


def test_stray_spaces_do_not_hide_anything():
    assert read("good  appetite @ Lunch")[2] == [90]
