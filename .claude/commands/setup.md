---
description: First-time setup of the LLM Wiki + MemPalace pipeline on a fresh clone. Walks through install, init, MCP registration, and hook wiring. Assumes clean slate (no existing palace).
---

You are walking the user through first-time setup of this repo. They have just cloned it and are running Claude Code from inside the repo root. Assume they have:

- Python 3.10+ on PATH
- Git installed
- Claude Code CLI installed
- **NO** existing MemPalace palace at `~/.mempalace/`
- **NO** existing pipeline content in this vault

Walk them through every step **in order**. Verify state with bash checks before each step. **Ask the user before destructive or irreversible actions.** Report each step's outcome to them in plain language. Do not skip the verification checks.

This setup uses cross-platform commands. Where Windows differs (env vars, line endings), call it out and provide PowerShell-compatible alternatives.

---

## Step 0 — Detect environment

Run these and tell the user what you found:

```bash
python --version
pip --version
git --version
```

If Python is < 3.10, stop and tell the user to upgrade. If any command is missing, stop and tell them what's missing.

Detect OS:

```bash
python -c "import platform; print(platform.system())"
```

Note whether it's `Windows`, `Darwin`, or `Linux` — you'll need it for step 2 and step 6.

---

## Step 1 — Install Python dependencies

Check what's already installed:

```bash
python -c "import mempalace, yaml, pytest, pytest_mock; print('ok')" 2>&1
```

If that prints `ok`, skip to step 2. Otherwise install:

```bash
pip install mempalace pyyaml pytest pytest-mock
```

If pip fails with permission errors, retry with `pip install --user mempalace pyyaml pytest pytest-mock`.

Re-verify:

```bash
python -c "import mempalace; print(mempalace.__version__ if hasattr(mempalace, '__version__') else 'installed')"
```

Mempalace must be ≥ 3.3.0.

---

## Step 2 — Set PYTHONIOENCODING (Windows only)

Skip this step on macOS or Linux. On **Windows**, mempalace's CLI crashes on cp1252-encoded output. Set the env var permanently:

```powershell
setx PYTHONIOENCODING utf-8
```

**Tell the user explicitly: "Close and reopen your terminal so the env var loads, then continue."** Wait for them to confirm they've done this before proceeding.

---

## Step 3 — Initialize the MemPalace palace

```bash
python -m mempalace init ~/
```

This is **interactive**. Do NOT pipe yes/no answers — let the user respond. Tell them what to do at each prompt:

1. At "PROJECTS / Your choice [enter/edit/add]": press **Enter** to accept the auto-detected entities (or type `edit` to clean them up — they're rough heuristics, often noise).
2. At "Add any missing? [y/N]": type **N** unless they want to manually name projects.
3. At "Review the proposed rooms": press **Enter** to accept room defaults.

After the init exits, run:

```bash
python -m mempalace status
```

Expect: `No palace found at ...`. **That's correct** — the palace doesn't exist yet; it's created on first mine.

---

## Step 4 — (Optional) Backfill existing Claude Code conversations

**Ask the user:**

> "Do you want to ingest your existing Claude Code conversation history (`~/.claude/projects/`) into MemPalace? This is a one-time backfill, reviewable before execution. You can decline and only have *future* conversations auto-saved."

If they say **no**, skip to step 5.

If **yes**:

```bash
python -m scripts.backfill_plan
```

This writes `backfill-plan.yaml` in the repo root. Open it for the user — pick the right command for their OS:

```bash
# Windows:
notepad backfill-plan.yaml

# macOS:
open backfill-plan.yaml

# Linux:
xdg-open backfill-plan.yaml
```

Tell the user:

> "Review every row. Each represents a project's conversation history. The `wing` field is the wing name that history will be filed under in MemPalace; rename if you want. The `include: true/false` field controls whether to ingest. **Flip `include: false` on anything sensitive — client work, NDA-bound projects, anything you don't want findable across all your future Claude sessions.** Save and close when done."

Wait for them to confirm they've finished editing. Then:

```bash
python -m scripts.backfill_run
```

This may take several minutes depending on transcript volume. Show the user the per-row `[mine] wing=...` progress lines as they appear.

After completion:

```bash
python -m mempalace status
```

Should show the included wings each with N drawers.

---

## Step 5 — Register MemPalace as an MCP server (user-globally)

Get the user's Python path:

```bash
python -c "import sys; print(sys.executable)"
```

Save that path. Then register:

```bash
claude mcp add --scope user mempalace -- "<PYTHON_PATH_FROM_ABOVE>" -m mempalace.mcp_server
```

Verify:

```bash
claude mcp list
```

Expect `mempalace` in the list with status `✓ Connected` (or `unknown`/`connecting` until the next session loads it — also fine).

---

## Step 6 — Wire hooks in `~/.claude/settings.json`

**This is the most fragile step. Be careful — settings.json is shared with Claude Code core.**

Read the user's current settings:

```bash
# Linux/macOS:
cat ~/.claude/settings.json 2>&1

# Windows PowerShell:
Get-Content $env:USERPROFILE\.claude\settings.json
```

Three cases:

### Case A: Settings file doesn't exist

Create one with just the `hooks` block. Get the absolute path to `session_start_hook.py`:

```bash
python -c "from pathlib import Path; print(Path('scripts/session_start_hook.py').resolve())"
```

Use the printed path to replace `<ABSOLUTE_PATH>` below, then write to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "python -m mempalace hook run --hook stop --harness claude-code", "timeout": 30 }] }
    ],
    "PreCompact": [
      { "hooks": [{ "type": "command", "command": "python -m mempalace hook run --hook precompact --harness claude-code", "timeout": 30 }] }
    ],
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "python <ABSOLUTE_PATH>", "timeout": 15 }] }
    ]
  }
}
```

### Case B: Settings file exists, no `hooks` key

**Read the entire existing file**. Show the user the full current contents. Compose a new JSON object that preserves every existing key (`permissions`, `model`, `theme`, etc.) and adds the `hooks` block above. Show the user the **full proposed merged JSON** before writing. **Ask them to confirm** before overwriting.

### Case C: Settings file exists with existing `hooks` key

**Stop and warn the user**: "Your settings.json already has hooks configured. I won't auto-merge to avoid breaking your existing setup. Please show me the existing `hooks` block so we can manually add Stop, PreCompact, and SessionStart entries without conflicts."

In all cases, **back up first**:

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak 2>/dev/null
```

