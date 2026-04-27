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
    print("DONE - all included rows mined successfully")
    return 0


def main() -> int:
    plan_path = Path(__file__).parent.parent / "backfill-plan.yaml"
    if not plan_path.exists():
        print(f"ERROR: {plan_path} not found. Run scripts/backfill_plan.py first.", file=sys.stderr)
        return 1
    return run_plan(plan_path, CLAUDE_PROJECTS_DIR)


if __name__ == "__main__":
    sys.exit(main())
