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
    # Strip common parent dirs (Desktop comes first, then project-specific parents)
    for prefix in ("Desktop-", "robotics-ai-thinking-", "Personal-Projects-", "PrimeAI-", "AD-KD-", "Claude-tools-"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            # After stripping Desktop-, continue checking for nested parent dirs
            if prefix == "Desktop-":
                for nested_prefix in ("robotics-ai-thinking-", "Personal-Projects-", "PrimeAI-", "AD-KD-", "Claude-tools-"):
                    if s.startswith(nested_prefix):
                        s = s[len(nested_prefix):]
                        break
            break
    if not s:
        return "unnamed"
    return sanitize_wing_name(s)


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
