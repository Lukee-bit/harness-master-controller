---
name: project-memory
description: Forced workspace memory. Always apply. Create and continuously update .cursor/memory/ (project, activeContext, progress, decisions, research). Merges saving-workspace-context habits and Memory Bank file schema without Memory Bank modes.
---

# Project Memory

## Paths

| Role | Path |
|------|------|
| Rule | `~/.cursor/rules/project-memory.mdc` |
| Skill | `~/.cursor/skills/my-workflow/project-memory/SKILL.md` |
| Templates | `~/Projects/cursor-master-controller-light/templates/memory/` (or installed package templates) |

## Layout

```text
.cursor/memory/
  project.md
  activeContext.md
  progress.md
  decisions.md
  research/
```

## Protocol

1. Create tree if missing; seed from templates.
2. Before non-trivial work: Read core three files.
3. Write durable facts immediately.
4. After progress: update `activeContext.md`; append dated `progress.md` / `decisions.md`.
5. Never store secrets.
6. Before ending: memory pass (or append `no durable updates`).
7. Single system only — no Memory Bank modes, no parallel `context/` memory.

## Dated entry format

```markdown
## YYYY-MM-DD — short title

What was learned, decided, or completed.
```

Newest entries go at the top of `progress.md` and `decisions.md`.
