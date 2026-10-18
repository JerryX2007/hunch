"""Unit tests for the `residents` repository."""

import pytest

from backend.app.repositories.residents_repository import delete, get_by_id, list_all, upsert


@pytest.fixture(autouse=True)
def mock_supabase(fake_supabase):
    fake_supabase.rows = [{"id": "DEMO-014", "display_name": "DEMO-014"}]
    return fake_supabase


def test_list_and_get():
    assert list_all()[0]["id"] == "DEMO-014"
    assert get_by_id("DEMO-014")["display_name"] == "DEMO-014"
    assert get_by_id("NOPE") is None


def test_upsert_needs_id():
    with pytest.raises(ValueError):
        upsert({"display_name": "No ID"})


def test_upsert_raises_when_no_row(mock_supabase):
    mock_supabase.rows = []
    with pytest.raises(RuntimeError) as exc:
        upsert({"id": "DEMO-030", "display_name": "x"})
    assert "Supabase error" in str(exc.value)


def test_delete_does_not_raise():
    delete("DEMO-014")
