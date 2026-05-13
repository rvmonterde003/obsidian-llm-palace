import yaml
from pathlib import Path
from scripts.backfill_plan import (
    decode_wing_from_encoded,
    is_likely_noise,
    scan_projects,
    write_plan,
)


def test_decode_strips_windows_user_prefix():
    assert decode_wing_from_encoded("C--Users-alice-Desktop-projects-widget-engine") == "widget-engine"


def test_decode_strips_macos_user_prefix():
    assert decode_wing_from_encoded("-Users-alice-Documents-widget-engine") == "widget-engine"


def test_decode_strips_linux_user_prefix():
    assert decode_wing_from_encoded("-home-alice-code-widget-engine") == "widget-engine"


def test_decode_handles_project_with_hyphens():
    # Project names with hyphens are reversed as-is after the prefix is stripped;
    # disambiguation is the human reviewing backfill-plan.yaml.
    assert decode_wing_from_encoded("C--Users-bob-Desktop-my-multi-hyphen-project") == "my-multi-hyphen-project"


def test_decode_bare_user_does_not_crash():
    # `C--Users-<name>` strips to "" — must return 'unnamed', not raise.
    assert decode_wing_from_encoded("C--Users-alice") == "unnamed"


def test_decode_without_parent_dir():
    assert decode_wing_from_encoded("C--Users-alice-claude-tools") == "claude-tools"


def test_is_likely_noise_flags_bare_parent_dirs():
    assert is_likely_noise("C--Users-alice-Desktop") is True
    assert is_likely_noise("C--Users-alice") is True
    assert is_likely_noise("-Users-alice-Documents") is True
    assert is_likely_noise("C--Users-alice-Desktop-projects-widget-engine") is False


def test_scan_projects_counts_jsonl(tmp_path):
    proj_dir = tmp_path / "C--Users-alice-foo"
    proj_dir.mkdir()
    (proj_dir / "session1.jsonl").write_text("{}")
    (proj_dir / "session2.jsonl").write_text("{}")
    (proj_dir / "ignore.txt").write_text("x")
    rows = scan_projects(tmp_path)
    assert len(rows) == 1
    assert rows[0]["encoded"] == "C--Users-alice-foo"
    assert rows[0]["transcripts"] == 2
    assert rows[0]["wing"] == "foo"
    assert rows[0]["include"] is True


def test_scan_projects_marks_noise_include_false(tmp_path):
    noise_dir = tmp_path / "C--Users-alice-Desktop"
    noise_dir.mkdir()
    (noise_dir / "session1.jsonl").write_text("{}")
    rows = scan_projects(tmp_path)
    assert rows[0]["include"] is False


def test_write_plan_emits_yaml_list(tmp_path):
    rows = [{"encoded": "x", "wing": "x", "transcripts": 1, "include": True}]
    out = tmp_path / "plan.yaml"
    write_plan(rows, out)
    parsed = yaml.safe_load(out.read_text())
    assert parsed == rows
