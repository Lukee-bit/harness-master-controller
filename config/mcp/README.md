# Layer B — MCP, Headroom, and Advisor (not skill-catalog entries)

These upgrade Cursor without bloating the light skill index.

## Headroom (ALWAYS REQUIRED)

Token compression is force-enabled for light/fat/live Cursor:

1. **MCP** — `headroom` server (`headroom_compress`, `headroom_retrieve`, `headroom_stats`)
2. **Proxy** — local Headroom proxy kept running; Cursor Override OpenAI Base URL points at it
3. **HEADROOM FORCE** — hooks/rules require using compress/retrieve; never skip for convenience

Run `scripts/setup-headroom.sh` (also invoked by `install.sh`). See `config/headroom/README.md`.

Snippet: `headroom.json`. Also listed in `mcp-light-recommended.json`.

**Do not** enable `headroom learn` writing into `.cursor/rules` (conflicts with humanizer-stack / always-use-all-skills / project-memory). Project memory stays `.cursor/memory/`.

## Other MCP snippets

Merge the JSON under `mcpServers` into your Cursor MCP config (Cursor Settings → MCP), or copy fields from:

- `context7.json` — up-to-date library docs
- `awwwards.json` — award-site design references / DNA
- `github.json` — structured GitHub Issues/PRs/checks
- `headroom.json` — **required** compression / retrieve / stats

Light install writes `~/.cursor/mcp-light-recommended.json`. `setup-headroom.sh` also merges Headroom into live `~/.cursor/mcp.json` when present.

## Advisor (judgment-based)

Advisor is judgment-based (never auto-enabled). Use Task `inherit` or a session-accepted slug. No model-pool file. See `config/advisor/README.md`.

## When to use

| Tool | Use when |
|------|----------|
| **Headroom** | **Always** (forced). Compress tool/file/log/JSON before heavy reasoning; retrieve by hash when needed. |
| Context7 | Implementing against a library/API |
| Awwwards MCP | Designing from award-winning references |
| GitHub MCP | Heavy Issues/PR/check automation |
| Advisor | Need a strong second opinion |
| Playwright MCP | Not in light edition (use Cursor browser + browser-testing skill) |
