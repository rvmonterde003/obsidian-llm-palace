"""SessionStart hook wrapper: emit MemPalace wake-up for the current wing.

Invoked by Claude Code's SessionStart hook. Stdout is injected into Claude's
initial context. Stderr/exit code are ignored by the harness.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._common import derive_wing_from_cwd, mempalace_env  # noqa: E402


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
    """Return True if wing starts with any of the given skip prefixes."""
    return any(wing.startswith(p) for p in prefixes)


def invoke_wake_up(wing: str) -> str:
    """Call `mempalace wake-up --wing <wing>` and return its stdout. Empty on any failure (fail-open)."""
    cmd = [sys.executable, "-m", "mempalace", "wake-up", "--wing", wing, "--format", "json"]
    try:
        result = subprocess.run(
            cmd, env=mempalace_env(),
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    if result.returncode != 0:
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
