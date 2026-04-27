# MemPalace Memory Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire MemPalace as the OS-wide conversation-memory layer for Claude Code, partitioned per project, with one-time backfill of `~/.claude/projects/` JSONL transcripts and going-forward auto-save via hooks.

**Architecture:** Single OS-wide palace at `~/.mempalace/palace`, wing-per-project (folder basename). Three pipelines: backfill (one-off scripts), save (Stop+PreCompact hooks coercing Claude to call `mempalace_add_drawer` MCP tool), retrieve (MCP server + SessionStart wake-up wrapper + `/recall` slash command). Cleanup via two helper scripts (archive renames wing prefix, hard-delete iterates `delete_drawer`).

**Tech Stack:** Python 3.13 (Windows), `mempalace` 3.3.0 (already installed), `pyyaml` (must install), `pytest` + `pytest-mock` for tests, Claude Code hooks/MCP infrastructure.

**Working directory for all tasks:** `C:/Users/Admin/Desktop/AD-KD/obsidian-llm-palace`. Reference spec: `docs/superpowers/specs/2026-04-27-mempalace-memory-retrieval-design.md`.

**Critical Windows preflight (one-time, before any task):**
```bash
setx PYTHONIOENCODING utf-8
```
Open a fresh terminal afterward so the env var is loaded. Every subprocess call to `mempalace` in this plan also passes `PYTHONIOENCODING=utf-8` defensively in the env dict.

---

## Task 1: Project scaffolding + shared helpers + dev dependencies

**Goal:** Set up `scripts/`, `tests/`, install `pyyaml` + `pytest` + `pytest-mock`, write `_common.py` with the constants and helpers every later script will share.

**Files:**
- Create: `scripts/__init__.py` (empty)
- Create: `scripts/_common.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Create: `pyproject.toml`
- Create: `.gitignore` additions for `__pycache__/`, `.pytest_cache/`, `*.pyc`

- [ ] **Step 1: Install dev dependencies**

```bash
pip install pyyaml pytest pytest-mock
```

Expected: successful install, no errors. Verify with:
```bash
python -c "import yaml, pytest, pytest_mock; print('ok')"
```
Expected output: `ok`

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "obsidian-llm-palace-tools"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["pyyaml>=6.0", "mempalace>=3.3.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-mock>=3.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 3: Append to `.gitignore`**

Open `.gitignore`, append:
```
__pycache__/
*.pyc
.pytest_cache/
backfill-plan.yaml
```

(`backfill-plan.yaml` is generated and contains private project paths — never commit it.)

- [ ] **Step 4: Write the failing test for `_common.py`**

Create `tests/conftest.py` first (empty placeholder for now):
```python
# Pytest configuration. Add fixtures here as tests need them.
```

Create `tests/test_common.py`:
```python
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
    assert sanitize_wing_name("foo  bar") == "foo-bar"
    assert sanitize_wing_name("FOO_BAR") == "foo_bar"


def test_mempalace_env_sets_utf8():
    env = mempalace_env()
    assert env["PYTHONIOENCODING"] == "utf-8"
    # Inherits PATH so subprocess can find python
    assert "PATH" in env or "Path" in env
```

- [ ] **Step 5: Run tests, expect failure**

```bash
pytest tests/test_common.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts._common'` or similar.

- [ ] **Step 6: Implement `scripts/_common.py`**

Create `scripts/__init__.py` as empty file.

Create `scripts/_common.py`:
```python
"""Shared constants and helpers for MemPalace tooling scripts."""
import os
import re
from pathlib import Path

PALACE_PATH = Path.home() / ".mempalace" / "palace"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def derive_wing_from_cwd(cwd: str) -> str:
    """Wing name = lowercased basename of the project directory."""
    return Path(cwd).name.lower()


def sanitize_wing_name(name: str) -> str:
    """Coerce a string into a valid wing name: lowercase, hyphens for unsafe chars."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9_-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name


def mempalace_env() -> dict:
    """Subprocess env that won't crash on Windows cp1252."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env
```

- [ ] **Step 7: Run tests, expect pass**

