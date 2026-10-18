"""Unit tests for the `observations` repository."""

import pytest

from backend.app.repositories.observations_repository import get_all, get_by_id, upsert, delete


@pytest.fixture(autouse=True)
def mock_supabase(fake_supabase):
    """Every query returns these rows (see tests/conftest.py)."""
    fake_supabase.rows = [{"id": "o1", "resident_id": "r1", "category": "nutrition"}]
    return fake_supabase


def test_get_all_returns_mocked_data():
    """get_all should return the mocked rows (optionally filtered)."""
    data = get_all()
    assert len(data) == 1
    assert data[0]["id"] == "o1"


def test_get_all_filtered_by_resident():
    """get_all with resident_id should filter."""
    data = get_all(resident_id="r1")
    assert len(data) == 1
    assert data[0]["resident_id"] == "r1"


def test_get_by_id_returns_mocked_row():
    """get_by_id should return the row with the matching id."""
    row = get_by_id("o1")
    assert row is not None
    assert row["id"] == "o1"


def test_upsert_raises_when_missing_id(mock_supabase):
    """upsert should raise RuntimeError when Supabase returns no data."""
    mock_supabase.rows = []
    with pytest.raises(RuntimeError) as exc:
        upsert({"id": "o2", "resident_id": "r2", "category": "energy"})
    assert "Supabase error" in str(exc.value)


def test_delete_does_not_raise():
    """delete should complete without exception."""
    delete("o1")