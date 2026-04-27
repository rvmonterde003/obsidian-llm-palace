# MemPalace Memory Retrieval — Design Spec

**Date:** 2026-04-27
**Owner:** rvmonterde003
**Status:** Draft (pending user approval)
**Scope:** Wire MemPalace as the OS-wide conversation-memory layer for Claude Code, backfilled from existing session transcripts and partitioned per project.

---

## Goal

Make every past and future Claude Code conversation — across all 19+ projects on this machine — cheaply searchable from inside any Claude Code session, without leaking content between unrelated projects by default.

The user's stated motivation: *"use obsidian-llm-palace for memory retrieval of old conversations"*, with the cost-efficiency expectation that pre-compiled / locally-embedded retrieval beats raw RAG.

## Non-Goals

- Building a custom retrieval layer. MemPalace already ships search, wake-up, drawers, tunnels, and a 29-tool MCP server.
- Modifying the wiki layer of `obsidian-llm-palace`. The wiki (Karpathy's compiled-knowledge pattern) is unchanged. This spec only wires MemPalace.
- Per-prompt auto-search injection (`UserPromptSubmit` hook). Considered and rejected — see Section 4.
- Cross-machine sync. Palace is local-only.

## Mental-model correction (preserved here so we don't re-litigate)

Karpathy's wiki pattern is for **compiled knowledge from raw sources** — papers, articles, repo notes. It makes *knowledge queries* cheap by reading 3-5 wiki pages instead of RAG-searching 500 docs.

Conversation recall is the other half of `obsidian-llm-palace`: **MemPalace** stores conversations as embeddings in a local ChromaDB and returns the relevant "drawer" via semantic search (~500–1000 tokens per recall, zero API cost). That is where cheap conversation retrieval comes from.

This spec is about wiring **MemPalace** specifically.

---

## 1. High-level architecture

One OS-wide palace at `~/.mempalace/palace/` (Chroma vectors + SQLite knowledge graph), partitioned internally by **wing** (top-level) and **room** (subdivision inside a wing).

**Wing = project**, derived from project folder basename. The user explicitly chose this over wing-by-topic.

```
                     ~/.mempalace/palace/           ← single OS-wide palace
                     ├── chroma/   (vectors)
                     └── palace.db (SQLite knowledge graph)
                              ▲
                              │ wing = <project-folder-name>
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────┴────┐           ┌────┴─────┐         ┌─────┴─────┐
   │ BACKFILL│           │   SAVE   │         │ RETRIEVE  │
   │ one-off │           │  hooks   │         │  surfaces │
   └────┬────┘           └────┬─────┘         └─────┬─────┘
        │                     │                     │
  mempalace mine        Stop + PreCompact      A. MCP server  (on-demand)
  ~/.claude/projects/*  hooks in user-         B. SessionStart hook (auto wake-up)
  --mode convos         global settings.json   D. /recall slash command (manual)
  --wing <derived>       (auto-save going-fwd)
```

### Correctness invariants

- **One palace, many wings.** No per-project palace duplicates.
- **Wing name = last path segment of project root** (e.g., `betaflight-sitl-msp-comms`).
- **Hooks live in `~/.claude/settings.json` (user-global)** — all projects auto-save without per-repo wiring.
- **Palace stays at `~/.mempalace/palace`** — outside any git repo. Conversation contents never accidentally committed.
- **Windows Unicode**: every `mempalace` invocation prefixed with `PYTHONIOENCODING=utf-8` to avoid the cp1252 crash.

---

## 2. Backfill pipeline (one-off)

**Inputs:** 19 directories under `~/.claude/projects/<encoded-folder>/*.jsonl`.

**Naming problem:** Claude Code encodes folder paths by replacing `\` with `-`, producing names like `C--Users-Admin-Desktop-AD-KD-betaflight-sitl-msp-comms`. Project names with hyphens (`AD-KD`, `wfa-remote-vibe-coding`) make this lossy to auto-decode. Some entries are accidental "parent dir" sessions (`C--Users-Admin-Desktop`).

**Solution:** generated review-then-execute mapping file.

### `scripts/backfill_plan.py`

Enumerates `~/.claude/projects/*` and writes `backfill-plan.yaml`:

```yaml
- encoded: C--Users-Admin-Desktop-AD-KD-betaflight-sitl-msp-comms
  wing: betaflight-sitl-msp-comms
  transcripts: 4
  include: true
- encoded: C--Users-Admin-Desktop
  wing: desktop-noise
  transcripts: 1
  include: false        # suggested skip — parent-dir noise
- encoded: C--Users-Admin-Desktop-PrimeAI-Joey-Munoz
  wing: primeai-joey-munoz
  transcripts: 12
  include: true         # client work — flip to false if NDA-sensitive
```

User reviews and edits before any ingestion happens. **This is the privacy/sanity gate.**

### `scripts/backfill_run.py`

Reads `backfill-plan.yaml`, for each `include: true` row runs:

```bash
PYTHONIOENCODING=utf-8 python -m mempalace mine \
    "<HOME>/.claude/projects/<encoded>" \
    --mode convos \
    --wing <wing>
```

### Pre-flight (run once)

- `mempalace init ~/` — creates `~/.mempalace/palace`, detects room structure.
- `mempalace split <encoded>` — only if any session file is a concatenated mega-transcript (Claude Code rotates on session boundaries, so usually unnecessary; the script checks file sizes and calls `split` defensively).

### Idempotency

`mempalace mine` is content-addressed via the `dedup` module. Re-running is safe.

### Verification after backfill

```bash
mempalace status                                                         # drawer count per wing
mempalace search "MSP serial protocol" --wing betaflight-sitl-msp-comms  # smoke test
```

---

## 3. Save pipeline (going-forward)

Two hooks in `~/.claude/settings.json` (user-global):

```json
{
  "hooks": {
    "Stop": [
      { "matcher": "*", "hooks": [{
        "type": "command",
        "command": "python -m mempalace hook run --hook stop --harness claude-code",
        "timeout": 30
      }] }
    ],
    "PreCompact": [
      { "hooks": [{
        "type": "command",
        "command": "python -m mempalace hook run --hook precompact --harness claude-code",
        "timeout": 30
      }] }
    ]
  }
}
```

### How the hook actually works (verified from `mempalace/hooks_cli.py`)

| Hook | Trigger | What it emits |
|---|---|---|
| `Stop` | End of each Claude turn (rate-limited every 15 msgs via `~/.mempalace/hook_state/`) | Blocks the turn with `STOP_BLOCK_REASON` instructing Claude to call `mempalace_add_drawer` for recent exchanges |
| `PreCompact` | Just before context compaction | Always blocks with a stronger "save EVERYTHING now" instruction so nothing is lost in compaction |

**The hook does not write to the palace itself** — it coerces Claude into doing the writing via the MCP tool. This is why the MCP server (Section 4) is a hard dependency of the save pipeline, not just retrieval.

### Wing resolution at save time

Claude looks for, in order:

1. `Wing: <name>` declared in the project's `CLAUDE.md` (Section 5).
2. Project root basename inferred from `cwd`.
3. Falls back to encoded `~/.claude/projects/<encoded>` dirname.

### Windows specifics

- Hook command must use `python -m mempalace`, not bare `mempalace`.
- Set `PYTHONIOENCODING=utf-8` system-wide via `setx PYTHONIOENCODING utf-8` (one-time, persists).

### Failure mode

If `python -m mempalace` is not on PATH or the palace isn't initialized, the hook timeout expires and Claude proceeds without saving — fail-open. We'd rather lose a save than break a session.

---

## 4. Retrieval pipeline (A + B + D)

### A. MCP server — pull-on-demand

Register MemPalace as an MCP server in user-global Claude Code config:

```bash
claude mcp add --scope user mempalace -- "C:\Python313\python.exe" -m mempalace.mcp_server
```

Exposes ~29 tools: `mempalace_search`, `mempalace_add_drawer`, `mempalace_list_wings`, `mempalace_wake_up`, `mempalace_find_tunnels`, `mempalace_delete_drawer`, etc. Claude calls them when context warrants. Zero token cost until invoked.

The MCP server is also what the **save pipeline depends on** — `add_drawer` is the tool Claude uses when the Stop hook blocks for save.

### B. SessionStart hook — auto-inject wake-up

Hook in `~/.claude/settings.json` invokes a wrapper script (cross-platform, gives a place to encode skip-prefix logic for archived wings — see Section 6 Pattern 1):

```json
"SessionStart": [
  { "hooks": [{
    "type": "command",
    "command": "python <obsidian-llm-palace>/scripts/session_start_hook.py",
    "timeout": 15
  }] }
]
```

`scripts/session_start_hook.py` does this (cross-platform, no shell substitution):

1. Derive `wing = basename(os.getcwd())`.
2. Read `scripts/wake_up_skip_prefixes.txt` (one prefix per line; default contents: `_archive_`).
3. If wing matches any skip prefix → exit 0 with empty stdout (no tokens injected).
4. Otherwise run `python -m mempalace wake-up --wing <wing> --format json` and pipe stdout through. Sets `PYTHONIOENCODING=utf-8` in the subprocess env.

This pipes the ~600–900 token L0+L1 cache into Claude's initial context for live wings. Claude opens already aware of the prior session's decisions for *this* wing.

**Wing detection at wake-up time** uses `cwd` basename rather than `CLAUDE.md` (the SessionStart hook fires before Claude reads any project files). For projects where the basename has no drawers, `wake-up` returns empty — zero tokens added, safe failure.

### D. `/recall` slash command — manual escape hatch

`~/.claude/commands/recall.md`:

```markdown
---
description: Search MemPalace for past conversations
---
Run: `python -m mempalace search "$ARGUMENTS" --limit 5`
Then read the matching drawers and synthesize an answer with citations.
```

Used as `/recall MSP serial protocol decisions` when Claude hasn't surfaced the right thing on its own.

### Why C (per-prompt auto-search) is excluded

A `UserPromptSubmit` hook running `mempalace search` against every prompt would inject 100–500 tokens of often-irrelevant context per turn — that compounds across a session. MemPalace search is cheap; **token-injection into context is not**. A+B+D captures ~95% of the recall value without that tax. Revisit only if A+B underperforms.

---

## 5. Project → wing mapping

### The convention

Every project that should have memory adds a `## MemPalace` section to its `CLAUDE.md`:

```markdown
## MemPalace

Wing: betaflight-sitl-msp-comms
```

Two-line section. Claude reads `CLAUDE.md` at every session start, so the wing name is resolved deterministically.

### Resolution order

**At save time:**
1. `Wing:` in `CLAUDE.md` → use that.
2. No `CLAUDE.md` or no `Wing:` line → `basename(cwd)`.
3. Empty/generic basename (`Desktop`, `AD-KD`) → encoded `~/.claude/projects/<encoded>` dirname.

**At wake-up time** (SessionStart hook fires before Claude reads files): always `basename(cwd)`.

**Implication:** the `CLAUDE.md` `Wing:` value should **match `basename(cwd)`** so save and wake-up agree on the wing name. If they disagree, save goes one place, wake-up reads from another, and history disappears across sessions.

### Concrete instances

| Project root | CLAUDE.md `Wing:` value |
|---|---|
| `~/Desktop/AD-KD/betaflight-sitl-msp-comms` | `betaflight-sitl-msp-comms` |
| `~/Desktop/AD-KD/obsidian-llm-palace` | `obsidian-llm-palace` |
| `~/robotics-ai-thinking` | `robotics-ai-thinking` |
| `~/Desktop/Personal-Projects/Cash-Flow-Management` | `cash-flow-management` |

### Onboarding a new project

1. Add `## MemPalace\n\nWing: <basename(cwd)>` to that project's `CLAUDE.md`.
2. That's it. First Stop hook fires → Claude saves to that wing → wing exists.

Wings are not "created" as a separate step — they appear the moment the first drawer is filed under that name (`tool_list_wings` enumerates distinct `wing` values across drawers).

---

## 6. Cleanup / removal patterns

MemPalace exposes drawer-level deletion (`mempalace_delete_drawer`, `mempalace_delete_tunnel`) but **no first-class wing-level deletion**. Two patterns supported by this design:

### Pattern 1 — Archive (default for completed personal projects)

Stop saving and stop wake-up. Drawers stay searchable on explicit query.

`scripts/archive_wing.py <wing>`:
- Renames wing in metadata: `<wing>` → `_archive_<wing>` (iterates `update_drawer` with new wing).
- The default `_archive_` prefix is already in `scripts/wake_up_skip_prefixes.txt`, so the SessionStart wrapper (Section 4.B) automatically stops auto-loading wake-up for archived wings.
- Drawers remain accessible via explicit `mempalace search "X" --wing _archive_<wing>`.

Cost: ~30 seconds, zero data loss.

### Pattern 2 — Hard delete (for client work, NDA cleanup, accidental ingest)

`scripts/delete_wing.py <wing>`:
- `list_drawers --wing <wing>` → iterate `delete_drawer(id)` with confirmation prompt.
- Clean any tunnels involving that wing via `delete_tunnel`.
- Verify with `mempalace status` — wing should disappear once drawer count hits zero.

Cost: a few seconds of script execution. **Irreversible** (the API itself documents this).

### Pattern 3 — Nuke and re-backfill (nuclear option)

`rm -rf ~/.mempalace/ && python scripts/backfill_run.py`. No script needed; documented here as the option of last resort. Edit `backfill-plan.yaml` first to flip unwanted wings to `include: false`.

---

## 7. Privacy posture

- Palace at `~/.mempalace/palace` — outside any git repo. No accidental commits.
- Backfill is reviewable before execution via `backfill-plan.yaml`.
- No remote calls — embeddings (all-MiniLM-L6-v2) and storage are local. Zero data leaves the machine.
- Cross-wing search is opt-in — default `mempalace search "X"` searches all wings; pass `--wing <name>` to scope. The MCP `search` tool exposes the same flag.
- For client-work isolation: per-project `CLAUDE.md` may state "do not cross-search wings unless asked" so Claude defaults to scoping searches.

---

## 8. Failure-mode matrix

| Failure | Symptom | Behavior |
|---|---|---|
| `python -m mempalace` not on PATH | Hooks timeout silently | Session proceeds without save/wake-up; `mempalace status` shows no growth. |
| Palace corrupted (segfault on search) | MCP tool errors | Run `mempalace repair`. Drawers preserved. |
| Wing mismatch between save and wake-up | History "disappears" across sessions | `mempalace list-wings` reveals duplicates; fix `CLAUDE.md` to match `basename(cwd)`. |
| Backfill ingests sensitive data unintentionally | Searches surface unwanted content | First defense: `backfill-plan.yaml` review. Second defense: Pattern 2 hard delete. |
| Windows cp1252 crash | `UnicodeEncodeError` on CLI output | `setx PYTHONIOENCODING utf-8` (one-time). |
| Stop hook saves too aggressively (every 15 msgs on chatty session) | Save-blocks interrupt flow | `SAVE_INTERVAL` is hardcoded in `hooks_cli.py`. Out of scope for v1. Revisit if it bites. |

---

## 9. Verification checklist

Run in order. Each must pass before the next.

1. **Install verification** — `python -m mempalace status` → palace path, wing count = 0, no errors.
2. **Init** — `python -m mempalace init ~/` → palace structure created.
3. **Backfill plan generation** — `python scripts/backfill_plan.py` → `backfill-plan.yaml` with 19 rows. Review.
4. **Backfill execution** — `python scripts/backfill_run.py` → per-row "mined N exchanges into wing X" logs. End with `mempalace status` showing N wings.
5. **MCP registration** — `claude mcp list` → `mempalace` listed.
6. **Save hook smoke test** — start session in `betaflight-sitl-msp-comms`, exchange ~16 messages, end. `mempalace search "<phrase from session>" --wing betaflight-sitl-msp-comms` → ≥1 hit.
7. **Wake-up hook smoke test** — fresh session in same project, ask "what did we discuss last session?" → Claude references prior exchange unprompted.
8. **`/recall` smoke test** — `/recall MSP serial protocol` → top hits printed inline.

---

## 10. Rollback

If anything goes wrong:

- **Disable hooks** — edit `~/.claude/settings.json`, remove `Stop` / `PreCompact` / `SessionStart` entries.
- **Disable MCP** — `claude mcp remove mempalace`.
- **Nuke palace** — `rm -rf ~/.mempalace/`. Conversation files in `~/.claude/projects/` untouched; can re-backfill anytime.

No state escapes into projects except the `CLAUDE.md` `Wing:` lines (harmless leftovers if MemPalace is uninstalled).

---

## 11. Deliverables

In `obsidian-llm-palace/` (sibling to `betaflight-sitl-msp-comms`):

- `scripts/backfill_plan.py` — generates `backfill-plan.yaml` from `~/.claude/projects/`.
- `scripts/backfill_run.py` — executes plan against `mempalace mine`.
- `scripts/session_start_hook.py` — wake-up wrapper invoked by SessionStart hook. Derives wing from `cwd`, checks skip-prefixes, calls `mempalace wake-up`.
- `scripts/wake_up_skip_prefixes.txt` — one prefix per line; default `_archive_`.
- `scripts/archive_wing.py` — Pattern 1 cleanup.
- `scripts/delete_wing.py` — Pattern 2 cleanup, with confirmation prompt.
- `docs/superpowers/specs/2026-04-27-mempalace-memory-retrieval-design.md` — this document.

In `~/.claude/`:

- `settings.json` — `Stop`, `PreCompact`, `SessionStart` hooks added.
- `commands/recall.md` — slash command.

In each opted-in project's root:

- `CLAUDE.md` — `## MemPalace\n\nWing: <name>` section appended.

---

## Open questions for v2 (not blocking)

- Whether `SAVE_INTERVAL=15` is right for this user's session shape. Revisit after a week of dogfooding.
- Whether to also mine the `obsidian-llm-palace/llm-palace/wiki/` markdown into the palace (project-style mining) so semantic search hits across both compiled-knowledge and conversation layers. Defer until the conversation-only setup is stable.
- Whether the per-project `CLAUDE.md` should also pin search-scope defaults ("only cross-search wings on explicit ask"). Current design relies on Claude's judgment.
