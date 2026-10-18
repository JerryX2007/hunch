"""Vitals: published limits, measured against each resident's own usual."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.history import vitals as vt
from app.history.check import check_resident
from app.main import app


# --- one reading -------------------------------------------------------------
@pytest.mark.parametrize("key,value,usual,out,alone,urgent", [
    ("temperature", 37.9, 36.6, True, True, False),    # IDSA single reading
    ("temperature", 37.5, 36.2, True, True, False),    # 1.3 above her usual: a fever for her
    ("temperature", 37.6, 36.5, True, False, False),   # exactly 1.1 above (float-safe): only "repeated > 37.2"
    ("temperature", 37.3, 36.6, True, False, False),   # needs a repeat
    ("temperature", 37.1, 36.6, False, False, False),
    ("temperature", 39.2, 36.6, True, True, True),
    ("oxygen", 90, 91, False, False, False),           # COPD: 90-92 is his usual
    ("oxygen", 86, 91, True, True, True),              # ...but 5 below it is not
    ("oxygen", 93, 96, True, False, False),            # below 94
    ("oxygen", 92, 96, True, False, False),            # 4 below usual
    ("oxygen", 88, 96, True, True, True),
    ("breathing_rate", 25, 18, True, False, False),
    ("breathing_rate", 31, 18, True, False, True),
    ("pulse", 101, 72, True, False, False),
    ("pulse", 96, 72, False, False, False),
    ("blood_pressure", 96, 102, False, False, False),  # low is her usual
    ("blood_pressure", 108, 132, True, False, False),  # 24 below usual
    ("blood_pressure", 86, None, True, False, False),
])
def test_judge(key, value, usual, out, alone, urgent):
    j = vt.judge(key, value, usual)
    assert (j.out_of_line, j.alone, j.urgent) == (out, alone, urgent), j.why


# --- vitals written in notes ------------------------------------------------
def test_vitals_in_note_text():
    assert vt.from_text("SpO2 88% RA, RR 28, P 104, T 37.6, BP 100/60") == [
        {"spo2": 88, "resp_rate": 28, "pulse": 104, "temp_c": 37.6, "bp_systolic": 100, "bp_diastolic": 60}]
    assert vt.from_text("Felt warm, T 37.6. Rechecked 1h later T 36.7.") == [{"temp_c": 37.6}, {"temp_c": 36.7}]
    for text in ["B/F 50%. ate 1/2 lunch", "voided x2, BM x1", "repo'd @0200", "drank 250ml", "No BM x4 days", "O2 2L at night"]:
        assert vt.from_text(text) == [], text


def test_a_note_repeating_a_charted_reading_is_not_counted_twice():
    entered = [{"id": "v1", "recorded_at": "2026-10-17T07:50:00", "spo2": 88, "pulse": 104}]
    notes = [{"id": "n1", "resident_id": "R", "recorded_at": "2026-10-17T07:55:00", "note_text": "SpO2 88% RA, P 104, T 37.6"}]
    merged = vt.merge_note_readings(entered, notes, {"n1": notes[0]["note_text"]})
    from_note = [r for r in merged if r.get("source") == "note"]
    assert len(from_note) == 1 and from_note[0]["temp_c"] == 37.6 and from_note[0]["spo2"] is None


# --- in the history check ---------------------------------------------------
def _resident(rid="R", days=14, start=datetime(2026, 10, 1, 8), usual_t=36.6, recent_t=(36.7, 36.6), o2=96):
    notes = [{"id": f"n{d}", "resident_id": rid, "recorded_at": (start + timedelta(days=d)).isoformat(),
              "note_text": "Ate all of breakfast."} for d in range(days)]
    vitals = [{"id": f"v{d}", "resident_id": rid, "recorded_at": (start + timedelta(days=d, hours=1)).isoformat(),
               "temp_c": usual_t, "spo2": o2, "pulse": 72} for d in range(0, days - 4, 2)]
    vitals += [{"id": f"r{i}", "resident_id": rid, "recorded_at": (start + timedelta(days=days - 2 + i, hours=1)).isoformat(),
                "temp_c": t, "spo2": o2, "pulse": 72} for i, t in enumerate(recent_t)]
    return {"id": rid}, notes, vitals


def test_a_fever_for_her_is_not_a_fever_by_the_book():
    resident, notes, vitals = _resident(usual_t=36.2, recent_t=(37.4, 37.5))
    c = check_resident(resident, notes, vitals=vitals)
    temp = next(f for f in c.findings if f.key == "temperature")
    assert temp.persisting and "usual 36.2 °C" in temp.reason and c.tier == "watch"
    assert c.vitals_usual["temperature"] == 36.2
    assert {e.read_by for e in temp.evidence} == {"vitals"} and all(e.vital_id for e in temp.evidence)


def test_chronically_low_oxygen_is_his_normal():
    resident, notes, vitals = _resident(o2=91)
    c = check_resident(resident, notes, vitals=vitals)
    assert c.tier == "quiet" and not any(f.key == "oxygen" for f in c.findings)


def test_one_warm_reading_is_context_not_a_change():
    resident, notes, vitals = _resident(recent_t=(37.4, 36.7))
    c = check_resident(resident, notes, vitals=vitals)
    temp = next(f for f in c.findings if f.key == "temperature")
    assert not temp.persisting and c.tier == "quiet" and "Not repeated" in temp.reason


def test_new_admission_with_a_fever_is_not_hidden_as_too_new():
    resident, notes, vitals = _resident(days=3, recent_t=(38.2,))
    c = check_resident(resident, notes, vitals=vitals)
    assert c.baseline_limited and c.tier == "watch"
    assert any(f.key == "temperature" and f.persisting for f in c.findings)


def test_falling_oxygen_is_urgent_and_says_so():
    resident, notes, vitals = _resident()
    vitals[-1]["spo2"] = 87
    c = check_resident(resident, notes, vitals=vitals)
    assert c.urgent and c.title == "Urgent: low oxygen"
    assert "oxygen" not in c.match_weights  # the case library has no vitals


# --- API ---------------------------------------------------------------------
@pytest.fixture
def client():
    auth._failures.clear()
    with TestClient(app) as c:
        yield c


def _sign_in(c):
    return c.post("/api/auth/signin", json={"email": auth.DEMO_EMAIL, "password": auth.DEMO_PASSWORD})


def test_charting_vitals(client):
    assert client.post("/api/residents/2W-011/vitals", json={"temp_c": 36.8}).status_code == 401
    _sign_in(client)
    assert client.post("/api/residents/2W-011/vitals", json={}).status_code == 422
    assert client.post("/api/residents/2W-011/vitals", json={"bp_systolic": 120}).status_code == 422
    assert client.post("/api/residents/2W-011/vitals", json={"temp_c": 50}).status_code == 422
    r = client.post("/api/residents/2W-011/vitals", json={"temp_c": 38.4, "spo2": 95, "bp_systolic": 128, "bp_diastolic": 76})
    assert r.status_code == 201 and r.json()["result"]["tier"] in {"watch", "alert", "urgent"}
    table = client.get("/api/residents/2W-011/vitals").json()
    newest = table["readings"][0]
    assert newest["temp_c"] == 38.4 and "temp_c" in newest["flags"] and newest["author_name"]
    assert table["usual"]["temperature"] is not None
    page = client.get("/api/residents/2W-011").json()
    assert page["vitals"]["readings"][0]["temp_c"] == 38.4
    assert page["resident"]["conditions"]  # medical history comes with the resident


def test_adding_a_patient_with_medical_history(client):
    _sign_in(client)
    r = client.post("/api/residents", json={"display_name": "Eleanor Park", "id": "2W-085",
                                            "conditions": ["Type 2 diabetes", " ", "COPD"]})
    assert r.status_code == 201 and r.json()["conditions"] == ["Type 2 diabetes", "COPD"]
