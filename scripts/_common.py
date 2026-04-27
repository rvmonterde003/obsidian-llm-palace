"""Shared constants and helpers for MemPalace tooling scripts."""
import os
import re
import unicodedata
from pathlib import Path

PALACE_PATH = Path.home() / ".mempalace" / "palace"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def derive_wing_from_cwd(cwd: str) -> str:
    """Wing name = lowercased basename of the project directory."""
    return Path(cwd).name.lower()


def sanitize_wing_name(name: str) -> str:
    """Coerce a string into a valid wing name: lowercase, ASCII, hyphens for unsafe chars.

    Raises ValueError if the input collapses to an empty string (e.g., "", "---", "βeta"
    after Unicode strip), which would silently route drawers to a wing with no name.
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9_-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    if not name:
        raise ValueError(f"sanitize_wing_name produced an empty wing name from input")
    return name


def mempalace_env() -> dict:
    """Subprocess env that won't crash on Windows cp1252."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env
