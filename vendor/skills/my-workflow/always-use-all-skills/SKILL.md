---
name: always-use-all-skills
description: Light master controller. Always apply. Enforces voice trio, forced project-memory, judgment-based Advisor (Task inherit / session allowlist), and a tiny conditional catalog (design, coding, SEO, browser, thermos review, subagent-creator).
---

# Always Use All Skills (Light)

## Trinity

| Component | Path |
|-----------|------|
| Rule | `~/.cursor/plugins/local/always-use-all-skills/rules/always-use-all-skills.mdc` |
| Skill | installed at `~/.cursor/skills/my-workflow/always-use-all-skills/SKILL.md` |
| Plugin | `~/.cursor/plugins/local/always-use-all-skills/` |

## Always apply

Controller + humanizer-stack (humanizer + structural-humanizer) + human-voice-rewrite + unslop + **project-memory**.


## HEADROOM FORCE (always on)

1. Headroom MCP + local proxy are mandatory every session.
2. Call `headroom_compress` before reasoning on large tool/file/log/JSON output.
3. Call `headroom_retrieve` by hash when full originals are needed; `headroom_stats` for health/savings.
4. Never skip Headroom. Do not write `headroom learn` into `.cursor/rules`.
5. See `~/Projects/cursor-master-controller-light/config/headroom/`.

## Advisor (Layer B, judgment)

1. Do not auto-enable. Reason about whether a second opinion helps, then consult only when it does.
2. Consult at stock checkpoints: before a major decision, when stuck, before declaring done. One-off on request.
3. When consulting, omit Task `model` or pass `inherit` unless the user names a slug from this session's Task `available_subagent_models`. If Task rejects a slug, use `inherit` and say so in one line. No model-pool file.
4. Never put Advisor in the catalog indexes.

## Subagents

1. Use only Task `subagent_type` values listed this session.
2. Omit `model` or pass `inherit` unless the user names a Task-accepted slug.
3. After creating `.cursor/agents/<name>.md`, tell the user to Reload Window before Task can use that name.
4. Until reload, use stock or plugin types (`generalPurpose`, `explore`, `advisor-subagent`, etc.).

See `~/Projects/cursor-master-controller-light/config/advisor/`.

## Conditionals (light only)

| catalog_id | Role |
|------------|------|
| design-taste-frontend | Reference/vibe-driven UI |
| design/anthropics/frontend-design | Distinctive art direction |
| ui-ux-pro-max | Design lookup brain |
| image-to-code | Image-first comps -> code |
| design/addyosmani/browser-testing-with-devtools | Browser verify |
| seo-mastery | SEO / schema / CWV |
| ponytail (plugin) | Simplest correct code |
| cursor-team-kit (plugin) | Team engineering standards |
| thermos (plugin) | Deep PR/security/quality review only |
| advisor (plugin) | Second opinion at a major decision, when stuck, or before done |
| cursor-subagent-creator | Build a custom Cursor subagent under `.cursor/agents/` |

## PROJECT MEMORY FORCE

Create/read/update `.cursor/memory/` every workspace. See project-memory skill/rule.

Prefer Advisor `nudge: false` so the plugin stays available without stop-hook spam; consult only when useful.
