import subprocess
from pathlib import Path
import pytest
from scripts.backfill_run import (
    build_mine_command,
    run_one_row,
    run_plan,
)


def test_build_mine_command_includes_mode_convos_and_wing():
    cmd = build_mine_command(
        encoded_dir=Path("/fake/projects/C--Users-Admin-foo"),
        wing="foo",
    )
    assert "mempalace" in cmd
    assert "mine" in cmd
    assert "--mode" in cmd
    assert "convos" in cmd
    assert "--wing" in cmd
    assert "foo" in cmd
    assert str(Path("/fake/projects/C--Users-Admin-foo")) in cmd


def test_run_one_row_calls_subprocess_with_utf8_env(mocker):
    fake_run = mocker.patch("scripts.backfill_run.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
    row = {"encoded": "C--x", "wing": "x", "transcripts": 1, "include": True}
    result = run_one_row(row, projects_dir=Path("/fake"))
    assert result is True
    args, kwargs = fake_run.call_args
    env = kwargs["env"]
    assert env["PYTHONIOENCODING"] == "utf-8"


def test_run_one_row_returns_false_on_subprocess_failure(mocker):
    fake_run = mocker.patch("scripts.backfill_run.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom")
    row = {"encoded": "C--x", "wing": "x", "transcripts": 1, "include": True}
    assert run_one_row(row, projects_dir=Path("/fake")) is False


def test_run_plan_skips_excluded_rows(mocker, tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        "- encoded: C--a\n  wing: a\n  transcripts: 1\n  include: true\n"
        "- encoded: C--b\n  wing: b\n  transcripts: 1\n  include: false\n"
    )
    spy = mocker.patch("scripts.backfill_run.run_one_row", return_value=True)
    rc = run_plan(plan, projects_dir=tmp_path)
    assert rc == 0
    assert spy.call_count == 1  # only the included row
    assert spy.call_args[0][0]["wing"] == "a"


def test_run_plan_returns_nonzero_when_any_row_fails(mocker, tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text("- encoded: C--a\n  wing: a\n  transcripts: 1\n  include: true\n")
    mocker.patch("scripts.backfill_run.run_one_row", return_value=False)
    assert run_plan(plan, projects_dir=tmp_path) != 0
