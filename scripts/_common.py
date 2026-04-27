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
