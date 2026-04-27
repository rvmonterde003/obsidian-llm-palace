import pytest
from scripts.archive_wing import (
    list_all_drawer_ids_for_wing,
    archive_wing,
)


def test_list_all_drawer_ids_paginates(mocker):
    """When the wing has more drawers than one page, paginate via offset."""
    fake_list = mocker.patch("scripts.archive_wing.tool_list_drawers")
    # First page returns 100, second returns 50, third returns 0
    fake_list.side_effect = [
        {"drawers": [{"id": f"d{i}"} for i in range(100)]},
        {"drawers": [{"id": f"d{i}"} for i in range(100, 150)]},
        {"drawers": []},
    ]
    ids = list_all_drawer_ids_for_wing("foo")
    assert len(ids) == 150
    assert ids[0] == "d0"
    assert ids[-1] == "d149"
    # Verify pagination calls
    assert fake_list.call_count == 3
    # Each call should pass wing="foo" and a limit
    for call in fake_list.call_args_list:
        assert call.kwargs.get("wing") == "foo" or "foo" in call.args


def test_list_all_drawer_ids_empty_when_no_results(mocker):
    fake_list = mocker.patch("scripts.archive_wing.tool_list_drawers")
    fake_list.return_value = {"drawers": []}
    assert list_all_drawer_ids_for_wing("nonexistent") == []


def test_list_all_drawer_ids_handles_error_response(mocker):
    """If tool_list_drawers returns {'error': ...}, return [] gracefully."""
    fake_list = mocker.patch("scripts.archive_wing.tool_list_drawers")
    fake_list.return_value = {"error": "no palace"}
    assert list_all_drawer_ids_for_wing("foo") == []


def test_archive_wing_calls_update_drawer_per_id(mocker, capsys):
    mocker.patch(
        "scripts.archive_wing.list_all_drawer_ids_for_wing",
        return_value=["d1", "d2"],
    )
    fake_update = mocker.patch("scripts.archive_wing.tool_update_drawer")
    fake_update.return_value = {"success": True}
    rc = archive_wing("foo")
    assert rc == 0
    assert fake_update.call_count == 2
    for call in fake_update.call_args_list:
        # Each call should pass the new wing name
        assert call.kwargs.get("wing") == "_archive_foo" or "_archive_foo" in call.args


def test_archive_wing_returns_nonzero_when_update_fails(mocker):
    mocker.patch(
        "scripts.archive_wing.list_all_drawer_ids_for_wing",
        return_value=["d1"],
    )
    fake_update = mocker.patch("scripts.archive_wing.tool_update_drawer")
    fake_update.return_value = {"success": False, "error": "boom"}
    rc = archive_wing("foo")
    assert rc != 0


def test_archive_wing_no_op_when_wing_empty(mocker, capsys):
    mocker.patch("scripts.archive_wing.list_all_drawer_ids_for_wing", return_value=[])
    fake_update = mocker.patch("scripts.archive_wing.tool_update_drawer")
    rc = archive_wing("ghost")
    assert rc == 0
    fake_update.assert_not_called()
    out = capsys.readouterr().out
    assert "no drawers" in out.lower() or "0 drawer" in out.lower()


def test_archive_wing_refuses_to_archive_already_archived(mocker, capsys):
    """Don't double-archive — return error if wing already starts with _archive_."""
    fake_update = mocker.patch("scripts.archive_wing.tool_update_drawer")
    rc = archive_wing("_archive_foo")
    assert rc != 0
    fake_update.assert_not_called()
    err = capsys.readouterr().err.lower() + capsys.readouterr().out.lower()
    assert "already" in err or "archived" in err


def test_list_all_drawer_ids_returns_partial_on_exception(mocker):
    """If tool_list_drawers raises mid-pagination, return what we have so far."""
    fake_list = mocker.patch("scripts.archive_wing.tool_list_drawers")
    fake_list.side_effect = [
        {"drawers": [{"id": f"d{i}"} for i in range(100)]},
        RuntimeError("connection lost"),
    ]
    ids = list_all_drawer_ids_for_wing("foo")
    assert len(ids) == 100
    assert ids[0] == "d0"


def test_archive_wing_returns_nonzero_when_update_raises(mocker):
    mocker.patch("scripts.archive_wing.list_all_drawer_ids_for_wing", return_value=["d1"])
    fake_update = mocker.patch("scripts.archive_wing.tool_update_drawer")
    fake_update.side_effect = RuntimeError("db locked")
    rc = archive_wing("foo")
    assert rc != 0
