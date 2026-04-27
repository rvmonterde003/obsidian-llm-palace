import yaml
from pathlib import Path
from scripts.backfill_plan import (
    decode_wing_from_encoded,
    is_likely_noise,
    scan_projects,
    write_plan,
)


def test_decode_strips_drive_prefix():
    assert decode_wing_from_encoded("C--Users-Admin-Desktop-AD-KD-betaflight-sitl-msp-comms") == "betaflight-sitl-msp-comms"


def test_decode_nested_with_hyphens_uses_last_two_segments_when_unambiguous():
    # AD-KD itself is a project that contains hyphens — we don't try to be clever, just take last segment by hyphen
    # The real disambiguation is the human reviewing backfill-plan.yaml
    assert decode_wing_from_encoded("C--Users-Admin-Desktop-AD-KD") == "ad-kd"


def test_decode_strips_desktop_and_primeai_nested():
    assert decode_wing_from_encoded("C--Users-Admin-Desktop-PrimeAI-Joey-Munoz") == "joey-munoz"


def test_decode_bare_admin_does_not_crash():
    # C--Users-Admin strips to "" — must return 'unnamed', not raise
    assert decode_wing_from_encoded("C--Users-Admin") == "unnamed"


def test_decode_bare_without_desktop_prefix():
    assert decode_wing_from_encoded("C--Users-Admin-Claude-tools") == "claude-tools"
    assert decode_wing_from_encoded("C--Users-Admin-robotics-ai-thinking") == "robotics-ai-thinking"


def test_is_likely_noise_flags_bare_desktop():
    assert is_likely_noise("C--Users-Admin-Desktop") is True
    assert is_likely_noise("C--Users-Admin") is True
    assert is_likely_noise("C--Users-Admin-Desktop-AD-KD-betaflight-sitl-msp-comms") is False


def test_scan_projects_counts_jsonl(tmp_path):
    proj_dir = tmp_path / "C--Users-Admin-foo"
    proj_dir.mkdir()
    (proj_dir / "session1.jsonl").write_text("{}")
    (proj_dir / "session2.jsonl").write_text("{}")
    (proj_dir / "ignore.txt").write_text("x")
    rows = scan_projects(tmp_path)
    assert len(rows) == 1
    assert rows[0]["encoded"] == "C--Users-Admin-foo"
    assert rows[0]["transcripts"] == 2
    assert rows[0]["wing"] == "foo"
    assert rows[0]["include"] is True


def test_scan_projects_marks_noise_include_false(tmp_path):
    noise_dir = tmp_path / "C--Users-Admin-Desktop"
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
