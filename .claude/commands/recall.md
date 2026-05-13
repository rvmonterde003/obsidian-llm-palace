---
description: With no args, resume the last session (hot.md + last log entry + recent diary). With args, semantic search across MemPalace.
---

The user typed `/recall`. Branch on arguments.

---

## Mode A — Session resumption (no args)

The user wants to know "what was the latest, what's next."

1. Read `obsidian-llm-palace/obsidian-llm-palace/wiki/hot.md` in full.
2. Read `obsidian-llm-palace/obsidian-llm-palace/wiki/log.md` — only the most recent `## [...]` block.
3. Call `mempalace_diary_read` with `agent_name="Claude"`, `last_n=3` for finer-grained recall.

Report to the user in this structure:

```
**Last session** ({date}): {one-line title from hot.md}

**What changed:**
- bullets from hot.md

**Open threads:**
- bullets from hot.md

**Best next steps:**
1. numbered items from hot.md
```

If hot.md is stale (date > 7 days old), flag that to the user.

---

## Mode B — Semantic search (with args)

The user wants to find a specific past conversation.

1. Call `mempalace_search`:
   - `query`: the user's query string (max 250 chars, keywords only)
   - `limit`: 5 by default
   - `wing`: filter if the user specified one (e.g., `/recall in betaflight: msp packet loss`)
2. For each result, show:
   - Drawer ID
   - Wing / room
   - Content preview (first ~150 chars)
   - Similarity score
3. Offer: "Want me to fetch the full content of any of these? Reply with the drawer ID."
4. On follow-up, call `mempalace_get_drawer` with the chosen ID.

Cite drawer IDs in your response so the user can verify.

---

## Edge cases

- Empty palace or no matches → tell the user clearly, don't fabricate.
- hot.md missing or empty → tell the user the vault hasn't been initialized for session continuity.
- Multiple wings present → in mode A, only resume from `obsidian-llm-palace`. In mode B, search all wings unless filtered.
