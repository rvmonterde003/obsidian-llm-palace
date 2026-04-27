"""Archive a wing: rename every drawer's wing to _archive_<wing>.

After archiving, the wing's drawers remain searchable via explicit
`mempalace search "X" --wing _archive_<wing>`, but the SessionStart wake-up
hook (Task 7) skips wings whose names start with `_archive_`.
"""
import argparse
import sys
from typing import List

from mempalace.mcp_server import tool_list_drawers, tool_update_drawer


PAGE_SIZE = 100
ARCHIVE_PREFIX = "_archive_"


def list_all_drawer_ids_for_wing(wing: str) -> List[str]:
    """Return all drawer IDs filed under the given wing, paginating as needed."""
    ids: List[str] = []
    offset = 0
    while True:
        result = tool_list_drawers(wing=wing, limit=PAGE_SIZE, offset=offset)
        if not isinstance(result, dict) or "error" in result:
            return ids
        page = result.get("drawers", [])
        if not page:
            break
        for drawer in page:
            if "id" in drawer:
                ids.append(drawer["id"])
        offset += PAGE_SIZE
    return ids


def archive_wing(wing: str) -> int:
    """Move all drawers from <wing> to _archive_<wing>.

    Returns 0 on success, non-zero on failure.
    """
    if wing.startswith(ARCHIVE_PREFIX):
        print(f"ERROR: wing {wing!r} is already archived. Refusing to double-archive.", file=sys.stderr)
        return 2

    new_wing = f"{ARCHIVE_PREFIX}{wing}"
    ids = list_all_drawer_ids_for_wing(wing)

    if not ids:
        print(f"No drawers found under wing {wing!r} - nothing to archive.")
        return 0

    print(f"Archiving {len(ids)} drawer(s): {wing} -> {new_wing}")
    for drawer_id in ids:
        result = tool_update_drawer(drawer_id=drawer_id, wing=new_wing)
        if not isinstance(result, dict) or not result.get("success", False):
            err = result.get("error", "unknown") if isinstance(result, dict) else "unknown"
            print(f"  FAIL drawer {drawer_id}: {err}", file=sys.stderr)
            return 1

    print(f"Done. Future sessions will skip wake-up for {new_wing} (prefix {ARCHIVE_PREFIX}).")
    print(f"Search remains available: python -m mempalace search 'X' --wing {new_wing}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Archive a MemPalace wing (rename drawers' wing to _archive_<name>).")
    p.add_argument("wing", help="Wing name to archive (e.g., old-project)")
    args = p.parse_args()
    return archive_wing(args.wing)


if __name__ == "__main__":
    sys.exit(main())
