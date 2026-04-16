---
title: Wiki Overview
type: meta
created: 2026-04-16
updated: 2026-04-16
---

# Mel Robotics & AI — Wiki Overview

A personal knowledge base covering robotics, artificial intelligence, and related projects. Built on [[Andrej Karpathy]]'s LLM Wiki pattern — structured markdown maintained by Claude Code, browsed through Obsidian.

## Scope

- **Robotics**: hardware, kinematics, control systems, sensors, actuators, ROS
- **AI/ML**: large language models, computer vision, reinforcement learning, embeddings
- **Projects**: active builds, experiments, prototypes
- **Tools**: frameworks, libraries, platforms used in the work

## Architecture

```
raw/        → Immutable sources (the truth)
wiki/       → Compiled knowledge (the understanding)
outputs/    → Generated artifacts (reports, analyses)
MemPalace   → Conversation memory (what we discussed)
```

## How to Use

1. Drop sources into `raw/` and ask Claude to ingest
2. Ask questions — Claude synthesizes answers from wiki pages
3. Browse the graph in Obsidian to discover connections
4. Run lint periodically to catch gaps and contradictions
