"""Unit tests for the `profiles` repository."""

import pytest
from unittest.mock import patch, MagicMock

from backend.app.repositories.profiles_repository import list_all, get_by_id, upsert, delete


@pytest.fixture(autouse=True)
def mock_supabase():
    """Patch the Supabase client used by the repository."""
    with patch("backend.app.database.supabase.table") as mock_table:
        mock_sel = MagicMock()
        mock_exe = MagicMock()
        mock_exe.data = [{"id": "p1", "display_name": "Test"}]
        mock_sel.return_value = mock_exe
        mock_table.return_value = mock_sel
        yield
        mock_table.reset_mock()


def test_list_all_returns_mocked_data():
    """list_all should return the mocked rows."""
    data = list_all()
    assert data == [{"id": "p1", "display_name": "Mock Resident"}]


def test_get_by_id_returns_mocked_row():
    """get_by_id should return the row with the matching id."""
    # The mock currently returns the same row for any id; we just test no crash.
    row = get_by_id("p1")
    assert row is not None
    assert row["id"] == "p1"


def test_upsert_raises_when_missing_id():
    """upsert should propagate a RuntimeError when Supabase returns an error."""
    with patch("backend.app.database.supabase.table") as mock_table:
        # Make the upsert path raise a generic error
        mock_sel = MagicMock()
        mock_exe = MagicMock()
        mock_exe.data = None  # simulate no data returned
        mock_sel.return_value = mock_exe
        mock_table.return_value = mock_sel
        with pytest.raises(RuntimeError) as exc:
            upsert({"display_name": "Oops"})
        # The error message should be formatted via format_supabase_error
        assert "Supabase error" in str(exc.value)


def test_delete_does_not_raise():
    """delete should succeed (no exception) when the mock data is present."""
    # The mock currently does not raise; just ensure no exception.
    delete("p1")