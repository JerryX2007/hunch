"""API tests for creating residents (demo store) and the staff profile routes (fake Supabase)."""

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app

client = TestClient(app)


def test_create_resident_then_log_a_note():
    r = client.post("/api/residents", json={"id": "DEMO-099", "display_name": "New Admission"})
    assert r.status_code == 201, r.text
    assert client.post("/api/residents", json={"id": "DEMO-099", "display_name": "Again"}).status_code == 409
    listed = {x["id"]: x for x in client.get("/api/residents").json()}
    assert listed["DEMO-099"]["tier"] == "baseline_limited"  # no history yet
    note = client.post("/api/residents/DEMO-099/notes", json={"note_text": "Ate all of lunch."})
    assert note.status_code == 201 and note.json()["result"]["tier"] == "baseline_limited"


def test_create_resident_rejects_bad_id():
    assert client.post("/api/residents", json={"id": "bad id!", "display_name": "x"}).status_code == 422


def test_profile_requires_sign_in():
    assert client.get("/api/profile/me").status_code == 401


@pytest.fixture
def signed_in():
    app.dependency_overrides[get_current_user] = lambda: "user-1"
    yield
    app.dependency_overrides.clear()


def test_profile_404_then_create(signed_in, fake_supabase):
    fake_supabase.rows = []
    assert client.get("/api/profile/me").status_code == 404
    fake_supabase.rows = [{"id": "user-1", "full_name": "Pat Lee", "role": "PSW"}]
    r = client.put("/api/profile/me", json={"full_name": "Pat Lee", "role": "PSW"})
    assert r.status_code == 200 and r.json()["full_name"] == "Pat Lee"
    assert client.get("/api/profile/me").json()["id"] == "user-1"
    assert "profiles" in fake_supabase.tables


def test_profile_rejects_unknown_role(signed_in):
    assert client.put("/api/profile/me", json={"full_name": "X", "role": "boss"}).status_code == 422
