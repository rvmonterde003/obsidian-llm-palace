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
├── llm-palace/                    # Obsidian vault root
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
- Python 3.9+
- Git

### Step 1: Clone the repository

```bash
git clone https://github.com/rvmonterde003/obsidian-llm-palace.git
cd obsidian-llm-palace
```

### Step 2: Open in Obsidian

1. Open Obsidian
2. Click **Manage Vaults** (vault icon, bottom left)
3. Click **Open folder as vault**
4. Select the `llm-palace/` directory inside the cloned repo

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
cd llm-palace/

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

### Step 7: (Optional) Wire auto-save hooks

Add these to your `.claude/settings.local.json` to automatically save conversations to MemPalace:

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
    ]
  }
}
```

### Step 8: Restart Claude Code

```bash
# Close and reopen Claude Code to activate the MCP server
claude
```

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
Save this session.
```

Updates `wiki/hot.md` with key takeaways so the next session starts with context.

### Searching conversation history (via MemPalace)

If the MCP server is active, Claude can use MemPalace tools directly:

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

MIT

---

*Built with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic.*
