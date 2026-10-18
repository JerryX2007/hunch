"""scripts/reseed_notes.py against an in-memory stand-in for Supabase."""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "test_data"


class Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, [], "select", None

    def select(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def range(self, a, b):
        self.window = (a, b)
        return self

    def in_(self, col, vals):
        self.filters.append(lambda r: r.get(col) in vals)
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def lt(self, col, val):
        self.filters.append(lambda r: str(r.get(col))[:19] < val)
        return self

    def is_(self, col, val):
        self.filters.append(lambda r: r.get(col) is None)
        return self

    def delete(self):
        self.op = "delete"
        return self

    def insert(self, rows):
        self.op, self.payload = "insert", rows
        return self

    def upsert(self, rows):
        self.op, self.payload = "upsert", rows
        return self

    def update(self, row):
        self.op, self.payload = "update", row
        return self

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        hit = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == "delete":
            self.db[self.table] = [r for r in rows if r not in hit]
        elif self.op in ("insert", "upsert"):
            for i, r in enumerate(self.payload):
                rows.append({"id": f"{self.table}-{len(rows)}-{i}", "author_id": None, **r})
        elif self.op == "update":
            for r in hit:
                r.update(self.payload)
        if hasattr(self, "window"):
            hit = hit[self.window[0]:self.window[1] + 1]
        return type("R", (), {"data": hit})()


class FakeSB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return Q(self.tables, name)


def test_reseed_replaces_seed_notes_and_keeps_later_ones():
    from scripts import reseed_notes

    new_notes = json.loads((DATA / "notes.json").read_text())
    tables = {
        "care_notes": [
            {"id": "old-1", "resident_id": "2W-014", "recorded_at": "2026-10-16T08:00:00", "note_text": "Ate all of breakfast."},
            {"id": "old-2", "resident_id": "2W-017", "recorded_at": "2026-09-21T08:00:00", "note_text": "Ate well."},
            {"id": "mine", "resident_id": "2W-014", "recorded_at": "2026-10-18T07:48:00", "note_text": "Added in the app."},
            {"id": "other", "resident_id": "2W-023", "recorded_at": "2026-10-01T08:00:00", "note_text": "New resident."},
        ],
        "alerts": [{"id": "a1", "resident_id": "2W-014"}, {"id": "a2", "resident_id": "2W-023"}],
        "profiles": [{"id": "u-priya", "full_name": "Priya Raman"}],
    }
    asked = []
    assert reseed_notes.main([], sb=FakeSB(tables), ask=lambda q: asked.append(q) or "yes") == 0

    notes = tables["care_notes"]
    ids = {n["id"] for n in notes}
    assert "old-1" not in ids and "old-2" not in ids          # seed-period notes replaced
    assert {"mine", "other"} <= ids                            # later notes and other residents kept
    assert len(notes) == len(new_notes) + 2
    assert [a["id"] for a in tables["alerts"]] == ["a2"]       # only seed residents' alerts cleared
    priya = [n for n in notes if n.get("author_name") == "Priya Raman"]
    assert priya and all(n["author_id"] == "u-priya" for n in priya)
    assert asked  # it asked first


def test_reseed_changes_nothing_without_a_yes():
    from scripts import reseed_notes

    tables = {"care_notes": [{"id": "old-1", "resident_id": "2W-014", "recorded_at": "2026-10-16T08:00:00"}]}
    assert reseed_notes.main([], sb=FakeSB(tables), ask=lambda q: "no") == 1
    assert [n["id"] for n in tables["care_notes"]] == ["old-1"]
