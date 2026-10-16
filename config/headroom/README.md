# Headroom — always-on force (Layer B)

Contract for cursor-master-controller-light, fat, and live `~/.cursor`.

## Always required

1. **CLI** — `headroom` on PATH (`uv tool install --python 3.13 "headroom-ai[all]"` or `pip install "headroom-ai[all]"`).
2. **MCP** — Cursor MCP server named `headroom` running `headroom mcp serve` (via `uvx --from headroom-ai[mcp]`).
3. **Proxy** — local proxy kept alive (LaunchAgent on macOS). Expected Base URL written to `~/.cursor/headroom-proxy-url.txt`.
4. **Cursor UI** — Settings → Models → Override OpenAI Base URL = contents of that file (Headroom). Keep provider API key (e.g. OpenRouter) in the API key field.
5. **Upstream (optional)** — If Cursor previously pointed Base URL at OpenRouter (or another OpenAI-compatible host), set Headroom’s upstream instead: `HEADROOM_OPENAI_TARGET_API_URL=https://openrouter.ai/api/v1`. Cursor has only one Base URL field; chain is Cursor → Headroom → upstream.
6. **HEADROOM FORCE** — agent policy injected every turn; use `headroom_compress` / `headroom_retrieve` / `headroom_stats`.

## Setup

```bash
# From light (or fat) checkout:
./scripts/setup-headroom.sh
# OpenRouter (or other OpenAI-compatible) upstream:
HEADROOM_OPENAI_TARGET_API_URL=https://openrouter.ai/api/v1 \
  HEADROOM_BACKEND=openrouter \
  ./scripts/setup-headroom.sh
# Also run automatically at the end of ./install.sh
```

Then:

1. Set Override OpenAI Base URL in Cursor to the URL in `~/.cursor/headroom-proxy-url.txt` (Headroom). Do **not** leave OpenRouter’s URL here if you want the proxy.
2. Keep your OpenRouter (or provider) API key in Cursor’s OpenAI API Key field.
3. Reload Window.
4. Confirm MCP lists `headroom`.
5. `headroom doctor`

## Tools

| Tool | Role |
|------|------|
| `headroom_compress` | Compress large tool/file/log/JSON before reasoning |
| `headroom_retrieve` | Expand original by hash when full text is needed |
| `headroom_stats` | Session savings / health |

## Banned by default

Do **not** run `headroom learn` in ways that write `.cursor/rules/*.mdc`. That fights humanizer-stack, always-use-all-skills, and project-memory. Keep durable project knowledge in `.cursor/memory/` only.

## Undo (emergency)

```bash
# Stop LaunchAgent (macOS)
launchctl unload ~/Library/LaunchAgents/ai.headroom.proxy.plist 2>/dev/null || true
# Clear Cursor Override OpenAI Base URL in Settings
# Remove headroom from ~/.cursor/mcp.json if needed
```

Upstream: https://github.com/headroomlabs-ai/headroom
