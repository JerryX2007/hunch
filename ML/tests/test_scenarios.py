"""Golden scenarios: plain-English situations with the answer we expect.

If a change to rules.py or weights.yaml breaks one of these, pytest tells you
before the demo does. Run with:  pytest -v
"""

from data.fake_unit import at, history, hunch, reading
from engine import Resident, Sign, score_resident
from engine.baseline import baseline
from engine.shifts import shift_id

NOW = at(14, 20)  # 14 Oct 2026, 8 pm (evening shift)


def resident(rid="R1", **kw) -> Resident:
    defaults = dict(id=rid, name="Test Resident", room="201", table="B", flu_shot_this_season=True)
    return Resident(**{**defaults, **kw})


def normal_chart(rid="R1", temp=36.6, fluids=1200, spo2=97):
    """Two weeks of ordinary readings, plus normal readings today."""
    return (
        history(rid, "temp_c", temp, NOW, jitter=0.1)
        + history(rid, "fluids_24h", fluids, NOW, jitter=60)
        + history(rid, "spo2", spo2, NOW, jitter=1)
        + [reading(rid, "temp_c", temp, at(14, 18)),
           reading(rid, "fluids_24h", fluids, at(14, 19)),
           reading(rid, "spo2", spo2, at(14, 18))]
    )


# ---------- The scenarios from the plan ----------

def test_single_tap_stays_quiet():
    r = resident()
    a = score_resident(r, [hunch("R1", "P1", Sign.SLEEPIER, at(14, 10))], normal_chart(), NOW)
    assert a.score == 1
    assert a.tier == "Quiet"


def test_brief_example_calls_np():
    """3 staff, 2 shifts, sleepier + eating less, 37.5 vs usual 36.2, fluids -36%."""
    r = resident(flu_shot_this_season=False)
    hunches = [
        hunch("R1", "P1", Sign.SLEEPIER, at(14, 10)),      # day shift
        hunch("R1", "P2", Sign.EATING_LESS, at(14, 13)),   # day shift
        hunch("R1", "P3", Sign.SLEEPIER, at(14, 17)),      # evening shift
    ]
    chart = (
        history("R1", "temp_c", 36.2, NOW, jitter=0.1)
        + history("R1", "fluids_24h", 1280, NOW, jitter=60)
        + [reading("R1", "temp_c", 37.5, at(14, 18)),
           reading("R1", "fluids_24h", 820, at(14, 19))]
    )
    a = score_resident(r, hunches, chart, NOW)

    assert {x.code: x.points for x in a.results} == {
        "HUNCH": 1, "MULTI_STAFF": 2, "MULTI_SHIFT": 1, "MULTI_SIGN": 1,
        "FEVER": 2, "FEVER_DELIRIUM": 1, "FLUIDS_LOW": 2,
    }
    assert a.score == 10
    assert a.tier == "Call NP"
    # 37.5 is not a fever by any absolute threshold: it counts only vs HER baseline.
    assert any("1.3 °C above usual 36.2" in reason for reason in a.reasons)
    assert any("-36%" in reason for reason in a.reasons)
    assert "Context: no flu shot recorded this season" in a.notes


def test_copd_cough_is_her_normal():
    r = resident(chronic_signs=frozenset({Sign.COUGHING}))
    a = score_resident(r, [hunch("R1", "P1", Sign.COUGHING, at(14, 10))], normal_chart(), NOW)
    assert a.score == 0
    assert a.tier == "Quiet"
    assert any("coughing is usual" in n for n in a.notes)


def test_dehydration_decoy_reaches_assess_without_fever():
    r = resident()
    hunches = [
        hunch("R1", "P1", Sign.CONFUSED, at(14, 10)),
        hunch("R1", "P4", Sign.NOT_DRINKING, at(14, 16)),
    ]
    chart = (history("R1", "temp_c", 36.5, NOW, jitter=0.1)
             + history("R1", "fluids_24h", 1200, NOW, jitter=60)
             + [reading("R1", "temp_c", 36.6, at(14, 18)),
                reading("R1", "fluids_24h", 700, at(14, 19))])
    a = score_resident(r, hunches, chart, NOW)
    codes = {x.code for x in a.results}
    assert "FEVER" not in codes
    assert "FLUIDS_LOW" in codes
    assert a.tier == "Assess"


def test_two_psws_two_shifts_is_watch():
    a = score_resident(resident(), [
        hunch("R1", "P1", Sign.SLEEPIER, at(14, 10)),
        hunch("R1", "P2", Sign.SLEEPIER, at(14, 17)),
    ], normal_chart(), NOW)
    assert a.score == 3
    assert a.tier == "Watch"


# ---------- Safety behaviours ----------

def test_repeated_reports_from_one_psw_count_once():
    spam = [hunch("R1", "P1", Sign.SLEEPIER, at(14, 10, m)) for m in range(5)]
    a = score_resident(resident(), spam, normal_chart(), NOW)
    assert a.score == 1


def test_very_low_oxygen_is_red_flag():
    chart = history("R1", "spo2", 96, NOW, jitter=1) + [reading("R1", "spo2", 88, at(14, 19))]
    a = score_resident(resident(), [], chart, NOW)
    assert a.tier == "Call NP"  # only 2 points, but a red flag overrides the score


def test_old_hunches_expire():
    a = score_resident(resident(), [hunch("R1", "P1", Sign.SLEEPIER, at(10, 10))], normal_chart(), NOW)
    assert a.score == 0  # 4 days ago is outside the 72 h window


# ---------- Building blocks ----------

def test_baseline_ignores_last_48_hours():
    chart = history("R1", "temp_c", 36.2, NOW, jitter=0.1) + [
        reading("R1", "temp_c", 38.5, at(13, 8)),   # yesterday's spike
        reading("R1", "temp_c", 38.9, at(13, 20)),
    ]
    assert baseline(chart, "temp_c", NOW) == 36.2


def test_night_shift_crosses_midnight():
    assert shift_id(at(15, 2)) == "2026-10-14-night"
    assert shift_id(at(14, 23, 30)) == "2026-10-14-night"
    assert shift_id(at(14, 7)) == "2026-10-14-day"
