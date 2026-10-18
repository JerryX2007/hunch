"""Unit tests for the `care_notes` repository."""

import pytest
from unittest.mock import patch, MagicMock

from backend.app.repositories.care_notes_repository import list_all, get_by_id, upsert, delete


@pytest.fixture(autouse=True)
def mock_supabase():
    """Patch the Supabase client used by the repository."""
    with patch("backend.app.database.supabase.table") as mock_table:
        mock_sel = MagicMock()
        mock_exe = MagicMock()
        mock_exe.data = [
            {"id": "c1", "resident_id": "r1", "recorded_at": "2024-01-01"}
        ]
        mock_sel.return_value = mock_exe
        mock_table.return_value = mock_sel
        yield
        mock_table.reset_mock()


def test_list_all_returns_mocked_data():
    """list_all should return the mocked rows (optionally filtered)."""
    data = list_all()
    assert len(data) == 1
    assert data[0]["id"] == "c1"


def test_list_all_filtered_by_resident():
    """list_all with a resident_id should filter."""
    data = list_all(resident_id="r1")
    assert len(data) == 1
    assert data[0]["resident_id"] == "r1"


def test_get_by_id_returns_mocked_row():
    """get_by_id should return the row with the matching id."""
    row = get_by_id("c1")
    assert row is not None
    assert row["id"] == "c1"


def test_upsert_raises_when_missing_id():
    """upsert should raise RuntimeError when Supabase returns no data."""
    with patch("backend.app.database.supabase.table") as mock_table:
        mock_sel = MagicMock()
        mock_exe = MagicMock()
        mock_exe.data = None
        mock_sel.return_value = mock_exe
        mock_table.return_value = mock_sel
        with pytest.raises(RuntimeError) as exc:
            upsert({"id": "c2", "resident_id": "r2", "recorded_at": "2024-01-02"})
        assert "Supabase error" in str(exc.value)


def test_delete_does_not_raise():
    """delete should complete without exception."""
    delete("c1")