After writing, validate:

```bash
python -c "import json, os; json.load(open(os.path.expanduser('~/.claude/settings.json'))); print('valid JSON')"
```

If parse fails, restore from the backup and ask the user for help.

---

## Step 7 — (Optional) Customize the per-project wing in CLAUDE.md

This step is per-project, not one-time. For each project where the user wants memory-tracking with a clean wing name, append this to that project's `CLAUDE.md`:

```markdown
## MemPalace

Wing: <project-folder-basename>
```

The repo's own `obsidian-llm-palace/obsidian-llm-palace/CLAUDE.md` already has this section as a reference example. Tell the user this is something they do per-project as they work — not a one-time setup.

---

## Step 8 — Verification

Tell the user setup is complete. Suggest the live smoke test:

1. Open a fresh terminal, `cd` into any project (e.g., this repo), run `claude`.
2. In that session, type `/recall` (no args) — on a fresh install this reports an empty palace, confirming wake-up wiring works end-to-end before any real history exists.
3. Have a short conversation. End the session, then type `/save` so Claude distills it into a MemPalace diary entry + drawers and refreshes `wiki/hot.md`.
4. Open *another* fresh session in the same project. Type `/recall` again (or just ask "where did we leave off?") — Claude should report what was decided in step 3 without you reminding it (SessionStart hook injected wake-up content into Claude's context).
5. From any session, try `/recall <some query>` to test semantic search mode.

---

## What's available after setup

- **Slash commands** (project-level — live under `.claude/commands/`):
  - `/setup` — re-run this playbook (re-entrant; safe to run twice).
  - `/save` — distill the current session into MemPalace + refresh `wiki/hot.md` and append to `wiki/log.md`.
  - `/recall` — no args: resume the last session. With args: semantic search across MemPalace wings.
- **Save side**: Stop hook (per-turn save; **deferred in this vault** — see `obsidian-llm-palace/CLAUDE.md` → *Save Behavior*), PreCompact hook (pre-compression insurance), and explicit `/save` or end-of-session pause-phrases ("let's wrap this up", "I'll resume later", "save what we have") all flush to MemPalace.
- **Retrieve side**: SessionStart hook injects wake-up at session start; `/recall` slash command exposes both resume and semantic-search modes; Claude can call `mempalace_search` and other MCP tools natively from any prompt.
- **Cleanup**: `python -m scripts.archive_wing <name>` (rename to `_archive_<name>`, skipped by wake-up); `python -m scripts.delete_wing <name> --yes` (irreversible drawer + tunnel deletion).
- **Wiki layer**: drop markdown into `obsidian-llm-palace/wiki/concepts/`, `entities/`, etc. (gitignored, your content), then `python -m mempalace mine "obsidian-llm-palace/obsidian-llm-palace/wiki" --wing obsidian-llm-palace` to add it to MemPalace search.

Setup playbook complete. Tell the user the system is live and walk them through whichever optional next step they want first.
