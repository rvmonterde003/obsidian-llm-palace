"""Generate backfill-plan.yaml from ~/.claude/projects/ for human review."""
import re
import sys
from pathlib import Path
from typing import List, Dict
import yaml

from scripts._common import CLAUDE_PROJECTS_DIR, sanitize_wing_name


# Encoded folder shapes that are almost certainly accidental parent-dir sessions.
# Built dynamically from the prefix matched by USER_PREFIX_RE so it works for
# any user/platform (we cannot list every "C--Users-<name>-Desktop" up front).
_NOISE_TRAILING_SEGMENTS = {"", "Desktop", "Documents", "Projects", "code", "workspace"}

# Matches the platform/user prefix Claude Code prepends to project folder names:
#   Windows: "C:\Users\<NAME>\..." -> "C--Users-<NAME>-..."
#   macOS:   "/Users/<NAME>/..."    -> "-Users-<NAME>-..."
#   Linux:   "/home/<NAME>/..."     -> "-home-<NAME>-..."
USER_PREFIX_RE = re.compile(
    r"^(?:[A-Z]--Users|-Users|-home)-[^-]+-?"
)

# Parent-directory segments commonly seen between $HOME and the actual project.
# These get stripped after USER_PREFIX_RE so the wing name is the project itself.
_COMMON_PARENT_SEGMENTS = ("Desktop", "Documents", "Projects", "projects", "code", "workspace", "dev", "src")


def _strip_user_prefix(encoded: str) -> str:
    """Remove the leading drive + Users/<name> prefix."""
    return USER_PREFIX_RE.sub("", encoded, count=1)


def _strip_parent_segments(rest: str) -> str:
    """Eat up to two common parent directory segments (e.g. Desktop, Projects)."""
    for _ in range(2):
        stripped = False
        for seg in _COMMON_PARENT_SEGMENTS:
            prefix = f"{seg}-"
            if rest.startswith(prefix):
                rest = rest[len(prefix):]
                stripped = True
                break
        if not stripped:
            break
    return rest


def decode_wing_from_encoded(encoded: str) -> str:
    """Best-guess wing name from Claude Code's encoded folder name.

    Claude Code encodes absolute paths by replacing path separators with `-`.
    On Windows, ``C:\\Users\\<name>\\Desktop\\foo`` becomes
    ``C--Users-<name>-Desktop-foo``. Project names that contain hyphens are
    inherently ambiguous to reverse — we strip the well-known user/parent
    prefixes and let the human review the generated YAML.
    """
    s = _strip_user_prefix(encoded)
    s = _strip_parent_segments(s)
    if not s:
        return "unnamed"
    return sanitize_wing_name(s)


def is_likely_noise(encoded: str) -> bool:
    """True for bare $HOME/<parent-dir> entries that shouldn't be ingested."""
    rest = _strip_user_prefix(encoded)
    return rest in _NOISE_TRAILING_SEGMENTS


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
    out_path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")


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
