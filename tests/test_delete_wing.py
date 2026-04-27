import pytest
from scripts.delete_wing import (
    list_tunnel_ids_for_wing,
    delete_wing,
)


def test_list_tunnel_ids_parses_dict_with_tunnels_key(mocker):
    """tool_list_tunnels returns {'tunnels': [...]} (most likely shape)."""
    mocker.patch(
        "scripts.delete_wing.tool_list_tunnels",
        return_value={"tunnels": [{"id": "t1"}, {"id": "t2"}]},
    )
    assert list_tunnel_ids_for_wing("foo") == ["t1", "t2"]


def test_list_tunnel_ids_parses_bare_list(mocker):
    """If tool_list_tunnels returns a bare list, handle that too."""
    mocker.patch(
        "scripts.delete_wing.tool_list_tunnels",
        return_value=[{"id": "t1"}, {"id": "t2"}],
    )
    assert list_tunnel_ids_for_wing("foo") == ["t1", "t2"]


def test_list_tunnel_ids_empty_on_error_response(mocker):
    mocker.patch(
        "scripts.delete_wing.tool_list_tunnels",
        return_value={"error": "boom"},
    )
    assert list_tunnel_ids_for_wing("foo") == []


def test_list_tunnel_ids_empty_on_exception(mocker):
    mocker.patch(
        "scripts.delete_wing.tool_list_tunnels",
        side_effect=RuntimeError("oops"),
    )
    assert list_tunnel_ids_for_wing("foo") == []


def test_delete_wing_aborts_when_not_confirmed(mocker, capsys):
    mocker.patch("scripts.delete_wing.list_all_drawer_ids_for_wing", return_value=["d1"])
    mocker.patch("scripts.delete_wing.list_tunnel_ids_for_wing", return_value=[])
    fake_delete = mocker.patch("scripts.delete_wing.tool_delete_drawer")
    rc = delete_wing("doomed", confirmed=False)
    assert rc != 0
    fake_delete.assert_not_called()
    out = capsys.readouterr().out.lower()
    assert "abort" in out or "confirm" in out


def test_delete_wing_iterates_delete_drawer(mocker):
    mocker.patch("scripts.delete_wing.list_all_drawer_ids_for_wing", return_value=["d1", "d2", "d3"])
    mocker.patch("scripts.delete_wing.list_tunnel_ids_for_wing", return_value=[])
    fake_delete = mocker.patch("scripts.delete_wing.tool_delete_drawer", return_value={"success": True})
    rc = delete_wing("doomed", confirmed=True)
    assert rc == 0
    assert fake_delete.call_count == 3


def test_delete_wing_also_deletes_tunnels(mocker):
    mocker.patch("scripts.delete_wing.list_all_drawer_ids_for_wing", return_value=["d1"])
    mocker.patch("scripts.delete_wing.list_tunnel_ids_for_wing", return_value=["t1", "t2"])
    mocker.patch("scripts.delete_wing.tool_delete_drawer", return_value={"success": True})
    fake_dt = mocker.patch("scripts.delete_wing.tool_delete_tunnel", return_value={"success": True})
    rc = delete_wing("doomed", confirmed=True)
    assert rc == 0
    assert fake_dt.call_count == 2


def test_delete_wing_no_op_when_empty(mocker, capsys):
    mocker.patch("scripts.delete_wing.list_all_drawer_ids_for_wing", return_value=[])
    mocker.patch("scripts.delete_wing.list_tunnel_ids_for_wing", return_value=[])
    fake_delete = mocker.patch("scripts.delete_wing.tool_delete_drawer")
    rc = delete_wing("ghost", confirmed=True)
    assert rc == 0
    fake_delete.assert_not_called()


def test_delete_wing_returns_nonzero_when_drawer_delete_fails(mocker):
    mocker.patch("scripts.delete_wing.list_all_drawer_ids_for_wing", return_value=["d1"])
    mocker.patch("scripts.delete_wing.list_tunnel_ids_for_wing", return_value=[])
    mocker.patch(
        "scripts.delete_wing.tool_delete_drawer",
        return_value={"success": False, "error": "boom"},
    )
    rc = delete_wing("doomed", confirmed=True)
    assert rc != 0


def test_delete_wing_returns_nonzero_when_drawer_delete_raises(mocker):
    mocker.patch("scripts.delete_wing.list_all_drawer_ids_for_wing", return_value=["d1"])
    mocker.patch("scripts.delete_wing.list_tunnel_ids_for_wing", return_value=[])
    mocker.patch(
        "scripts.delete_wing.tool_delete_drawer",
        side_effect=RuntimeError("db locked"),
    )
    rc = delete_wing("doomed", confirmed=True)
    assert rc != 0
