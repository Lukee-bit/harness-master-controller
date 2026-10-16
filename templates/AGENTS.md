# AGENTS.md

## Project memory (forced)

Durable knowledge lives in `.cursor/memory/`:

| File | Purpose |
|------|---------|
| `project.md` | Stable identity, stack, constraints |
| `activeContext.md` | Current goal and open questions |
| `progress.md` | Dated append-only progress log |
| `decisions.md` | Dated append-only decisions |
| `research/` | Topic research notes |

Before non-trivial work: Read the core memory files. During and after work: update them. Never store secrets.

This is the only memory system for this workspace. Do not create parallel Memory Bank or `context/` trees.
