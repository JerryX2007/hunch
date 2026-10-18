"""Unit tests for the `alerts` repository."""

import pytest

from backend.app.repositories.alerts_repository import get_all, get_by_id, upsert, delete


@pytest.fixture(autouse=True)
def mock_supabase(fake_supabase):
    """Every query returns these rows (see tests/conftest.py)."""
    fake_supabase.rows = [{"id": "a1", "title": "Test Alert", "urgent": False}]
    return fake_supabase


def test_get_all_returns_mocked_data():
    """get_all should return the mocked rows."""
    data = get_all()
    assert len(data) == 1
    assert data[0]["title"] == "Test Alert"


def test_get_by_id_returns_mocked_row():
    """get_by_id should return the row with the matching id."""
    row = get_by_id("a1")
    assert row is not None
    assert row["id"] == "a1"


def test_upsert_raises_when_missing_id(mock_supabase):
    """upsert should raise RuntimeError when Supabase returns no data."""
    mock_supabase.rows = []
    with pytest.raises(RuntimeError) as exc:
        upsert({"id": "a2", "title": "Oops", "urgent": True})
    assert "Supabase error" in str(exc.value)


def test_delete_does_not_raise():
    """delete should complete without exception."""
    delete("a1")