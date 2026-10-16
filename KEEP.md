# Keep list — Cursor Master Controller Light

Hard allowlist for **Layer A** (catalog). Layer B (MCP/Advisor) and Layer C (forced memory) sit beside it without bloating indexes.

## Layer A — Always on

| Unit | Paths |
|------|--------|
| Master controller | rule + skill + plugin |
| **humanizer-stack** | rule + skills `humanizer` + `structural-humanizer` + plugin |
| human-voice-rewrite | `my-workflow/human-voice-rewrite` |
| unslop | `my-workflow/unslop` |
| **project-memory** | rule + skill — forced `.cursor/memory/` |

## Layer A — Coding

| Unit | Role |
|------|------|
| ponytail | Simplest correct code |
| cursor-team-kit | TS standards, CI, ship helpers |

## Layer A — Conditionals

| Skill / plugin | Load when |
|----------------|-----------|
| design-taste-frontend | References / landings / portfolios |
| frontend-design | Distinct art direction |
| ui-ux-pro-max | Style / type / palette lookup |
| image-to-code | Comp-first |
| browser-testing-with-devtools | Verify in browser |
| seo-mastery | SEO |
| **thermos** | Deep PR / security / maintainability review only |
| **advisor** | Second opinion at a major decision, when stuck, or before done (judgment, never auto-enabled) |
| **cursor-subagent-creator** | Build a custom Cursor subagent under `.cursor/agents/` |

## Layer B — MCP / Headroom / Advisor (not catalog skills)

| Tool | Role |
|------|------|
| **Headroom (ALWAYS FORCE)** | MCP + local proxy + Override OpenAI Base URL. Compress/retrieve always. See `config/headroom/`. |
| Context7 | Current library docs |
| Awwwards MCP | Award-site design DNA |
| GitHub MCP | Issues / PRs / checks |
| Advisor (judgment-based) | Agent reasons whether a second opinion helps, then consults; never auto-enabled. Task model: omit or `inherit` unless user names a Task-accepted slug. No model-pool file. See `config/advisor/`. |
| Task subagents | Use session Task enum only; custom `.cursor/agents` need Reload Window before `subagent_type` works. |

See `config/mcp/` and `config/headroom/`.

## Layer C — Forced project memory

Workspace root:

```text
.cursor/memory/
  project.md
  activeContext.md
  progress.md
  decisions.md
  research/
```

Create if missing. Read before non-trivial work. Update continuously. Never store secrets. Single memory system (no Memory Bank modes).

## Judgment map

| Task smell | Load |
|------------|------|
| Any reply / copy | humanizer-stack + human-voice-rewrite + unslop |
| Any agent turn | **Headroom FORCE** (MCP compress/retrieve + proxy) |
| New/unknown workspace | project-memory create/read |
| Like Linear / Awwwards URL | design-taste-frontend (+ frontend-design); Awwwards MCP if available |
| Comp-first premium UI | image-to-code |
| Font / style / palette | ui-ux-pro-max |
| Build / simplify | ponytail + team-kit |
| Library/API coding | Context7 MCP |
| SEO | seo-mastery |
| Browser check | browser-testing-with-devtools |
| Deep PR / security review | thermos |
| Hard decision / stuck / before done | Advisor (judgment; consult, never auto-enable) |
| Build a custom Cursor subagent | cursor-subagent-creator |

## Explicitly out

aaron-marketing, writing/*, SEO mega-packs, design aesthetic clones, full Memory Bank modes, standalone saving-workspace-context skill, MengTo/ihlamury bulk packs, Playwright MCP, continual-learning as catalog bulk.
