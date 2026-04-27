import os
from pathlib import Path
from scripts._common import (
    PALACE_PATH,
    CLAUDE_PROJECTS_DIR,
    derive_wing_from_cwd,
    sanitize_wing_name,
    mempalace_env,
)


def test_palace_path_is_user_home_mempalace():
    assert PALACE_PATH == Path.home() / ".mempalace" / "palace"


def test_claude_projects_dir_is_user_claude_projects():
    assert CLAUDE_PROJECTS_DIR == Path.home() / ".claude" / "projects"


def test_derive_wing_from_cwd_returns_basename(tmp_path):
    project = tmp_path / "my-project-name"
    project.mkdir()
    assert derive_wing_from_cwd(str(project)) == "my-project-name"


def test_derive_wing_lowercases_and_keeps_hyphens(tmp_path):
    project = tmp_path / "Cash-Flow-Management"
    project.mkdir()
    assert derive_wing_from_cwd(str(project)) == "cash-flow-management"


def test_sanitize_wing_name_strips_unsafe_chars():
    assert sanitize_wing_name("foo bar/baz") == "foo-bar-baz"
    assert sanitize_wing_name("foo-/bar") == "foo-bar"   # actually exercises the -+ collapse
    assert sanitize_wing_name("FOO_BAR") == "foo_bar"


def test_sanitize_wing_name_raises_on_empty_result():
    import pytest
    with pytest.raises(ValueError):
        sanitize_wing_name("")
    with pytest.raises(ValueError):
        sanitize_wing_name("---")
    with pytest.raises(ValueError):
        sanitize_wing_name("///")


def test_mempalace_env_sets_utf8():
    env = mempalace_env()
    assert env["PYTHONIOENCODING"] == "utf-8"
    # Verify it's a copy of os.environ (not the same dict) and inherited keys
    assert env is not os.environ
    assert len(env) > 1
