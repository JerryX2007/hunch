"""Unit tests for the `profiles` repository."""

import pytest

from backend.app.repositories.profiles_repository import list_all, get_by_id, upsert, delete


@pytest.fixture(autouse=True)
def mock_supabase(fake_supabase):
    """Every query returns these rows (see tests/conftest.py)."""
    fake_supabase.rows = [{"id": "p1", "display_name": "Test"}]
    return fake_supabase


def test_list_all_returns_mocked_data():
    """list_all should return the mocked rows."""
    data = list_all()
    assert data == [{"id": "p1", "display_name": "Test"}]


def test_get_by_id_returns_mocked_row():
    """get_by_id should return the row with the matching id."""
    # The mock currently returns the same row for any id; we just test no crash.
    row = get_by_id("p1")
    assert row is not None
    assert row["id"] == "p1"


def test_upsert_raises_when_missing_id(mock_supabase):
    """upsert should raise RuntimeError when Supabase returns no data."""
    mock_supabase.rows = []
    with pytest.raises(RuntimeError) as exc:
        upsert({"display_name": "Oops"})
    assert "Supabase error" in str(exc.value)


def test_delete_does_not_raise():
    """delete should succeed (no exception) when the mock data is present."""
    # The mock currently does not raise; just ensure no exception.
    delete("p1")