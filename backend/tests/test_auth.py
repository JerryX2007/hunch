"""Nurse sign-in: who can see what. Demo accounts, plus the Supabase path with a fake client."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from app.store import get_store

DEMO = {"email": auth.DEMO_EMAIL, "password": auth.DEMO_PASSWORD}


@pytest.fixture
def client():
    auth._failures.clear()
    with TestClient(app) as c:
        yield c
    auth._failures.clear()


def sign_in(c, **kw):
    return c.post("/api/auth/signin", json={**DEMO, **kw})


# --------------------------------------------------------------------------- not signed in
def test_without_sign_in_only_names_are_visible(client):
    rows = client.get("/api/residents").json()
    assert rows and set(rows[0]) == {"id", "display_name"}  # no tiers, reasons or notes
    for path in ["/api/residents/2W-014", "/api/residents/2W-014/notes", "/api/alerts", "/api/history/check"]:
        assert client.get(path).status_code == 401, path
    assert client.post("/api/history/run").status_code == 401
    assert client.patch("/api/alerts/x/status", json={"status": "reviewed"}).status_code == 401
    assert client.post("/api/residents", json={"id": "2W-098", "display_name": "x"}).status_code == 401


def test_psw_can_log_a_note_without_sign_in(client):
    r = client.post("/api/residents/2W-012/notes", json={"note_text": "Ate all of lunch.", "author_role": "PSW"})
    assert r.status_code == 201
    assert set(r.json()["result"]) == {"resident_id", "tier", "title"}  # no clinical reasons


def test_me_never_401(client):
    me = client.get("/api/auth/me").json()
    assert me["signed_in"] is False and me["is_nurse"] is False
    # demo mode lists the unit's nurses (test_data/people.json) and the shared demo password
    assert me["demo_login"]["password"] == auth.DEMO_PASSWORD
    names = [n["name"] for n in me["demo_login"]["nurses"]]
    assert len(names) == 7 and names[:2] == ["Priya Raman", "Daniel Osei"]


# --------------------------------------------------------------------------- signing in
def test_wrong_password_then_right(client):
    r = sign_in(client, password="nope")
    assert r.status_code == 401 and "don’t match" in r.json()["detail"]
    r = sign_in(client)
    assert r.status_code == 200 and r.json()["is_nurse"] is True
    assert r.json()["profile"]["role"] == "nurse"
    assert "hunch_access" in r.cookies or client.cookies.get("hunch_access")


def test_signed_in_nurse_sees_everything_and_can_act(client):
    sign_in(client)
    rows = {r["id"]: r for r in client.get("/api/residents").json()}
    assert rows["2W-014"]["tier"] in {"alert", "urgent", "watch", "quiet", "baseline_limited"}
    assert client.get("/api/residents/2W-014").status_code == 200
    assert client.post("/api/history/run").status_code == 200
    alert = client.get("/api/residents/2W-014").json()["alert"]
    assert client.patch(f"/api/alerts/{alert['id']}/status", json={"status": "reviewed"}).json()["status"] == "reviewed"
    created = client.post("/api/residents", json={"id": "2W-097", "display_name": "New Admission"})
    assert created.status_code == 201


def test_nurse_note_carries_her_name(client):
    sign_in(client)
    client.post("/api/residents/2W-013/notes", json={"note_text": "Temp 37.2, resting.", "author_role": "PSW"})
    note = next(n for n in client.get("/api/residents/2W-013/notes?limit=50").json() if n["note_text"] == "Temp 37.2, resting.")
    assert note["author_name"] == "Priya Raman" and note["author_role"] == "Nurse"
    assert note["author_id"] == auth.DEMO_USER_ID
    row = {r["id"]: r for r in client.get("/api/residents").json()}["2W-013"]
    assert row["last_note"]["author_name"] == "Priya Raman"


def test_name_shows_on_evidence(client):
    sign_in(client)
    client.post("/api/residents/2W-012/notes", json={"note_text": "Found on floor beside bed."})
    check = client.get("/api/residents/2W-012").json()["check"]
    urgent = [f for f in check["findings"] if f["urgent"]]
    assert urgent and urgent[0]["evidence"][0]["author_name"] == "Priya Raman"


def test_psw_note_has_no_name(client):
    text = "Ate all of lunch, PSW check."
    client.post("/api/residents/2W-013/notes", json={"note_text": text, "author_role": "PSW"})
    sign_in(client)
    note = next(n for n in client.get("/api/residents/2W-013/notes?limit=50").json() if n["note_text"] == text)
    assert note["author_role"] == "PSW" and not note.get("author_name")


def test_name_kept_before_migration_010(monkeypatch):
    """Live database without the author_name column: the name goes into author_role instead."""
    from app.store import SupabaseStore
    saved = []

    def upsert(note):
        if "author_name" in note:
            raise RuntimeError("Could not find the 'author_name' column of 'care_notes' in the schema cache")
        saved.append(note)
        return note

    store = SupabaseStore.__new__(SupabaseStore)
    store.db = type("DB", (), {"upsert_care_note": staticmethod(upsert)})()
    out = store.add_note({"resident_id": "DEMO-1", "note_text": "x", "author_role": "Nurse",
                          "author_name": "Dana Lee", "author_id": "u1"})
    assert out["author_role"] == "Dana Lee" and "author_name" not in saved[0]


def test_logout_ends_the_session(client):
    sign_in(client)
    assert client.get("/api/alerts").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/alerts").status_code == 401
    assert client.get("/api/auth/me").json()["signed_in"] is False


def test_tampered_cookie_is_rejected(client):
    sign_in(client)
    token = client.cookies.get("hunch_access")
    client.cookies.clear()
    client.cookies.set("hunch_access", token[:-2] + ("00" if not token.endswith("00") else "11"))
    assert client.get("/api/alerts").status_code == 401


def test_too_many_wrong_passwords_are_slowed_down(client):
    for _ in range(auth.MAX_FAILURES):
        assert sign_in(client, password="wrong").status_code == 401
    assert sign_in(client).status_code == 429  # even the right password waits


# --------------------------------------------------------------------------- profiles
def test_new_account_must_add_a_name_first(client, supabase_mode):
    get_store()._profiles.pop("user-dana", None)  # account exists, profile doesn't yet
    client.post("/api/auth/signin", json={"email": "dana@example.com", "password": "correct horse"})
    r = client.get("/api/alerts")
    assert r.status_code == 403 and "name" in r.json()["detail"]
    assert client.get("/api/auth/me").json()["is_nurse"] is False
    saved = client.put("/api/profile/me", json={"full_name": "Dana Lee"}).json()
    assert saved["role"] == "nurse"
    assert client.get("/api/alerts").status_code == 200
    assert client.put("/api/profile/me", json={"full_name": ""}).status_code == 422


def test_profile_requires_sign_in(client):
    assert client.get("/api/profile/me").status_code == 401


def test_startup_key_runs_the_check_without_a_login(client, monkeypatch):
    monkeypatch.setenv("HUNCH_INTERNAL_TOKEN", "launch-secret")
    assert client.post("/api/history/run", headers={"X-Hunch-Internal": "launch-secret"}).status_code == 200
    assert client.post("/api/history/run", headers={"X-Hunch-Internal": "guess"}).status_code == 401


# --------------------------------------------------------------------------- Supabase accounts (fake client)
class FakeAuth:
    def __init__(self):
        self.users = {"dana@example.com": ("correct horse", "user-dana")}

    def sign_in_with_password(self, creds):
        pw, uid = self.users.get(creds["email"], (None, None))
        if pw != creds["password"]:
            raise RuntimeError("Invalid login credentials")
        return self._session(uid, creds["email"])

    def _session(self, uid, email):
        user = SimpleNamespace(id=uid, email=email)
        return SimpleNamespace(user=user, session=SimpleNamespace(
            access_token=f"access-{uid}", refresh_token=f"refresh-{uid}", expires_in=3600))

    def get_user(self, token):
        if token == "access-user-dana":
            return SimpleNamespace(user=SimpleNamespace(id="user-dana", email="dana@example.com"))
        raise RuntimeError("expired")

    def refresh_session(self, token):
        if token == "refresh-user-dana":
            return self._session("user-dana", "dana@example.com")
        raise RuntimeError("bad refresh token")


@pytest.fixture
def supabase_mode(monkeypatch):
    fake = SimpleNamespace(auth=FakeAuth())
    monkeypatch.setattr(auth, "mode", lambda: "supabase")
    monkeypatch.setattr(auth, "_supabase", lambda service=False: fake)
    monkeypatch.setattr(auth, "_token_checker", lambda: fake)
    get_store().save_profile({"id": "user-dana", "full_name": "Dana Lee", "role": "nurse"})
    return fake


def test_supabase_account_signs_in_and_renews(client, supabase_mode):
    assert client.post("/api/auth/signin", json={"email": "dana@example.com", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/signin", json={"email": "Dana@Example.com ", "password": "correct horse"})
    assert r.status_code == 200 and r.json()["profile"]["full_name"] == "Dana Lee"
    assert r.json()["demo_login"] is None
    assert client.get("/api/alerts").status_code == 200
    # access token expired: the refresh cookie renews the session transparently
    refresh_token = client.cookies.get("hunch_refresh")
    client.cookies.clear()
    client.cookies.set("hunch_access", "access-expired")
    client.cookies.set("hunch_refresh", refresh_token)
    r = client.get("/api/alerts")
    assert r.status_code == 200
    assert "access-user-dana" in r.headers.get("set-cookie", "")  # new access cookie issued


def test_each_demo_nurse_signs_in_as_herself(client):
    for nurse in auth.DEMO_NURSES:
        r = client.post("/api/auth/signin", json={"email": nurse["email"].upper(), "password": auth.DEMO_PASSWORD})
        assert r.status_code == 200 and r.json()["profile"]["full_name"] == nurse["name"]
        client.post("/api/auth/logout")
    assert client.post("/api/auth/signin", json={"email": "nobody@hunch.test", "password": auth.DEMO_PASSWORD}).status_code == 401


def test_residents_have_names_and_unit_ids(client):
    sign_in(client)
    rows = {r["id"]: r for r in client.get("/api/residents").json()}
    assert rows["2W-014"]["display_name"] == "Evelyn Brooks"
    assert all(not rid.startswith("DEMO") for rid in rows)
    notes = client.get("/api/residents/2W-014/notes?limit=10").json()
    assert {n["author_name"] for n in notes} <= {n["name"] for n in auth.DEMO_NURSES}


# --------------------------------------------------------------------------- adding patients
def test_add_patient_gets_next_unit_id_and_admission_note(client):
    sign_in(client)
    nxt = client.get("/api/residents/next-id").json()["id"]
    r = client.post("/api/residents", json={"display_name": "  Eleanor Park  ",
                                            "first_note": "Admitted from hospital. Walks with a cane."})
    assert r.status_code == 201, r.text
    new = r.json()
    assert new["id"] == nxt and new["display_name"] == "Eleanor Park"
    assert client.get("/api/residents/next-id").json()["id"] != nxt  # the next one moves on
    rows = {x["id"]: x for x in client.get("/api/residents").json()}
    assert rows[nxt]["tier"] == "baseline_limited"   # no usual pattern yet
    note = client.get(f"/api/residents/{nxt}/notes").json()[0]
    assert note["note_text"].startswith("Admitted") and note["author_name"] == "Priya Raman"


def test_add_patient_with_chosen_id_and_errors(client):
    sign_in(client)
    assert client.post("/api/residents", json={"id": "2w-090", "display_name": "Tom Reyes"}).json()["id"] == "2W-090"
    dup = client.post("/api/residents", json={"id": "2W-090", "display_name": "Someone Else"})
    assert dup.status_code == 409 and "already used" in dup.json()["detail"]
    assert client.post("/api/residents", json={"display_name": "   "}).status_code == 422
    assert client.post("/api/residents", json={"id": "bad id!", "display_name": "x"}).status_code == 422
    highest = max(int(r["id"][3:]) for r in client.get("/api/residents").json() if r["id"][3:].isdigit())
    assert client.get("/api/residents/next-id").json()["id"] == f"2W-{highest + 1:03d}"  # after the highest in use


def test_add_patient_needs_sign_in(client):
    assert client.post("/api/residents", json={"display_name": "Nobody"}).status_code == 401
    assert client.get("/api/residents/next-id").status_code == 401