```bash
pytest tests/test_common.py -v
```
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add scripts/__init__.py scripts/_common.py tests/__init__.py tests/conftest.py tests/test_common.py pyproject.toml .gitignore
git commit -m "scaffold: scripts/_common helpers + tests + pyproject"
```

---

## Task 2: One-time palace initialization (verification-only)

**Goal:** Run `mempalace init` to create the palace at `~/.mempalace/palace`. No code, no test — just verification before later tasks depend on the palace existing.

- [ ] **Step 1: Confirm no palace exists yet**

```bash
PYTHONIOENCODING=utf-8 python -m mempalace status
```
Expected: either an error like `palace not found` OR a status with 0 wings. If it already shows wings, **stop** and ask the user — there's pre-existing palace data we shouldn't overwrite.

- [ ] **Step 2: Run init**

```bash
PYTHONIOENCODING=utf-8 python -m mempalace init ~/
```
Expected: a message that the palace was created at `~/.mempalace/palace`. Some "rooms" may be auto-detected from `~/` subdirs — that's fine, they're metadata-only.

- [ ] **Step 3: Verify palace exists on disk**

```bash
ls -la ~/.mempalace/
```
Expected: a `palace` directory and a `config.json` file. The `palace/` dir contains chroma + sqlite files.

- [ ] **Step 4: Verify status reports zero drawers**

```bash
PYTHONIOENCODING=utf-8 python -m mempalace status
```
Expected: status output shows palace path = `~/.mempalace/palace` and 0 drawers. **No commit** — this task changes nothing in the repo.

---

## Task 3: Backfill plan generator (`backfill_plan.py`)

**Goal:** TDD a script that walks `~/.claude/projects/`, decodes each encoded folder name into a wing-name suggestion, counts JSONL transcripts, and writes `backfill-plan.yaml` for human review.

**Files:**
- Create: `scripts/backfill_plan.py`
- Create: `tests/test_backfill_plan.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_backfill_plan.py`:
```python
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


def test_decode_lowercases_pascal_case():
    assert decode_wing_from_encoded("C--Users-Admin-Desktop-PrimeAI-Joey-Munoz") == "joey-munoz"


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
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/test_backfill_plan.py -v
```
Expected: import error — `scripts.backfill_plan` not found.

- [ ] **Step 3: Implement `scripts/backfill_plan.py`**

```python
"""Generate backfill-plan.yaml from ~/.claude/projects/ for human review."""
import sys
from pathlib import Path
from typing import List, Dict
import yaml

from scripts._common import CLAUDE_PROJECTS_DIR, sanitize_wing_name


# Encoded folder prefixes that are almost certainly accidental parent-dir sessions
NOISE_PATTERNS = {
    "C--Users-Admin",
    "C--Users-Admin-Desktop",
    "C--Users-Admin-Desktop-AD-KD",  # parent-of-projects, not a project
}


