---
title: MemPalace
type: concept
sources:
  - "https://github.com/MemPalace/mempalace"
related:
  - "[[LLM Wiki Pattern]]"
created: 2026-04-16
updated: 2026-04-16
confidence: high
tags:
  - memory
  - ai
  - tools
---

# MemPalace

An open-source AI memory system that stores conversations verbatim and makes them searchable via semantic search. Sits on top of the [[LLM Wiki Pattern]].

## Architecture

Uses a hierarchical "palace" metaphor inspired by the ancient method of loci:

- **Wings** — Individual people or projects
- **Rooms** — Specific topics within wings
- **Halls** — Connection types (facts, events, discoveries, preferences, advice)
- **Closets** — Summary pointers to original content
- **Drawers** — Verbatim original text
- **Tunnels** — Cross-wing connections linking same topics across domains

## Technical Stack

- **Storage**: ChromaDB (semantic search) + SQLite (entity relationships)
- **Integration**: MCP server with 29 tools for reads/writes
- **Hooks**: Auto-save every 15 messages + pre-compaction emergency save
- **Knowledge Graph**: Temporal entity-relationship triples with validity windows

## How It Complements the Wiki

| Layer | What It Stores | Format |
|-------|---------------|--------|
| Wiki | Compiled knowledge | Structured markdown with wikilinks |
| MemPalace | Raw conversation memory | Verbatim text in vector DB |

The wiki is what we *know*. MemPalace is what we *discussed*.

## Related Concepts

- [[LLM Wiki Pattern]] — The foundation this builds on
