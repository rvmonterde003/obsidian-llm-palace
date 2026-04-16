# Research Wiki: Mel Robotics & AI

## Project Structure

- `raw/` — Immutable source documents. **Never modify files here.**
  - `raw/articles/` — Web articles, blog posts, news clippings
  - `raw/papers/` — Academic papers, whitepapers, technical reports
  - `raw/repos/` — Code snippets, README excerpts, repo notes
  - `raw/data/` — Datasets, CSV, JSON data files
  - `raw/images/` — Diagrams, photos, screenshots
  - `raw/assets/` — Misc files (PDFs, slides, etc.)
- `wiki/` — LLM-generated and maintained markdown pages.
  - `wiki/concepts/` — Technical concepts, algorithms, methodologies
  - `wiki/entities/` — People, organizations, products, projects
  - `wiki/sources/` — Summaries of ingested raw sources
  - `wiki/comparisons/` — Side-by-side analyses
  - `wiki/meta/` — Dashboards, health reports
- `wiki/index.md` — Master content catalog. **Update on every ingest/edit.**
- `wiki/log.md` — Append-only operation log.
- `wiki/hot.md` — Recent context cache (last session's key takeaways).
- `wiki/overview.md` — High-level executive summary of the wiki's scope.
- `outputs/` — Generated reports, lint results, presentations.
- `_templates/` — Obsidian note templates.
- `raw/` is the verification baseline. `wiki/` is the compiled knowledge.

## Page Conventions

Every wiki page MUST have YAML frontmatter:

```yaml
---
title: Page Title
type: concept | entity | source-summary | comparison
sources:
  - raw/papers/filename.md
related:
  - "[[related-concept]]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high | medium | low
tags:
  - robotics
  - ai
---
```

### Naming
- Filenames: `kebab-case` matching the concept (e.g., `simultaneous-localization-and-mapping.md`)
- Cross-references: use `[[wikilinks]]` for internal links
- Source references: always link back to `raw/` file paths
- Entities: use full names (e.g., `andrej-karpathy.md`, not `karpathy.md`)

### Linking Rules
- Every wiki page must link to at least one other wiki page
- Every source summary must link to its raw source path
- Use `[[wikilinks]]` not markdown links for internal references
- Tag pages with relevant topics for Obsidian graph clustering

## Workflows

### Ingest

When the user adds sources to `raw/` and asks to ingest:

1. Read the source document(s) in `raw/`
2. Discuss key takeaways with the user
3. Create `wiki/sources/<source-name>.md` summary with frontmatter
4. Update or create concept pages in `wiki/concepts/` as needed
5. Update or create entity pages in `wiki/entities/` as needed
6. Add `[[wikilinks]]` between all related pages (both directions)
7. Update `wiki/index.md` with new entries under the right categories
8. Append to `wiki/log.md` with format: `## [YYYY-MM-DD] ingest | <title>`
9. Update `wiki/hot.md` with the session's key context

### Query

When the user asks a question about wiki content:

1. Read `wiki/hot.md` first (recent context cache)
2. Read `wiki/index.md` to identify relevant pages
3. Read those pages and synthesize an answer
4. Cite sources using `[[wikilinks]]`
5. If the answer is valuable, offer to save as a new wiki page

### Lint

When asked to lint or health-check the wiki:

1. Scan all wiki pages for contradictions between pages
2. Identify orphan pages (no incoming `[[wikilinks]]`)
3. Flag referenced concepts that don't have their own page yet
4. Find stale claims superseded by newer sources
5. Check all raw source references still exist
6. Save results to `outputs/lint-YYYY-MM-DD.md`
7. Append to `wiki/log.md`

### Save (Session End)

Before ending a session or when asked to save:

1. Update `wiki/hot.md` with key topics, decisions, and context from this session
2. Update any wiki pages that were discussed or modified
3. Append session summary to `wiki/log.md`

## MemPalace Integration

This vault is paired with MemPalace for conversation memory. The wiki handles
structured knowledge; MemPalace handles verbatim conversation recall.

- Wiki = compiled knowledge (what we know)
- MemPalace = raw memory (what we discussed)
- When ingesting, file structured knowledge in the wiki AND key facts in MemPalace
- When querying, check wiki first, fall back to MemPalace for conversation history
- MemPalace wings map to wiki categories:
  - `wing_robotics` — robotics hardware, kinematics, control systems
  - `wing_ai` — machine learning, LLMs, computer vision
  - `wing_projects` — active project work, experiments, builds

## Quality Standards

- **Confidence levels**: Mark every page. `high` = verified from multiple sources. `medium` = single source or reasonable inference. `low` = speculative or unverified.
- **No hallucination**: If a fact isn't in the sources, don't add it to the wiki. Say "not covered in current sources" instead.
- **Verbatim quotes**: When a source makes a key claim, include the exact quote in the source summary.
- **Atomic pages**: One concept per page. If a page covers two distinct ideas, split it.
