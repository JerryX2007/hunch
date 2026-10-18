"""Gemini note reading, with Gemini replaced by a stand-in (no network, no key needed).

Checks that Python, not Gemini, has the last word: quotes must be in the note, rules still
count and decide what's ruled out, unread non-English notes are never "quiet", and saving
a note never fails because of Gemini.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.history import ai_read, service
from app.history.check import check_resident
from app.models import note_reader

DATA = Path(__file__).resolve().parents[2] / "test_data"
TAGALOG = "Nahulog siya sa banyo kaninang umaga. Hindi kumain ng almusal."
TAGALOG_EN = "She fell in the bathroom this morning. Did not eat breakfast."


def reading(observations=(), events=(), language="en", translation=None):
    return {"index": 0, "language": language, "translation_en": translation,
            "observations": list(observations), "events": list(events)}


def obs(category, quote, direction="worsening", sub=None, change=None):
    return {"category": category, "direction": direction, "source_text": quote, "note": "",
            "subcategory": sub, "change": change}


# --- validate ---------------------------------------------------------------
def test_quote_must_be_in_the_note():
    text = "Barely touched her lunch. Seemed more tired than usual."
    r = ai_read.validate(reading([obs("nutrition", "barely touched her lunch"),
                                  obs("pain", "complained of knee pain")]), text, "m")
    assert r["status"] == "ok"
    assert [o["category"] for o in r["observations"]] == ["nutrition"]
    assert any("pain: quote not found" in d for d in r["dropped"])


def test_small_quote_slips_are_allowed_but_inventions_are_not():
    text = "Mrs. K was picking at her food at dinner, ate maybe a quarter."
    assert ai_read.quote_found("picking at her food at dinner ate maybe a quarter", text)
    assert ai_read.quote_found("Picking at her food, at dinner", text)
    assert not ai_read.quote_found("refused all of her dinner", text)


def test_bad_categories_and_incomplete_toileting_are_dropped():
    text = "No BM for 4 days. Fever 38.2."
    r = ai_read.validate(reading([obs("fever", "Fever 38.2"),
                                  obs("toileting", "No BM for 4 days"),
                                  obs("toileting", "No BM for 4 days", sub="bowel", change="decreased")]), text)
    assert [(o["category"], o["subcategory"]) for o in r["observations"]] == [("toileting", "bowel")]


def test_denied_events_are_dropped_but_a_later_denial_does_not_undo_a_fall():
    text = "No falls this shift. Found on the floor at 0300, did not hit her head."
    r = ai_read.validate(reading(events=[{"type": "fall", "source_text": "No falls this shift"},
                                         {"type": "fall", "source_text": "Found on the floor at 0300, did not hit her head"}]),
                         text)
    assert [e["source_text"] for e in r["events"]] == ["Found on the floor at 0300, did not hit her head"]


def test_quote_may_come_from_the_original_or_the_translation():
    r = ai_read.validate(reading([obs("nutrition", "Hindi kumain ng almusal"), obs("mobility", "She fell in the bathroom")],
                                 language="tl", translation=TAGALOG_EN), TAGALOG)
    assert {o["category"] for o in r["observations"]} == {"nutrition", "mobility"}
    assert r["translation_en"] == TAGALOG_EN and r["language"] == "tl"


def test_english_notes_keep_no_translation():
    r = ai_read.validate(reading(language="en", translation="same text"), "Ate well.")
    assert r["translation_en"] is None


def test_missing_reading_is_a_failure_not_an_empty_reading():
    assert ai_read.validate(None, "Ate well.")["status"] == "failed"


# --- read_note --------------------------------------------------------------
def note(text, when="2026-10-10T08:00:00", rid="R1", reading_=None, nid="n1"):
    n = {"id": nid, "resident_id": rid, "note_text": text, "recorded_at": when, "author_role": "PSW"}
    if reading_ is not None:
        n["ai_reading"] = reading_
    return n


def test_gemini_adds_what_the_rules_missed():
    text = "Barely touched her lunch. Picking at her food."
    assert not ai_read.read_note(note(text)).meals  # the rules don't know these phrasings
    r = ai_read.validate(reading([obs("nutrition", "Barely touched her lunch"),
                                  obs("energy", "Picking at her food")]), text)
    f = ai_read.read_note(note(text, reading_=r))
    assert f.read_by == "ai"
    assert f.meals and f.meals[0].said_less and f.meals[0].source == "ai"
    assert [(s.category, s.source) for s in f.signals] == [("energy", "ai")]


def test_rules_win_ties_and_decide_what_is_ruled_out():
    text = "Drowsy after lunch. Denies pain."
    r = ai_read.validate(reading([obs("energy", "Drowsy after lunch"), obs("pain", "Denies pain")]), text)
    f = ai_read.read_note(note(text, reading_=r))
    assert [(s.category, s.source) for s in f.signals] == [("energy", "rules")]


def test_translated_note_is_read_by_the_rules_too():
    r = ai_read.validate(reading([obs("nutrition", "Hindi kumain ng almusal")], language="tl",
                                 translation=TAGALOG_EN), TAGALOG)
    f = ai_read.read_note(note(TAGALOG, reading_=r))
    falls = [s for s in f.signals if s.category == "mobility"]
    assert falls and falls[0].urgent and falls[0].source == "rules"  # "fell" in the translation
    assert f.translation == TAGALOG_EN and f.language == "tl"


def test_reported_event_is_urgent():
    text = "Took a tumble in the hallway after dinner."
    r = ai_read.validate(reading(events=[{"type": "fall", "source_text": "Took a tumble in the hallway"}]), text)
    f = ai_read.read_note(note(text, reading_=r))
    assert [(s.category, s.urgent, s.source) for s in f.signals] == [("mobility", True, "ai")]


def test_old_or_failed_readings_are_ignored():
    text = "Barely touched her lunch."
    for bad in ({**ai_read.validate(reading([obs("nutrition", text)]), text), "v": 0},
                ai_read.validate(None, text)):
        assert ai_read.read_note(note(text, reading_=bad)).read_by == "rules"


# --- unreadable notes are never "quiet" -------------------------------------
def _history(rid, recent_text, reading_=None):
    start = datetime(2026, 10, 1, 8)
    notes = [note("Ate all of breakfast. Up walking with walker.", (start + timedelta(days=d)).isoformat(),
                  rid, nid=f"b{d}") for d in range(10)]
    notes.append(note(recent_text, (start + timedelta(days=10)).isoformat(), rid, reading_, nid="new"))
    return {"id": rid}, notes


def test_unread_non_english_note_asks_the_nurse_to_read_it():
    resident, notes = _history("R9", TAGALOG)
    c = check_resident(resident, notes)
    assert c.tier == "watch" and c.unread_notes and c.unread_notes[0]["note_id"] == "new"
    assert "couldn't be read" in c.reasons[0]
    assert c.title == "A recent note needs reading"


def test_same_note_read_by_gemini_is_urgent():
    r = ai_read.validate(reading(language="tl", translation=TAGALOG_EN), TAGALOG)
    resident, notes = _history("R9", TAGALOG, r)
    c = check_resident(resident, notes)
    assert c.tier == "urgent" and not c.unread_notes
    ev = next(f for f in c.findings if f.urgent).evidence[0]
    assert ev.translation == TAGALOG_EN and ev.language == "tl"
    assert c.reading == {"notes": 11, "read_by_ai": 1}


# --- asking Gemini, saving, caching -----------------------------------------
class FakeGemini:
    """Stands in for note_reader.read_notes. Reads each note by a simple lookup."""

    def __init__(self, answers=None, fail=False):
        self.answers, self.fail, self.calls = answers or {}, fail, []

    def __call__(self, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise RuntimeError("429 rate limited")
        return {"model": "fake-model",
                "readings": [{**self.answers.get(t, reading()), "index": i} for i, t in enumerate(texts)]}


@pytest.fixture
def gemini(monkeypatch, tmp_path):
    fake = FakeGemini({TAGALOG: reading(language="tl", translation=TAGALOG_EN)})
    monkeypatch.setattr(note_reader, "read_notes", fake)
    monkeypatch.setattr(note_reader, "ai_enabled", lambda: True)
    monkeypatch.setattr(ai_read, "CACHE_FILE", tmp_path / "cache.json")
    monkeypatch.setattr(ai_read, "_cache", None)
    return fake


class SavingStore:
    def __init__(self):
        self.saved = {}

    def save_note_reading(self, note_id, r):
        self.saved[note_id] = r


def test_ensure_read_saves_caches_and_never_sends_a_note_twice(gemini):
    store = SavingStore()
    notes = [note(f"Ate {p}% of breakfast.", nid=f"n{p}") for p in range(0, 30)] + [note(TAGALOG, nid="tl")]
    out = ai_read.ensure_read(notes, store)
    assert out["read"] == 31 and out["failed"] == 0
    assert len(gemini.calls) == 3  # batches of 12
    assert store.saved["tl"]["translation_en"] == TAGALOG_EN
    assert ai_read.ensure_read(notes, store)["already_read"] == 31 and len(gemini.calls) == 3
    fresh = [note(n["note_text"], nid=n["id"] + "-copy") for n in notes]  # same text, new rows
    out = ai_read.ensure_read(fresh, store)
    assert out["from_cache"] == 31 and len(gemini.calls) == 3
    assert json.loads(ai_read.CACHE_FILE.read_text())  # cache written


def test_gemini_failure_leaves_notes_to_the_rules(gemini):
    gemini.fail = True
    notes = [note("Barely touched her lunch.")]
    out = ai_read.ensure_read(notes, SavingStore())
    assert out == {**out, "read": 0, "failed": 1}
    assert "ai_reading" not in notes[0]


def test_without_a_key_nothing_is_sent(monkeypatch):
    called = []
    monkeypatch.setattr(note_reader, "read_notes", lambda t: called.append(t))
    out = ai_read.ensure_read([note("Ate well.")])
    assert out["skipped"] == 1 and not called


def test_saving_a_note_has_gemini_read_it(gemini):
    rid = json.loads((DATA / "residents.json").read_text())[0]["id"]
    out = service.add_note(rid, TAGALOG)
    assert out["note"]["ai_reading"]["translation_en"] == TAGALOG_EN
    saved = next(n for n in service.get_store().notes(rid) if n["note_text"] == TAGALOG)
    assert saved["ai_reading"]["language"] == "tl" and saved["extraction_status"] == "ai_read"
    assert out["result"]["tier"] == "urgent"  # the fall, read from the translation


def test_saving_a_note_still_works_when_gemini_fails(gemini):
    gemini.fail = True
    rid = json.loads((DATA / "residents.json").read_text())[1]["id"]
    out = service.add_note(rid, "Barely touched her dinner tonight.")
    assert out["note"]["ai_reading"] is None and out["result"] is not None


def test_supabase_keeps_readings_in_memory_until_the_migration_is_run():
    from app.store import SupabaseStore

    class Table:
        def update(self, row):
            raise RuntimeError("Could not find the 'ai_reading' column of 'care_notes' in the schema cache")

    class DB:
        @staticmethod
        def get_care_notes(resident_id=None):
            return [{"id": "n1", "note_text": "Ate well."}, {"id": "n2", "note_text": "Drowsy."}]

    s = object.__new__(SupabaseStore)
    s.db, s.sb, s._readings, s._no_reading_column = DB, type("SB", (), {"table": lambda self, name: Table()})(), {}, False
    s.save_note_reading("n2", {"v": 1, "status": "ok"})
    assert s._no_reading_column
    assert [n.get("ai_reading") for n in s.notes()] == [None, {"v": 1, "status": "ok"}]


def test_non_english_reading_without_a_translation_does_not_count():
    r = ai_read.validate(reading(language="tl", translation=None), TAGALOG)
    assert r["status"] == "failed"
    assert ai_read.read_note(note(TAGALOG, reading_=r)).unreadable  # still flagged for the nurse
