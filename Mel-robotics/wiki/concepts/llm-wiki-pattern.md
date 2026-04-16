---
title: LLM Wiki Pattern
type: concept
sources:
  - "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
related:
  - "[[Andrej Karpathy]]"
  - "[[MemPalace]]"
created: 2026-04-16
updated: 2026-04-16
confidence: high
tags:
  - knowledge-management
  - llm
  - methodology
---

# LLM Wiki Pattern

A pattern for building persistent, compounding knowledge bases maintained by an LLM agent. Introduced by [[Andrej Karpathy]] in April 2026.

## Summary

Instead of querying raw documents on every request (like RAG), an LLM builds and maintains a structured wiki — a "compiled" knowledge base. The human curates sources; the LLM handles summarization, cross-referencing, and maintenance.

## Three-Layer Architecture

1. **Raw sources** (immutable) — the verification baseline
2. **The wiki** (LLM-maintained) — compiled knowledge with cross-references
3. **The schema** (CLAUDE.md) — rules defining structure and workflows

## Three Core Operations

- **Ingest**: Process new sources, cascade updates across related pages
- **Query**: Navigate via index, synthesize answers with citations
- **Lint**: Health checks for contradictions, orphans, stale claims, gaps

## Key Insight

> "The tedious part of maintaining a knowledge base is not the reading or the thinking — it's the bookkeeping."

LLMs excel at maintenance; humans provide curation and direction.

## Related Concepts

- [[MemPalace]] — Adds conversation memory on top of the wiki layer