def decode_wing_from_encoded(encoded: str) -> str:
    """Best-guess wing name from Claude Code's encoded folder name.

    Claude Code encodes `C:\\Users\\Admin\\Desktop\\foo` as
    `C--Users-Admin-Desktop-foo`. Project names with hyphens (AD-KD) are
    ambiguous to reverse — we take everything after `Desktop-` (or after the
    last well-known prefix) and lowercase it. The user is expected to review
    the generated YAML and fix any wing name they don't like.
    """
    s = encoded
    # Strip drive prefix
    if s.startswith("C--Users-Admin-"):
        s = s[len("C--Users-Admin-"):]
    elif s.startswith("C--Users-Admin"):
        s = s[len("C--Users-Admin"):]
    # Strip common parent dirs
    for prefix in ("Desktop-", "robotics-ai-thinking-", "Personal-Projects-", "PrimeAI-", "AD-KD-", "Claude-tools-"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return sanitize_wing_name(s) or "unnamed"


def is_likely_noise(encoded: str) -> bool:
    """True for bare parent-dir entries that shouldn't be ingested."""
    return encoded in NOISE_PATTERNS


def scan_projects(projects_dir: Path) -> List[Dict]:
    """Walk projects_dir and return one row per subdirectory."""
    rows = []
    for child in sorted(projects_dir.iterdir()):
        if not child.is_dir():
            continue
        encoded = child.name
        transcripts = len(list(child.glob("*.jsonl")))
        rows.append({
            "encoded": encoded,
            "wing": decode_wing_from_encoded(encoded),
            "transcripts": transcripts,
            "include": not is_likely_noise(encoded),
        })
    return rows


def write_plan(rows: List[Dict], out_path: Path) -> None:
    """Write rows to YAML in a stable order."""
    out_path.write_text(yaml.safe_dump(rows, sort_keys=False))


def main() -> int:
    if not CLAUDE_PROJECTS_DIR.exists():
        print(f"ERROR: {CLAUDE_PROJECTS_DIR} does not exist.", file=sys.stderr)
        return 1
    rows = scan_projects(CLAUDE_PROJECTS_DIR)
    out = Path(__file__).parent.parent / "backfill-plan.yaml"
    write_plan(rows, out)
    print(f"Wrote {len(rows)} rows to {out}")
    print("Review and edit, then run scripts/backfill_run.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/test_backfill_plan.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Run the script for real to generate the actual YAML**

```bash
python -m scripts.backfill_plan
```
Expected: `Wrote 19 rows to .../backfill-plan.yaml`. Open `backfill-plan.yaml` and review — confirm wing names look sensible, decide which `include: true/false` flags to flip (especially PrimeAI client work). **Do not edit the YAML to remove rows; flip `include` flags only.**

- [ ] **Step 6: Commit**

```bash
git add scripts/backfill_plan.py tests/test_backfill_plan.py
git commit -m "feat: backfill plan generator for ~/.claude/projects"
```

(The generated `backfill-plan.yaml` is already gitignored — do not commit it.)

---

## Task 4: Backfill executor (`backfill_run.py`)

**Goal:** TDD a script that reads `backfill-plan.yaml` and runs `mempalace mine ... --mode convos --wing <name>` per included row, with `PYTHONIOENCODING=utf-8` env. Logs progress, skips excluded rows, exits non-zero if any row fails.

**Files:**
- Create: `scripts/backfill_run.py`
- Create: `tests/test_backfill_run.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_backfill_run.py`:
```python
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
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/test_backfill_run.py -v
```
Expected: import error.

- [ ] **Step 3: Implement `scripts/backfill_run.py`**

```python
"""Execute backfill-plan.yaml against `mempalace mine`."""
import subprocess
import sys
from pathlib import Path
from typing import Dict, List
import yaml

from scripts._common import CLAUDE_PROJECTS_DIR, mempalace_env


def build_mine_command(encoded_dir: Path, wing: str) -> List[str]:
    return [
        sys.executable, "-m", "mempalace", "mine",
        str(encoded_dir),
        "--mode", "convos",
        "--wing", wing,
    ]


def run_one_row(row: Dict, projects_dir: Path) -> bool:
    """Returns True on success, False on failure."""
    encoded_dir = projects_dir / row["encoded"]
    cmd = build_mine_command(encoded_dir, row["wing"])
    print(f"[mine] wing={row['wing']!r} transcripts={row['transcripts']} dir={encoded_dir}")
    result = subprocess.run(cmd, env=mempalace_env(), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAIL (rc={result.returncode}): {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"  OK: {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else 'mined'}")
    return True


def run_plan(plan_path: Path, projects_dir: Path) -> int:
    rows = yaml.safe_load(plan_path.read_text())
    failures = 0
    for row in rows:
        if not row.get("include", False):
            print(f"[skip] {row['encoded']}")
            continue
        if not run_one_row(row, projects_dir):
            failures += 1
    if failures:
        print(f"DONE with {failures} failure(s)", file=sys.stderr)
        return 1
    print("DONE — all included rows mined successfully")
    return 0


def main() -> int:
    plan_path = Path(__file__).parent.parent / "backfill-plan.yaml"
    if not plan_path.exists():
        print(f"ERROR: {plan_path} not found. Run scripts/backfill_plan.py first.", file=sys.stderr)
        return 1
    return run_plan(plan_path, CLAUDE_PROJECTS_DIR)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/test_backfill_run.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/backfill_run.py tests/test_backfill_run.py
git commit -m "feat: backfill executor calls mempalace mine per included row"
```

---

## Task 5: Run the actual backfill (verification-only)

**Goal:** Execute `backfill_run.py` against the reviewed `backfill-plan.yaml`, ingesting all included projects' JSONL transcripts into the palace. Single one-shot run.

- [ ] **Step 1: Re-verify the plan before executing**

```bash
cat backfill-plan.yaml | head -40
```
Expected: see the rows you reviewed in Task 3 step 5. **If you haven't reviewed and adjusted `include` flags yet, stop and do that now.**

- [ ] **Step 2: Run the backfill**

```bash
python -m scripts.backfill_run
```
Expected: a series of `[mine] wing=...` lines, each followed by `OK: ...`. May take several minutes for ~19 wings depending on transcript volume. Final line: `DONE — all included rows mined successfully`.

- [ ] **Step 3: Verify drawer count grew**

```bash
PYTHONIOENCODING=utf-8 python -m mempalace status
```
Expected: status now shows N wings (where N = number of `include: true` rows in your plan), each with at least one drawer.

- [ ] **Step 4: Smoke test a search**

Pick a wing you know contains a known phrase (e.g., `betaflight-sitl-msp-comms`):
```bash
PYTHONIOENCODING=utf-8 python -m mempalace search "MSP" --wing betaflight-sitl-msp-comms --limit 3
```
Expected: at least one hit with content from a past Claude Code session about MSP. **No commit** — this task changes only `~/.mempalace/`, which is outside the repo.

---

## Task 6: Register MemPalace MCP server (verification-only)

**Goal:** Make MemPalace's MCP tools available in every Claude Code session by registering it user-globally.

- [ ] **Step 1: Find your Python interpreter path**

```bash
python -c "import sys; print(sys.executable)"
```
Expected: an absolute path like `C:\Python313\python.exe`. Note this — you'll pass it to `claude mcp add`.

- [ ] **Step 2: Register the MCP server**

Use the path from step 1 (replace `<PYTHON_PATH>` with the actual path):
```bash
claude mcp add --scope user mempalace -- "<PYTHON_PATH>" -m mempalace.mcp_server
```
Expected: success message like `Added MCP server "mempalace"`.

- [ ] **Step 3: Verify registration**

```bash
claude mcp list
```
Expected: `mempalace` appears alongside the existing Google services. Status will likely be `unknown` or `connecting` until a Claude session actually loads it. **No commit** — this changes only Claude Code user config.

---

## Task 7: SessionStart hook wrapper (`session_start_hook.py` + skip-prefixes file)

**Goal:** TDD a wrapper script that the SessionStart hook will invoke. Derives wing from `cwd`, checks a skip-prefix file, runs `mempalace wake-up --wing <wing>` (with utf-8 env), passes its stdout through.

**Files:**
- Create: `scripts/session_start_hook.py`
- Create: `scripts/wake_up_skip_prefixes.txt`
- Create: `tests/test_session_start_hook.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_session_start_hook.py`:
```python
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


def test_main_skips_when_wing_matches_prefix(mocker, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path / "_archive_dead" if False else tmp_path)
    # simulate cwd basename = "_archive_dead"
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
    mocker.patch("scripts.session_start_hook.invoke_wake_up", return_value="WAKE_UP_PAYLOAD")
    rc = main(skip_file=skip_file)
    assert rc == 0
    captured = capsys.readouterr()
    assert "WAKE_UP_PAYLOAD" in captured.out
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/test_session_start_hook.py -v
```
Expected: import error.

- [ ] **Step 3: Create the skip-prefixes file**

Create `scripts/wake_up_skip_prefixes.txt` with this content:
```
# One prefix per line. Wings whose names start with any of these will not
# trigger an auto wake-up at session start. Used by archive_wing.py.
_archive_
```

- [ ] **Step 4: Implement `scripts/session_start_hook.py`**

```python
"""SessionStart hook wrapper: emit MemPalace wake-up for the current wing.

Invoked by Claude Code's SessionStart hook. Stdout is injected into Claude's
initial context. Stderr/exit code are ignored by the harness.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List

from scripts._common import derive_wing_from_cwd, mempalace_env


DEFAULT_SKIP_FILE = Path(__file__).parent / "wake_up_skip_prefixes.txt"


def load_skip_prefixes(path: Path) -> List[str]:
    """Read prefixes; skip blank lines and comments."""
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def should_skip(wing: str, prefixes: List[str]) -> bool:
    return any(wing.startswith(p) for p in prefixes)


def invoke_wake_up(wing: str) -> str:
    """Call `mempalace wake-up --wing <wing>` and return its stdout. Empty on failure."""
    cmd = [sys.executable, "-m", "mempalace", "wake-up", "--wing", wing, "--format", "json"]
    result = subprocess.run(cmd, env=mempalace_env(), capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        # Fail open: no wake-up rather than a broken session start
        return ""
    return result.stdout


def main(skip_file: Path = DEFAULT_SKIP_FILE) -> int:
    wing = derive_wing_from_cwd(os.getcwd())
    prefixes = load_skip_prefixes(skip_file)
    if should_skip(wing, prefixes):
        return 0
    payload = invoke_wake_up(wing)
    if payload:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests, expect pass**

```bash
pytest tests/test_session_start_hook.py -v
```
Expected: 7 passed.

- [ ] **Step 6: Manual sanity check**

From the obsidian-llm-palace project root:
```bash
python -m scripts.session_start_hook
```
Expected: either some JSON wake-up content (if the `obsidian-llm-palace` wing has drawers from the backfill) or empty output (if no drawers yet under that wing). Either is fine — what matters is it doesn't crash.

- [ ] **Step 7: Commit**

```bash
git add scripts/session_start_hook.py scripts/wake_up_skip_prefixes.txt tests/test_session_start_hook.py
git commit -m "feat: SessionStart hook wrapper with skip-prefix support"
```

---

## Task 8: Wire hooks in user-global `~/.claude/settings.json`

**Goal:** Add Stop, PreCompact, and SessionStart hooks to the user-global settings file. Single config edit, then verify by tailing logs.

- [ ] **Step 1: Locate or create the settings file**

```bash
ls -la ~/.claude/settings.json 2>&1
```
If it exists, **read it first** so you know what's there:
```bash
cat ~/.claude/settings.json
```
If it doesn't exist, that's fine — we'll create it.

- [ ] **Step 2: Determine the absolute path to `session_start_hook.py`**

```bash
python -c "from pathlib import Path; print(Path.home() / 'Desktop' / 'AD-KD' / 'obsidian-llm-palace' / 'scripts' / 'session_start_hook.py')"
```
Expected: the absolute path. Note this for the next step.

- [ ] **Step 3: Edit `~/.claude/settings.json`**

If the file already has content, **merge these hooks into the existing structure** — do not overwrite other settings. If the file is empty or missing, write this entire object.

The three hook entries to add (use the absolute path from step 2 in the SessionStart command):

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python -m mempalace hook run --hook stop --harness claude-code",
            "timeout": 30
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m mempalace hook run --hook precompact --harness claude-code",
            "timeout": 30
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python <ABSOLUTE_PATH_FROM_STEP_2>",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

If `settings.json` already had a `hooks` key, merge the three arrays into the existing one rather than replacing it.

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open(str(__import__('pathlib').Path.home() / '.claude' / 'settings.json'))); print('valid')"
```
Expected: `valid`.

- [ ] **Step 5: Smoke-test by starting a fresh Claude Code session**

Open a new terminal in `obsidian-llm-palace`, start `claude`. Watch for: no hook errors at startup, Claude opens normally. The SessionStart wake-up output (if any) becomes part of Claude's initial context — visible only inside the session, not as terminal output. **No commit** — settings.json is outside the repo.

---

## Task 9: `/recall` slash command

**Goal:** Create a user-global slash command that runs `mempalace search` against the user's argument and surfaces hits inline.

**Files:**
- Create: `~/.claude/commands/recall.md`

- [ ] **Step 1: Create the commands directory if missing**

```bash
mkdir -p ~/.claude/commands
```

- [ ] **Step 2: Write the slash command**

Create `~/.claude/commands/recall.md`:
```markdown
---
description: Search MemPalace for past conversations across all wings
---

Run this command to search MemPalace for the user's query:

```bash
PYTHONIOENCODING=utf-8 python -m mempalace search "$ARGUMENTS" --limit 5
```

Then read the printed drawer contents and synthesize an answer for the user, citing each drawer's wing/room and a short excerpt. If no hits, say so.
```

- [ ] **Step 3: Smoke test in a fresh Claude Code session**

In any project's Claude Code session, type:
```
/recall MSP serial protocol
```
Expected: Claude runs the bash command, prints hits (assuming the backfill picked up MSP-related conversations), and synthesizes a summary. **No commit** — this lives in `~/.claude/`, outside the repo.

---

## Task 10: Add `## MemPalace` section to two CLAUDE.md files

**Goal:** Pin the wing name for the two highest-traffic projects so Claude doesn't drift on naming. Other projects can be opted in later by repeating this pattern.

**Files:**
- Modify: `C:/Users/Admin/Desktop/AD-KD/obsidian-llm-palace/obsidian-llm-palace/CLAUDE.md` (the inner vault folder, not the repo root)
- Modify: `C:/Users/Admin/Desktop/AD-KD/betaflight-sitl-msp-comms/CLAUDE.md` (create if missing)

- [ ] **Step 1: Append to obsidian-llm-palace CLAUDE.md**

Open `C:/Users/Admin/Desktop/AD-KD/obsidian-llm-palace/obsidian-llm-palace/CLAUDE.md`. Append at the end:

```markdown

## MemPalace

Wing: obsidian-llm-palace
```

- [ ] **Step 2: Verify or create betaflight-sitl-msp-comms CLAUDE.md**

```bash
ls "C:/Users/Admin/Desktop/AD-KD/betaflight-sitl-msp-comms/CLAUDE.md" 2>&1 || echo "missing"
```

If missing, create it with this content:
```markdown
# Betaflight SITL MSP Comms

## MemPalace

Wing: betaflight-sitl-msp-comms
```

If it exists, append the same `## MemPalace` section as Step 1 (with `Wing: betaflight-sitl-msp-comms`).

- [ ] **Step 3: Commit obsidian-llm-palace CLAUDE.md change**

```bash
cd C:/Users/Admin/Desktop/AD-KD/obsidian-llm-palace
git add obsidian-llm-palace/CLAUDE.md
git commit -m "docs: declare MemPalace wing for obsidian-llm-palace"
```

- [ ] **Step 4: Commit betaflight-sitl-msp-comms CLAUDE.md change**

```bash
cd C:/Users/Admin/Desktop/AD-KD/betaflight-sitl-msp-comms
git add CLAUDE.md
git commit -m "docs: declare MemPalace wing for betaflight-sitl-msp-comms"
cd C:/Users/Admin/Desktop/AD-KD/obsidian-llm-palace
```

(Each repo gets its own commit because they're separate gits.)

---

## Task 11: `archive_wing.py` (Pattern 1 cleanup)

**Goal:** TDD a script that renames every drawer's wing from `<wing>` to `_archive_<wing>`. After running, the `_archive_` prefix in `wake_up_skip_prefixes.txt` ensures wake-up no longer auto-loads that wing — but `mempalace search --wing _archive_<wing>` still works for explicit recall.

**Files:**
- Create: `scripts/archive_wing.py`
- Create: `tests/test_archive_wing.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_archive_wing.py`:
```python
import json
import subprocess
import pytest
from scripts.archive_wing import (
    list_drawer_ids_for_wing,
    archive_wing,
)


def test_list_drawer_ids_parses_json_output(mocker):
    fake_run = mocker.patch("scripts.archive_wing.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout=json.dumps([{"id": "drw-1"}, {"id": "drw-2"}]),
        stderr="",
    )
    ids = list_drawer_ids_for_wing("foo")
    assert ids == ["drw-1", "drw-2"]


def test_list_drawer_ids_empty_when_wing_missing(mocker):
    fake_run = mocker.patch("scripts.archive_wing.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
    assert list_drawer_ids_for_wing("nope") == []


def test_archive_wing_calls_update_drawer_per_id(mocker):
    mocker.patch(
        "scripts.archive_wing.list_drawer_ids_for_wing",
        return_value=["drw-1", "drw-2"],
    )
    fake_run = mocker.patch("scripts.archive_wing.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
    rc = archive_wing("foo")
    assert rc == 0
    # Two update_drawer calls, both with the new wing name
    assert fake_run.call_count == 2
    for call in fake_run.call_args_list:
        cmd = call[0][0]
        assert "update-drawer" in cmd or "update_drawer" in cmd
        assert "_archive_foo" in cmd


def test_archive_wing_no_op_when_wing_empty(mocker, capsys):
    mocker.patch("scripts.archive_wing.list_drawer_ids_for_wing", return_value=[])
    fake_run = mocker.patch("scripts.archive_wing.subprocess.run")
    rc = archive_wing("ghost")
    assert rc == 0
    fake_run.assert_not_called()
    out = capsys.readouterr().out
    assert "no drawers" in out.lower() or "0 drawers" in out
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/test_archive_wing.py -v
```
Expected: import error.

- [ ] **Step 3: Verify the actual `mempalace` CLI surface for drawer listing/updating**

Before implementing, confirm the CLI verbs because we mock these in tests but they need to be real:
```bash
PYTHONIOENCODING=utf-8 python -m mempalace --help 2>&1 | grep -iE "drawer|update"
```

If `mempalace` does not expose `list-drawers` / `update-drawer` as CLI subcommands (they may only be MCP tools), fall back to direct Python API. Inspect:
```bash
PYTHONIOENCODING=utf-8 python -c "from mempalace import miner; print([x for x in dir(miner) if not x.startswith('_')])"
```

**If the CLI lacks these commands, implement using the Python API directly** (import from `mempalace`) instead of `subprocess.run`. Update the tests in step 1 to mock the Python-API call site instead. This is a fork-in-the-road — do whichever the actual `mempalace` 3.3.0 surface supports. Both paths produce the same result.

- [ ] **Step 4: Implement `scripts/archive_wing.py`**

The implementation below uses subprocess for consistency with other scripts. **If step 3 revealed the CLI doesn't have these subcommands, replace `subprocess.run` calls with direct Python imports from `mempalace.mcp_server` (e.g., `tool_list_drawers`, `tool_update_drawer`) — those are the canonical entry points.**

```python
"""Archive a wing: rename it to _archive_<wing> so wake-up skips it."""
import argparse
import json
import subprocess
import sys
from typing import List

from scripts._common import mempalace_env


def list_drawer_ids_for_wing(wing: str) -> List[str]:
    """Return drawer IDs filed under the given wing."""
    cmd = [
        sys.executable, "-m", "mempalace", "list-drawers",
        "--wing", wing, "--format", "json", "--limit", "10000",
    ]
    result = subprocess.run(cmd, env=mempalace_env(), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"list-drawers failed: {result.stderr}", file=sys.stderr)
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [d["id"] for d in data if "id" in d]


def archive_wing(wing: str) -> int:
    """Move all drawers from <wing> to _archive_<wing>."""
    new_wing = f"_archive_{wing}"
    ids = list_drawer_ids_for_wing(wing)
    if not ids:
        print(f"No drawers found under wing {wing!r} — nothing to archive.")
        return 0
    print(f"Archiving {len(ids)} drawer(s): {wing} -> {new_wing}")
    for drawer_id in ids:
        cmd = [
            sys.executable, "-m", "mempalace", "update-drawer",
            "--id", drawer_id, "--wing", new_wing,
        ]
        result = subprocess.run(cmd, env=mempalace_env(), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAIL drawer {drawer_id}: {result.stderr}", file=sys.stderr)
            return 1
    print(f"Done. Future sessions will skip wake-up for {new_wing} (prefix _archive_).")
    print(f"Search remains available: mempalace search 'X' --wing {new_wing}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Archive a MemPalace wing.")
    p.add_argument("wing", help="Wing name to archive (e.g., old-project)")
    args = p.parse_args()
    return archive_wing(args.wing)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests, expect pass**

```bash
pytest tests/test_archive_wing.py -v
```
Expected: 4 passed. **If tests fail because the CLI surface differed in step 3, the tests need to be updated to reflect the Python-API path.**

- [ ] **Step 6: Commit**

```bash
git add scripts/archive_wing.py tests/test_archive_wing.py
git commit -m "feat: archive_wing script renames drawers to _archive_<wing>"
```

---

## Task 12: `delete_wing.py` (Pattern 2 cleanup, with confirmation)

**Goal:** TDD a script that hard-deletes every drawer in a wing, plus tunnels involving that wing. Requires interactive confirmation unless `--yes` is passed.

**Files:**
- Create: `scripts/delete_wing.py`
- Create: `tests/test_delete_wing.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_delete_wing.py`:
```python
import json
import subprocess
import pytest
from scripts.delete_wing import (
    delete_wing,
    list_tunnels_for_wing,
)


def test_delete_wing_iterates_delete_drawer(mocker):
    mocker.patch("scripts.delete_wing.list_drawer_ids_for_wing", return_value=["d1", "d2", "d3"])
    mocker.patch("scripts.delete_wing.list_tunnels_for_wing", return_value=[])
    fake_run = mocker.patch("scripts.delete_wing.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    rc = delete_wing("doomed", confirmed=True)
    assert rc == 0
    # 3 delete-drawer calls
    delete_calls = [c for c in fake_run.call_args_list if "delete-drawer" in c[0][0]]
    assert len(delete_calls) == 3


def test_delete_wing_also_deletes_tunnels(mocker):
    mocker.patch("scripts.delete_wing.list_drawer_ids_for_wing", return_value=["d1"])
    mocker.patch("scripts.delete_wing.list_tunnels_for_wing", return_value=["tun-A"])
    fake_run = mocker.patch("scripts.delete_wing.subprocess.run")
    fake_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    rc = delete_wing("doomed", confirmed=True)
    assert rc == 0
    cmds = [c[0][0] for c in fake_run.call_args_list]
    assert any("delete-tunnel" in cmd for cmd in cmds)


def test_delete_wing_aborts_when_not_confirmed(mocker, capsys):
    mocker.patch("scripts.delete_wing.list_drawer_ids_for_wing", return_value=["d1"])
    fake_run = mocker.patch("scripts.delete_wing.subprocess.run")
    rc = delete_wing("doomed", confirmed=False)
    assert rc != 0
    fake_run.assert_not_called()
    assert "abort" in capsys.readouterr().out.lower()


def test_delete_wing_no_op_when_empty(mocker, capsys):
    mocker.patch("scripts.delete_wing.list_drawer_ids_for_wing", return_value=[])
    mocker.patch("scripts.delete_wing.list_tunnels_for_wing", return_value=[])
    fake_run = mocker.patch("scripts.delete_wing.subprocess.run")
    rc = delete_wing("ghost", confirmed=True)
    assert rc == 0
    fake_run.assert_not_called()


def test_list_tunnels_parses_json(mocker):
    mocker.patch(
        "scripts.delete_wing.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([{"id": "t1"}, {"id": "t2"}]),
            stderr="",
        ),
    )
    assert list_tunnels_for_wing("foo") == ["t1", "t2"]
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/test_delete_wing.py -v
```
Expected: import error.

- [ ] **Step 3: Implement `scripts/delete_wing.py`**

Same fork-in-the-road caveat as Task 11 step 3 — if `mempalace` CLI lacks `delete-drawer` / `list-tunnels` / `delete-tunnel` subcommands, switch to Python imports from `mempalace.mcp_server` and update tests accordingly.

```python
"""Hard-delete a wing: irreversibly remove all drawers and tunnels under it."""
import argparse
import json
import subprocess
import sys
from typing import List

from scripts._common import mempalace_env
from scripts.archive_wing import list_drawer_ids_for_wing


def list_tunnels_for_wing(wing: str) -> List[str]:
    cmd = [
        sys.executable, "-m", "mempalace", "list-tunnels",
        "--wing", wing, "--format", "json",
    ]
    result = subprocess.run(cmd, env=mempalace_env(), capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [t["id"] for t in data if "id" in t]


def delete_wing(wing: str, confirmed: bool) -> int:
    if not confirmed:
        print(f"Aborting: pass --yes (or answer 'y') to actually delete wing {wing!r}.")
        return 2

    drawer_ids = list_drawer_ids_for_wing(wing)
    tunnel_ids = list_tunnels_for_wing(wing)

    if not drawer_ids and not tunnel_ids:
        print(f"Wing {wing!r} has no drawers or tunnels — nothing to delete.")
        return 0

    print(f"Deleting {len(drawer_ids)} drawer(s) and {len(tunnel_ids)} tunnel(s) from {wing!r}...")

    for drawer_id in drawer_ids:
        cmd = [sys.executable, "-m", "mempalace", "delete-drawer", "--id", drawer_id]
        result = subprocess.run(cmd, env=mempalace_env(), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAIL drawer {drawer_id}: {result.stderr}", file=sys.stderr)
            return 1

    for tunnel_id in tunnel_ids:
        cmd = [sys.executable, "-m", "mempalace", "delete-tunnel", "--id", tunnel_id]
        result = subprocess.run(cmd, env=mempalace_env(), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAIL tunnel {tunnel_id}: {result.stderr}", file=sys.stderr)
            return 1

    print(f"Wing {wing!r} deleted. Verify with: mempalace status")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Hard-delete a MemPalace wing. Irreversible.")
    p.add_argument("wing", help="Wing name to delete")
    p.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt")
    args = p.parse_args()

    confirmed = args.yes
    if not confirmed:
        ans = input(f"Hard-delete wing {args.wing!r}? This is IRREVERSIBLE. [y/N]: ")
        confirmed = ans.strip().lower() == "y"

    return delete_wing(args.wing, confirmed=confirmed)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/test_delete_wing.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/delete_wing.py tests/test_delete_wing.py
git commit -m "feat: delete_wing script for hard cleanup with confirmation"
```

---

## Task 13: End-to-end verification (Section 9 of spec)

**Goal:** Run the spec's verification checklist top-to-bottom and confirm the wired system actually works.

- [ ] **Step 1: Install verification**

```bash
PYTHONIOENCODING=utf-8 python -m mempalace status
```
Expected: palace path printed, wing count > 0 (because of Task 5 backfill), no errors.

- [ ] **Step 2: MCP registration check**

```bash
claude mcp list
```
Expected: `mempalace` listed.

- [ ] **Step 3: Save hook smoke test**

Open a fresh Claude Code session in `betaflight-sitl-msp-comms`. Have a short conversation (~16 turns) about a unique phrase like "**plan-13-canary-msp-frame**". End the session normally.

Then verify:
```bash
PYTHONIOENCODING=utf-8 python -m mempalace search "plan-13-canary-msp-frame" --wing betaflight-sitl-msp-comms
```
Expected: at least one hit. **If zero hits**: the Stop hook didn't fire or Claude didn't actually save. Check `~/.mempalace/hook_state/` for activity, re-read `~/.claude/settings.json`, confirm `python -m mempalace` resolves on PATH.

- [ ] **Step 4: Wake-up hook smoke test**

Open another fresh Claude Code session in the same project. As the very first message, ask:
> "What did we discuss in the last session?"

Expected: Claude references the canary phrase or topic from the prior session without you telling it. **If it doesn't**: the SessionStart hook isn't injecting wake-up. Manually run `python -m scripts.session_start_hook` from that project root and confirm it produces output. Check timeout in `settings.json` (15s should be enough; bump if MemPalace is slow).

- [ ] **Step 5: `/recall` smoke test**

In any active Claude Code session:
```
/recall MSP serial protocol
```
Expected: Claude runs the command, prints hits, summarizes. If it says "command not found", recheck `~/.claude/commands/recall.md` exists.

- [ ] **Step 6: Cleanup-script smoke test (optional, low-risk)**

Pick the lowest-value backfilled wing (or create a throwaway one). First archive:
```bash
python -m scripts.archive_wing throwaway-wing
PYTHONIOENCODING=utf-8 python -m mempalace search "anything" --wing _archive_throwaway-wing
```
Expected: archive prints "Done", explicit search still returns hits.

Then hard-delete:
```bash
python -m scripts.delete_wing _archive_throwaway-wing --yes
PYTHONIOENCODING=utf-8 python -m mempalace search "anything" --wing _archive_throwaway-wing
```
Expected: zero hits after delete.

- [ ] **Step 7: Summary commit (no code, just plan completion marker)**

If you've kept any test fixtures or notes, commit them now. Otherwise this is a no-op. A final commit signal helps future-you know the implementation is complete:

```bash
# Only if there are unstaged changes from the smoke tests
git status
# Otherwise:
echo "Implementation complete; verified end-to-end."
```

---

## Spec coverage check (after all tasks done)

Confirm every spec section maps to at least one task:

| Spec § | Implemented in |
|---|---|
| §1 High-level architecture (palace location, wing convention) | Task 1 (`_common.py` constants), Task 2 (init) |
| §2 Backfill pipeline | Tasks 3, 4, 5 |
| §3 Save pipeline (Stop, PreCompact hooks) | Task 8 |
| §4.A MCP server | Task 6 |
| §4.B SessionStart wake-up | Tasks 7, 8 |
| §4.D `/recall` slash command | Task 9 |
| §5 Project → wing mapping (CLAUDE.md convention) | Task 10 |
| §6 Pattern 1 archive | Task 11 |
| §6 Pattern 2 hard delete | Task 12 |
| §7 Privacy posture | Tasks 1 (`.gitignore` for backfill-plan.yaml), 3 (review gate) |
| §8 Failure-mode matrix | Tasks 1 (utf8 env), 7 (fail-open in `invoke_wake_up`) |
| §9 Verification checklist | Task 13 |
| §10 Rollback | Documented in spec; no code needed |

If any cell is empty after execution, that's a gap — open a follow-up task.
