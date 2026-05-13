---
description: Save the current session — diary entry, focused drawers, hot.md refresh, log.md append. Use at session end or when pausing work.
---

You are saving the current session. Walk through this in order. Be concise — one assistant turn, no narration between steps.

## Step 1 — Distill

Skim the conversation. Identify:
- The 1–3 most important takeaways (decisions, discoveries, corrections, blockers)
- New entities, concepts, or relationships worth pinning
- Open threads / unresolved questions
- Best next steps for the user

Skip noise: routine tool calls, syntactic back-and-forth, navigation.

## Step 2 — Diary entry

Call `mempalace_diary_write`:
- `agent_name`: "Claude"
- `topic`: short slug for the session focus (e.g., `vault-cleanup-2026-05-09`)
- `entry`: AAAK-compressed summary. Cover what was discussed, what was decided, open items. Mark importance ★ to ★★★★★.

## Step 3 — Focused drawers

For each major topic from step 1, call `mempalace_add_drawer`:
- `wing`: read from `obsidian-llm-palace/obsidian-llm-palace/CLAUDE.md` "MemPalace" section. Default `obsidian-llm-palace`.
- `room`: short kebab-case slug of the topic — one room per topic
- `content`: verbatim, full prose — the drawer is the receipt, do not abbreviate
- `source_file`: `conversation-YYYY-MM-DD`

Aim for 1–3 drawers. Don't bundle unrelated topics.

## Step 4 — Refresh hot.md

Overwrite `obsidian-llm-palace/obsidian-llm-palace/wiki/hot.md`. Structure:

```markdown
---
title: Hot Cache
type: meta
created: <preserve original>
updated: <today>
---

# Hot Cache

Recent context from the last session. Read this first for continuity.

---

## Last Session: YYYY-MM-DD — <one-line title>

- 3–5 bullets of what changed / was decided

## Open Threads

- bullets

## Best Next Steps

1. numbered items
```

Keep under ~600 tokens. This file is read at every session start.

## Step 5 — Append to log.md

Append to `obsidian-llm-palace/obsidian-llm-palace/wiki/log.md`:

```markdown
## [YYYY-MM-DD] <op-type> | <short title>

- bullet 1
- bullet 2
```

`op-type` is one of: `ingest`, `reset`, `save`, `lint`, `meta`, `refactor`, `decision`.

## Step 6 — Optional KG triples

If durable entity facts emerged (e.g., "User chose PX4 for project X"), call `mempalace_kg_add` for each. Skip for purely conceptual discussions.

## Step 7 — Report

3-line summary back to the user:
- Diary entry: written (topic)
- Drawers: N saved (list room names)
- hot.md + log.md: updated
