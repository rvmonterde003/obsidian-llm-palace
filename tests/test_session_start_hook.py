import subprocess
from pathlib import Path
import pytest
from scripts.session_start_hook import (
    load_skip_prefixes,
    should_skip,
    invoke_wake_up,
    main,
)


def test_load_skip_prefixes_reads_one_per_line(tmp_path):
    f = tmp_path / "prefixes.txt"
    f.write_text("_archive_\n_disabled_\n# comment\n\n  _whitespace_  \n")
    prefixes = load_skip_prefixes(f)
    assert prefixes == ["_archive_", "_disabled_", "_whitespace_"]


def test_should_skip_matches_prefix():
    assert should_skip("_archive_old-project", ["_archive_"]) is True
    assert should_skip("active-project", ["_archive_"]) is False
    assert should_skip("_archive_", ["_archive_"]) is True


def test_should_skip_returns_false_when_no_prefixes():
    assert should_skip("anything", []) is False


def test_invoke_wake_up_passes_utf8_env(mocker):
    fake_run = mocker.patch("scripts.session_start_hook.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="hello", stderr="")
    out = invoke_wake_up("my-wing")
    assert out == "hello"
    args, kwargs = fake_run.call_args
    assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
    cmd = args[0]
    assert "wake-up" in cmd
    assert "my-wing" in cmd


def test_invoke_wake_up_returns_empty_on_subprocess_failure(mocker):
    fake_run = mocker.patch("scripts.session_start_hook.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="oops")
    assert invoke_wake_up("dead-wing") == ""


def test_invoke_wake_up_returns_empty_on_timeout(mocker):
    fake_run = mocker.patch("scripts.session_start_hook.subprocess.run")
    fake_run.side_effect = subprocess.TimeoutExpired(cmd=["mempalace"], timeout=10)
    assert invoke_wake_up("any-wing") == ""


def test_invoke_wake_up_returns_empty_when_mempalace_missing(mocker):
    fake_run = mocker.patch("scripts.session_start_hook.subprocess.run")
    fake_run.side_effect = FileNotFoundError("mempalace not found")
    assert invoke_wake_up("any-wing") == ""


def test_main_skips_when_wing_matches_prefix(mocker, tmp_path, capsys, monkeypatch):
    project = tmp_path / "_archive_dead"
    project.mkdir()
    monkeypatch.chdir(project)
    skip_file = tmp_path / "skips.txt"
    skip_file.write_text("_archive_\n")
    fake_invoke = mocker.patch("scripts.session_start_hook.invoke_wake_up")
    rc = main(skip_file=skip_file)
    assert rc == 0
    fake_invoke.assert_not_called()
    captured = capsys.readouterr()
    # Skipped wings emit nothing to stdout (no tokens injected)
    assert captured.out == ""


def test_main_invokes_wake_up_for_live_wing(mocker, tmp_path, capsys, monkeypatch):
    project = tmp_path / "live-wing"
    project.mkdir()
    monkeypatch.chdir(project)
    skip_file = tmp_path / "skips.txt"
    skip_file.write_text("_archive_\n")
    mock_invoke = mocker.patch("scripts.session_start_hook.invoke_wake_up", return_value="WAKE_UP_PAYLOAD")
    rc = main(skip_file=skip_file)
    assert rc == 0
    mock_invoke.assert_called_once_with("live-wing")
    captured = capsys.readouterr()
    assert "WAKE_UP_PAYLOAD" in captured.out
