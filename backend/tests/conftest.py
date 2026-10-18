import pytest
from unittest.mock import patch, MagicMock

# Shared fixture that patches the global supabase.client.table() call
@pytest.fixture(autouse=True)
def mock_supabase():
    """Patch supabase.table so tests don't hit a real Supabase project."""
    with patch("backend.app.database.supabase.table") as mock_table:
        # Create a mock chain: .select().execute().data
        mock_sel = MagicMock()
        mock_exe = MagicMock()
        mock_exe.data = [
            {"id": "test", "display_name": "Mock Resident"}
        ]
        mock_sel.return_value = mock_exe
        mock_table.return_value = mock_sel
        yield
        mock_table.reset_mock()