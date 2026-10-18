"""Shared test setup. No test talks to a real Supabase project.

- Dummy Supabase settings are used when backend/.env doesn't provide them, so
  ``app.database`` imports anywhere (CI, a fresh clone).
- ``fake_supabase`` replaces ``supabase.table(...)`` with a chainable fake:
  every builder call (select/eq/order/upsert/...) returns the same query, ``eq``
  filters the rows, and ``execute().data`` returns them (one row after
  ``single``/``maybe_single``). Set ``fake_supabase.rows`` in a test.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND), str(BACKEND.parent)]  # `app.*` and `backend.app.*` both import

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("HUNCH_MODE", "demo")      # the pipeline uses in-memory data in tests
os.environ.setdefault("HUNCH_LLM_EXPLAIN", "0")  # never call Gemini from tests


class FakeQuery:
    def __init__(self, store, table):
        self.store, self.table, self.filters, self.one = store, table, [], False

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def single(self):
        self.one = True
        return self

    maybe_single = single

    def __getattr__(self, name):  # select, order, limit, range, upsert, insert, update, delete, in_ ...
        def chain(*args, **kwargs):
            return self
        return chain

    def execute(self):
        rows = self.store.rows
        if rows is not None:
            rows = [r for r in rows if all(r.get(c, v) == v for c, v in self.filters)]
        if self.one:
            rows = rows[0] if rows else None
        return SimpleNamespace(data=rows)


class FakeSupabase:
    def __init__(self):
        self.rows = []
        self.tables = []

    def table(self, name):
        self.tables.append(name)
        return FakeQuery(self, name)


@pytest.fixture
def fake_supabase():
    # The app is importable as `app.*` (from backend/) and `backend.app.*` (from the
    # repo root); each has its own database module and client, so patch both.
    from contextlib import ExitStack

    from app import database as db_a
    from backend.app import database as db_b
    fake = FakeSupabase()
    with ExitStack() as stack:
        for db in {id(db_a): db_a, id(db_b): db_b}.values():
            stack.enter_context(patch.object(db.supabase, "table", side_effect=fake.table))
        yield fake
