---
title: Brain Dump Protocol
type: meta
related:
  - "[[index]]"
  - "[[mempalace]]"
  - "[[llm-wiki-pattern]]"
created: 2026-04-16
updated: 2026-04-16
confidence: high
tags:
  - workflow
  - protocol
  - voice-dictation
---

# Brain Dump Protocol

Routing rules for free-form text (voice dictation, quick thoughts, paste-ins). When the user pastes raw text into the terminal with a trigger phrase, follow this protocol exactly.

---

## Trigger phrases and routing

| Trigger | Destination | Behavior |
|---|---|---|
| `brain dump:` | MemPalace (verbatim) + wiki (extracted concepts) | Store full text in a MemPalace drawer. Extract any concrete entities/concepts and create or update wiki pages. |
| `thought:` | MemPalace only | Store verbatim in a drawer. Do not create wiki pages. |
| `ingest:` | Wiki (full treatment) | Create/update concept and entity pages with `[[wikilinks]]`. Update `index.md` and `log.md`. |
| `journal:` | `wiki/hot.md` or daily note | Append to session context. No permanent wiki page unless explicitly asked. |
| `save this as <type>` | Specific wiki folder | User directs the routing (concept/entity/source/comparison). |
| `update <page>` | Named wiki page | Edit that specific page only. |

If no trigger is given, infer intent: short reflective text → `thought:`, structured knowledge → `ingest:`, mixed → `brain dump:`.

---

## Routing decision tree

When processing a dump:

1. **Is it a person, org, or project?** → `wiki/entities/`
2. **Is it a technical concept, algorithm, or pattern?** → `wiki/concepts/`
3. **Does it reference a raw source the user already added?** → `wiki/sources/` + link to `raw/`
4. **Is it comparing two things?** → `wiki/comparisons/`
5. **Is it a fleeting thought with no durable content?** → MemPalace drawer only
6. **Is it mixed?** → MemPalace verbatim + extract durable pieces into wiki

---

## File creation rules

- **Filename**: `kebab-case.md` derived from the main subject
- **Frontmatter**: required on every new page (see `_templates/`)
- **Confidence**:
  - `high` if multiple sources agree or user stated as fact
  - `medium` if single source or single dump
  - `low` if speculative or user expressed uncertainty
- **Cross-references**: add `[[wikilinks]]` to every related existing page
- **Bookkeeping**: always update `wiki/index.md` (add row) and `wiki/log.md` (append entry)

---

## MemPalace routing (when MCP server active)

Use `mempalace_add_drawer` with:
- **Wing**: infer from content (`wing_robotics`, `wing_ai`, `wing_projects`, or user-specified)
- **Content**: verbatim paste from user
- **Tags**: extract 2-5 topic tags from the dump

For `brain dump:` triggers, also record the resulting wiki page paths in the drawer's metadata so the two layers stay linked.

---

## What NOT to do

- Do not paraphrase or edit the user's words when storing in MemPalace — verbatim only
- Do not create wiki pages for transient thoughts (use MemPalace)
- Do not skip `index.md` / `log.md` updates
- Do not guess entity names — if ambiguous, ask once before filing
- Do not file into multiple wings/folders "just in case" — pick one primary home, link from others

---

## Example flows

### Brain dump

**User**: `brain dump: was thinking about how inverse kinematics for a 6DOF arm could use a Jacobian transpose approach instead of pseudo-inverse when near singularities. Also need to email Dr. Chen about the calibration rig.`

**Claude**:
1. Store full text in MemPalace drawer under `wing_robotics`
2. Create/update `wiki/concepts/inverse-kinematics.md` with Jacobian transpose note
3. Create/update `wiki/entities/dr-chen.md` (if not exists) with calibration rig context
4. Update `index.md` and `log.md`
5. Note the TODO about emailing Dr. Chen in `hot.md`

### Thought

**User**: `thought: maybe the whole sensor fusion problem is just a Kalman filter with bad priors`

**Claude**: Store verbatim in MemPalace drawer. No wiki pages created.

### Ingest

**User**: `ingest: MoveIt 2 is ROS 2's motion planning framework. Uses OMPL for sampling-based planners. Replaces MoveIt 1 which was ROS 1 only.`

**Claude**:
1. Create `wiki/concepts/moveit-2.md` with frontmatter, links to `[[ros-2]]`, `[[ompl]]`, `[[moveit-1]]`
2. Create stub pages for any missing linked concepts
3. Update `index.md` and `log.md`
