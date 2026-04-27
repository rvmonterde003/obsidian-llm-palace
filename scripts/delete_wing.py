"""Hard-delete a wing: irreversibly remove all drawers and tunnels under it."""
import argparse
import sys
from typing import List

from mempalace.mcp_server import (
    tool_delete_drawer,
    tool_delete_tunnel,
    tool_list_tunnels,
)

from scripts.archive_wing import list_all_drawer_ids_for_wing


def list_tunnel_ids_for_wing(wing: str) -> List[str]:
    """Return tunnel IDs involving the given wing.

    Tolerates both `{"tunnels": [...]}` and bare-list response shapes.
    Returns [] on error or exception.
    """
    try:
        result = tool_list_tunnels(wing=wing)
    except Exception as exc:
        print(f"  WARN list_tunnels raised: {exc}", file=sys.stderr)
        return []
    if isinstance(result, dict):
        if "error" in result:
            return []
        items = result.get("tunnels", [])
    elif isinstance(result, list):
        items = result
    else:
        return []
    return [t["id"] for t in items if isinstance(t, dict) and "id" in t]


def delete_wing(wing: str, confirmed: bool) -> int:
    """Hard-delete every drawer and tunnel under wing. Irreversible.

    Returns 0 on success (or no-op for empty wing), non-zero on failure or unconfirmed.
    """
    if not confirmed:
        print(f"Aborting: pass --yes (or answer 'y') to actually delete wing {wing!r}.")
        return 2

    drawer_ids = list_all_drawer_ids_for_wing(wing)
    tunnel_ids = list_tunnel_ids_for_wing(wing)

    if not drawer_ids and not tunnel_ids:
        print(f"Wing {wing!r} has no drawers or tunnels - nothing to delete.")
        return 0

    print(f"Deleting {len(drawer_ids)} drawer(s) and {len(tunnel_ids)} tunnel(s) from {wing!r}...")

    deleted_drawers = 0
    for drawer_id in drawer_ids:
        try:
            result = tool_delete_drawer(drawer_id=drawer_id)
        except Exception as exc:
            print(f"  FAIL drawer {drawer_id}: exception: {exc}", file=sys.stderr)
            print(
                f"  Partial state: {deleted_drawers} of {len(drawer_ids)} drawer(s) "
                f"deleted before failure. Wing {wing!r} is in an inconsistent state.",
                file=sys.stderr,
            )
            return 1
        if not isinstance(result, dict) or not result.get("success", False):
            err = result.get("error", "unknown") if isinstance(result, dict) else "unknown"
            print(f"  FAIL drawer {drawer_id}: {err}", file=sys.stderr)
            print(
                f"  Partial state: {deleted_drawers} of {len(drawer_ids)} drawer(s) "
                f"deleted before failure. Wing {wing!r} is in an inconsistent state.",
                file=sys.stderr,
            )
            return 1
        deleted_drawers += 1

    deleted_tunnels = 0
    for tunnel_id in tunnel_ids:
        try:
            result = tool_delete_tunnel(tunnel_id=tunnel_id)
        except Exception as exc:
            print(f"  FAIL tunnel {tunnel_id}: exception: {exc}", file=sys.stderr)
            print(
                f"  Partial state: all {deleted_drawers} drawer(s) deleted, "
                f"{deleted_tunnels} of {len(tunnel_ids)} tunnel(s) deleted before failure.",
                file=sys.stderr,
            )
            return 1
        if not isinstance(result, dict) or not result.get("success", False):
            err = result.get("error", "unknown") if isinstance(result, dict) else "unknown"
            print(f"  FAIL tunnel {tunnel_id}: {err}", file=sys.stderr)
            print(
                f"  Partial state: all {deleted_drawers} drawer(s) deleted, "
                f"{deleted_tunnels} of {len(tunnel_ids)} tunnel(s) deleted before failure.",
                file=sys.stderr,
            )
            return 1
        deleted_tunnels += 1

    print(f"Wing {wing!r} deleted. Verify with: python -m mempalace status")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Hard-delete a MemPalace wing. IRREVERSIBLE.",
    )
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
