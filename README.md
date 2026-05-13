# Obsidian LLM Palace

A combined knowledge management pipeline that merges [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern with [MemPalace](https://github.com/MemPalace/mempalace) — an open-source AI memory system — using [Obsidian](https://obsidian.md) as the visual frontend.

**The idea**: LLM Wiki compiles raw sources into structured, cross-referenced knowledge. MemPalace stores every conversation verbatim and makes it searchable. Together, they give your AI agent both *compiled knowledge* and *raw recall* — two layers that neither system provides alone.

---

## Why This Exists

| Problem | How This Solves It |
|---|---|
| RAG degrades as corpus grows | Wiki pre-compiles knowledge — Claude reads 3-5 pages, not 500 documents |
| LLMs forget between sessions | MemPalace auto-saves conversations every 15 messages + before context compaction |
| Knowledge bases die from neglect | Claude handles the bookkeeping — summarization, cross-referencing, linting |
| No visual way to browse AI knowledge | Obsidian renders wikilinks as an interactive graph with backlinks |
| Compiled knowledge lacks raw recall | MemPalace's semantic search finds the exact conversation where a decision was made |
| Raw recall lacks structure | Wiki pages organize and cross-reference what matters |

---

## Architecture

```
                    YOU
                     |
          +----------+----------+
          |                     |
     [ Obsidian ]         [ Claude Code ]
     Visual frontend      AI engine
     Graph view           Ingest / Query / Lint
     Backlinks            File operations
     Dashboards           MCP tools
          |                     |
          +----------+----------+
                     |
        +------------+------------+
        |            |            |
    [ raw/ ]    [ wiki/ ]   [ MemPalace ]
    Immutable    Compiled    Conversation
    sources      knowledge   memory
    (truth)      (understanding)  (recall)
        |            |            |
        Layer 1      Layer 2      Layer 3
```

### Three-Layer Memory Model

| Layer | What | Format | Maintained By |
|---|---|---|---|
| `raw/` | Immutable source documents | Markdown, PDF, text | You (drop files in) |
| `wiki/` | Compiled knowledge with cross-references | Markdown + YAML frontmatter + `[[wikilinks]]` | Claude Code |
| MemPalace | Verbatim conversation history | ChromaDB vectors + SQLite knowledge graph | Auto-save hooks |

### Three Core Operations

- **Ingest** — Drop sources into `raw/`, ask Claude to process them. Creates wiki pages, updates the index, logs the operation.
- **Query** — Ask a question. Claude checks the wiki first (fast, structured), falls back to MemPalace for conversation recall.
- **Lint** — Health-check the wiki for contradictions, orphan pages, stale claims, and missing cross-references.

---

## Vault Structure

```
obsidian-llm-palace/
├── obsidian-llm-palace/            # Obsidian vault root
│   ├── CLAUDE.md                    # Schema — tells Claude how to run the wiki
│   ├── .gitignore
│   │
│   ├── raw/                         # Layer 1: Immutable sources
│   │   ├── articles/                # Web articles, blog posts
│   │   ├── papers/                  # Academic papers, whitepapers
│   │   ├── repos/                   # Code snippets, repo notes
│   │   ├── data/                    # Datasets, CSV, JSON
│   │   ├── images/                  # Diagrams, screenshots
│   │   └── assets/                  # PDFs, slides, misc
│   │
│   ├── wiki/                        # Layer 2: Compiled knowledge
│   │   ├── index.md                 # Master catalog (updated on every operation)
│   │   ├── log.md                   # Append-only operation log
│   │   ├── hot.md                   # Session context cache
│   │   ├── overview.md              # Executive summary
│   │   ├── concepts/               # Technical concepts, algorithms
│   │   ├── entities/               # People, orgs, projects
│   │   ├── sources/                # Summaries of ingested raw docs
│   │   ├── comparisons/            # Side-by-side analyses
│   │   └── meta/                   # Dashboards, health reports
│   │
│   ├── outputs/                     # Generated reports, lint results
│   │
│   ├── _templates/                  # Obsidian note templates
│   │   ├── concept.md
│   │   ├── entity.md
│   │   ├── source-summary.md
│   │   └── comparison.md
│   │
│   └── .obsidian/
│       └── snippets/
│           └── vault-colors.css     # Color-coded file explorer
│
└── README.md
```

---

## Installation

### Prerequisites

- [Obsidian](https://obsidian.md) (free)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic CLI)
- Python 3.10+
- Git

### Quick start — let Claude set it up for you

After cloning, the fastest path is to let Claude Code drive the install:

```bash
git clone https://github.com/rvmonterde003/obsidian-llm-palace.git
cd obsidian-llm-palace
claude            # opens Claude Code in this repo
```

Then in Claude Code, type:

```
/setup
```

This invokes the project-level `setup.md` slash command. Claude reads it as a playbook and walks you through every step interactively — installing dependencies, initializing the palace, optional backfill of `~/.claude/projects/` history, registering the MCP server, and merging hooks (Stop, PreCompact, SessionStart) into your `~/.claude/settings.json` (with backup). Once it finishes you'll have:

- `/setup` — re-run the playbook (re-entrant by design; safe to run twice)
- `/save` — distill the current session into MemPalace + refresh `wiki/hot.md` and `wiki/log.md`
- `/recall` — with no args: resume the last session. With args: semantic search across MemPalace.

Skip to step "Open in Obsidian" below once it's done.

If you'd rather do it manually, the rest of this section walks through the same steps. Pick whichever you prefer.

### Step 1: Clone the repository

```bash
git clone https://github.com/rvmonterde003/obsidian-llm-palace.git
cd obsidian-llm-palace
```

### Step 2: Open in Obsidian

1. Open Obsidian
2. Click **Manage Vaults** (vault icon, bottom left)
3. Click **Open folder as vault**
4. Select the `obsidian-llm-palace/` directory inside the cloned repo

### Step 3: Enable the CSS snippet

1. In Obsidian, go to **Settings > Appearance**
2. Scroll to **CSS Snippets**
3. Toggle on `vault-colors`

This color-codes your file explorer: blue for concepts, purple for entities, green for sources, orange for comparisons.

### Step 4: Install MemPalace

```bash
pip install mempalace
```

### Step 5: Initialize MemPalace in the vault

```bash
# Navigate to the vault directory
cd obsidian-llm-palace/

# Initialize — detects entities and sets up the palace structure
mempalace init .

# Run the first mine to ingest existing vault content
mempalace mine .
```

> **Windows users**: If you get a `UnicodeEncodeError`, prefix with:
> ```bash
> set PYTHONIOENCODING=utf-8
> mempalace init . --yes
> ```

### Step 6: Add MemPalace MCP server to Claude Code

This gives Claude Code direct access to MemPalace's 29 tools (search, add drawer, knowledge graph, diary, etc.):

```bash
claude mcp add mempalace -- python -m mempalace.mcp_server
```

> **Windows users**: You may need to specify the full Python path:
> ```bash
> claude mcp add mempalace -- "C:\Python313\python.exe" -m mempalace.mcp_server
> ```

### Step 7: (Optional) Wire auto-save + wake-up hooks

Add these to your user-global `~/.claude/settings.json` so every Claude Code session in *any* project auto-saves to MemPalace, and so each session boots with wake-up context from the relevant wing:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python -m mempalace hook run --hook stop --harness claude-code",
            "timeout": 30
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m mempalace hook run --hook precompact --harness claude-code",
            "timeout": 30
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python <ABSOLUTE_PATH_TO_REPO>/scripts/session_start_hook.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

Replace `<ABSOLUTE_PATH_TO_REPO>` with the absolute path returned by:

```bash
python -c "from pathlib import Path; print((Path.cwd() / 'scripts' / 'session_start_hook.py').resolve())"
```

The SessionStart hook injects ~600–900 tokens of wake-up context (the relevant MemPalace wing's recent drawers) into Claude's initial context window. Wings prefixed `_archive_` are auto-skipped via `scripts/wake_up_skip_prefixes.txt`.

> **Save Behavior in this vault**: the per-turn Stop save is intentionally deferred — Claude only saves at session end, on explicit `/save`, when you say a pause-phrase ("let's wrap this up", "I'll resume later"), or when PreCompact fires. See `obsidian-llm-palace/CLAUDE.md` → *Save Behavior* for the rationale (keeps costs low without losing context).

### Step 8: Restart Claude Code

```bash
# Close and reopen Claude Code to activate the MCP server and hooks
claude
```

### Step 9: First-session smoke test

In a fresh Claude Code session inside this repo, type:

```
/recall
```

With no args, `/recall` reads `wiki/hot.md` + the last `wiki/log.md` entry + recent MemPalace diary entries to resume the previous session. On a fresh install this will report an empty palace — confirming the wiring works end-to-end before you start accumulating real history.

When you're done for the day, type:

```
/save
```

This distills the conversation into a MemPalace diary entry, one or more focused drawers, and refreshes `wiki/hot.md` + appends to `wiki/log.md`. Next session, `/recall` (or just asking "where did we leave off?") will pick up where you stopped.

---

## Usage

### Ingesting sources

Drop files into the appropriate `raw/` subfolder, then tell Claude:

```
I added 3 papers to raw/papers/. Ingest them all.
```

Claude will:
1. Read each source
2. Create wiki summary pages in `wiki/sources/`
3. Create or update concept and entity pages
4. Add `[[wikilinks]]` between related pages
5. Update `wiki/index.md` and `wiki/log.md`

### Querying your knowledge base

```
What do I know about inverse kinematics?
```

Claude navigates `wiki/index.md` to find relevant pages, reads them, and synthesizes an answer with `[[wikilink]]` citations.

### Linting the wiki

```
Lint the wiki. Focus on contradictions and missing pages.
```

Claude scans all pages and produces a health report in `outputs/`.

### Saving session context

```
/save
```

Or just tell Claude any pause-phrase like *"let's wrap this up"*, *"I'll resume later"*, or *"save what we have"*. Claude distills the session into a MemPalace diary entry, one or more focused drawers, and refreshes `wiki/hot.md` + appends to `wiki/log.md`.

### Resuming a prior session

```
/recall
```

With no args, reads `wiki/hot.md` + the last `wiki/log.md` entry + recent MemPalace diary entries and reports what was decided, what's open, and the best next step. Equivalent to asking *"where did we leave off?"*.

### Searching conversation history (via MemPalace)

```
/recall <query>
```

With args, performs a semantic search across MemPalace and returns the top matches with drawer IDs you can drill into. Or just ask Claude directly:

```
Search MemPalace for the conversation where we decided on the sensor array layout.
```

---

## How the Combined Pipeline Improves on Each System Alone

### Karpathy's LLM Wiki alone

Compiles knowledge beautifully, but:
- No conversation memory between sessions
- No semantic search over past discussions
- No visual navigation (just files)

### MemPalace alone

Stores and retrieves conversations, but:
- No structured knowledge compilation
- No cross-referencing between concepts
- No visual graph of how ideas connect

### Combined (this pipeline)

- **Compiled knowledge** (wiki) for what you *know*
- **Raw recall** (MemPalace) for what you *discussed*
- **Visual navigation** (Obsidian) for how it all *connects*
- **Session continuity** (hot.md + auto-save hooks) so nothing is lost
- **Token efficiency** — Claude reads 3-5 wiki pages instead of searching the entire corpus; MemPalace returns only relevant drawers via semantic search

---

## Projected Performance

Estimates based on [MemPalace's published benchmarks](https://github.com/MemPalace/mempalace/tree/main/benchmarks) (96.6% R@5 on LongMemEval, 600-900 token wake-up cost) and the LLM Wiki pattern's architectural properties. These are projections, not guarantees — actual results depend on usage patterns and wiki maturity.

### Token Efficiency Per Session

The combined pipeline routes queries to the cheapest layer that can answer them. Knowledge questions hit the wiki (pre-compiled pages). Conversation recall hits MemPalace (semantic search). Neither re-derives from raw sources.

```
                           Without pipeline       With pipeline
───────────────────────────────────────────────────────────────────
Session startup            0 tokens (cold)        600-900 tokens (hot.md + wake-up)
Knowledge query            2,000-5,000 tokens     1,500-3,000 tokens (wiki pages)
Conversation recall        Impossible (no memory) ~500-1,000 tokens (MemPalace search)
Source re-reading           Full doc every time    Read once → wiki page persists
───────────────────────────────────────────────────────────────────
Est. token savings/query:  ~30-50%
Est. savings/session (10 queries): ~40-60%
```

The largest savings come from **avoiding re-reading raw sources**. A 20-page paper costs ~15,000 tokens every time RAG retrieves it. A pre-compiled wiki summary costs ~500 tokens and is written once.

### Cost Projection (Annual, Assuming Daily Use)

```
                           Standard RAG    MemPalace alone    Combined pipeline
────────────────────────────────────────────────────────────────────────────────
Wake-up / session          $0              ~$0.70/year        ~$0.70/year
Search / retrieval         $200-500/year   ~$10/year          ~$10/year
LLM calls for queries      $300-800/year   $300-800/year      $150-400/year
Vector DB hosting          $50-200/year    $0 (local)         $0 (local)
────────────────────────────────────────────────────────────────────────────────
Estimated total            $550-1,500/yr   $310-810/yr        $160-410/yr
```

**Estimated savings over standard RAG: ~60-75%.** The wiki layer eliminates repeated LLM re-derivation for compiled knowledge. MemPalace eliminates cloud vector DB costs by running entirely locally (ChromaDB + all-MiniLM-L6-v2 embeddings, ~79MB on disk, zero API calls).

### Session Continuity

This is where neither system alone comes close to the combined pipeline.

```
                           Wiki alone       MemPalace alone    Combined pipeline
─────────────────────────────────────────────────────────────────────────────────
Context carried to         0%               ~96.6% of          ~96.6% conversations
 next session                               conversations      + 100% compiled knowledge
                                                               + hot.md recent context

Time to productive start   5-10 min         1-2 min            <30 seconds
 (re-establishing context) (re-explain       (wake-up call)     (hot.md + wake-up)
                           everything)
─────────────────────────────────────────────────────────────────────────────────
```

Without memory, every session starts cold — you re-explain your project, your decisions, your terminology. With the combined pipeline, `hot.md` gives the last session's context in ~600 tokens, the wiki gives all compiled knowledge, and MemPalace gives verbatim recall of any past conversation.

### Caveats

- MemPalace's 96.6% R@5 is measured on [LongMemEval](https://github.com/MemPalace/mempalace/tree/main/benchmarks) with 500 questions in raw verbatim mode. AAAK compressed mode scores 84.2%.
- The +34% palace structure boost [was acknowledged by MemPalace's authors](https://github.com/MemPalace/mempalace#honest-corrections-april-2026) as comparing filtered vs unfiltered search — a standard feature, not a novel improvement.
- Wiki retrieval accuracy (~95-100%) assumes the index is maintained and pages are current. A stale wiki degrades this.
- Token and cost savings compound over time — a new vault with few sources will show smaller gains than a mature one with 50-200 ingested sources.
- All MemPalace operations run locally with zero API calls. The cost projections for the LLM layer assume Claude Code usage.

---

## Recommended Obsidian Plugins

These are optional but improve the experience:

| Plugin | What It Does |
|---|---|
| **Templater** | Auto-fills frontmatter in new notes using `_templates/` |
| **Obsidian Git** | Auto-commits vault changes every 15 minutes |
| **Dataview** | Query wiki pages like a database (e.g., "show all low-confidence concepts") |
| **Calendar** | Sidebar calendar with daily note word counts |

Install via: **Settings > Community Plugins > Browse**

### Example Dataview query

Add this to any note to surface pages that need attention:

````markdown
```dataview
TABLE type, confidence, updated
FROM "wiki"
WHERE confidence = "low"
SORT updated ASC
```
````

---

## Wiki Page Conventions

Every wiki page uses YAML frontmatter:

```yaml
---
title: Page Title
type: concept | entity | source-summary | comparison
sources:
  - raw/papers/filename.md
related:
  - "[[related-concept]]"
created: 2026-04-16
updated: 2026-04-16
confidence: high | medium | low
tags:
  - robotics
  - ai
---
```

- **Filenames**: `kebab-case` (e.g., `inverse-kinematics.md`)
- **Cross-references**: `[[wikilinks]]` for internal links
- **Confidence**: `high` = verified from multiple sources, `medium` = single source, `low` = speculative

---

## Contributing

This is an evolving pipeline. Contributions welcome:

1. Fork the repo
2. Create a feature branch
3. Submit a PR with a clear description

Ideas for contribution:
- Additional `_templates/` for new page types
- Dataview dashboard templates
- Obsidian Canvas layouts for visual knowledge mapping
- Scripts for batch-ingesting sources
- Integration with other AI coding agents (Cursor, Codex CLI)

---

## Credits & Acknowledgments

This project stands on the shoulders of two open-source projects:

### Andrej Karpathy — LLM Wiki Pattern

The foundational architecture — the three-layer model (raw/wiki/schema), the ingest/query/lint workflow, and the core insight that **compilation beats retrieval** for personal knowledge management — comes from Andrej Karpathy's [LLM Knowledge Bases](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) gist (April 2026).

Karpathy is the co-founder of OpenAI, former Director of AI at Tesla, and founder of [Eureka Labs](https://eurekalabs.ai). His work on AI education and practical LLM patterns continues to shape how the community builds with these tools.

### MemPalace — AI Memory System

The conversation memory layer — verbatim storage, semantic search via ChromaDB, the palace hierarchy (wings/rooms/drawers/tunnels), temporal knowledge graph, auto-save hooks, and the 29-tool MCP server — comes from [MemPalace](https://github.com/MemPalace/mempalace) (MIT License, v3.3.0).

MemPalace provides the raw recall that the wiki pattern alone cannot: 96.6% R@5 on LongMemEval with zero API calls, entirely local-first.

### Obsidian

[Obsidian](https://obsidian.md) provides the visual layer — graph view, backlinks, community plugins, and a local-first markdown editor that makes the compiled knowledge navigable by humans.

---

## License

MIT — see [LICENSE](LICENSE).

Third-party licenses (MemPalace) — see [THIRD-PARTY-LICENSES](THIRD-PARTY-LICENSES).

---

*Built with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic.*
