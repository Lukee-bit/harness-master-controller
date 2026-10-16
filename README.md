# Cursor Master Controller Light

A small, always-on control layer for Cursor agent sessions: a forced spine (voice, project memory, Headroom, an MCP gateway) plus a tiny conditional catalog you can pull any skill, plugin, rule, or tool from on demand.

The design goal is a fixed per-turn token cost as low as possible without losing the ability to reach any tool when a task needs it. Everything already in context is enforced by an always-on rule; everything expensive loads only when it fits the task.

## What it does

- **Voice, every reply.** Hard bans (no em dashes, no "workflow", no AI cliche filler, peer tone) live in one small rule. The large humanizer skill bodies load only when you actually ask to humanize or de-slop.
- **Forced project memory.** Every workspace gets `.cursor/memory/` (project, activeContext, progress, decisions). Hooks nudge at stop if non-trivial work had no memory write.
- **Headroom.** MCP compression for large tool output, called on demand.
- **mcptoon gateway.** All other token tools run behind one MCP gateway, so their schemas never load until used.
- **Conditional catalog.** A tiny list of skills that load only when the task fits them.

## Requirements

- macOS or Linux (Windows is partial; see Honest limits).
- Cursor with agent mode and hooks.
- Python 3.10+.
- Optional per tool: `uv`, Homebrew, Node/npm.

## Install

```bash
git clone <this repo> ~/Projects/cursor-master-controller-light
cd ~/Projects/cursor-master-controller-light
chmod +x install.sh bundle-from-cursor.sh
./bundle-from-cursor.sh    # only if re-bundling from a configured ~/.cursor
./install.sh               # macOS/Linux
```

`install.sh` copies skills, plugins, rules, hooks, and scripts into `~/.cursor`, installs the token-optimizer CLIs (`scripts/setup-token-optimizers.sh`), wires Headroom (`scripts/setup-headroom.sh`), and generates a portable MCP config (`scripts/setup-mcp.sh`).

On Windows, run `.\install.ps1` from PowerShell after installing Git Bash.

Then:

1. Developer: Reload Window.
2. Customize -> Rules: enable the always-on rules.
3. Customize -> Plugins: enable Always Use All Skills, Humanizer Stack, Ponytail, cursor-team-kit, Thermos, Advisor.
4. Verify:

```bash
python3 ~/.cursor/scripts/master-controller/verify_setup.py
```

## The token stack (core)

These are part of light, not optional extras:

| Tool | Role |
|------|------|
| Headroom | MCP compression for tool output and file dumps |
| mcptoon | gateway fronting the other MCP servers |
| RTK | shell-output compression via `preToolUse` |
| sqz / squeez | reversible tool-output compression |
| context-mode | sandboxed execution, only summaries in context |
| jCodeMunch | symbol-level code retrieval |
| Claude Context | semantic code search (local Milvus + Ollama) |
| Code Context Engine | tree-sitter chunk search |
| lumen | local semantic code search (Ollama + SQLite-vec) |
| caveman | terse-output voice |
| token-optimizer | per-session token accounting |
| Ponytail | simplest-correct-code rule (code turns only) |

Direct MCP connections are `headroom` and `mcptoon` only. Everything else is reached through `mcptoon_call`, which keeps the fixed per-turn schema cost near zero.

## Per-project indexing

Some tools index per repo. Run once in each project:

- jCodeMunch: told by its rule (`resolve_repo` then `index_folder`).
- Code Context Engine: `cce init`.
- Claude Context: `index_codebase` via MCP.
- lumen: `lumen index . --backend ollama`.

## Portability

`scripts/setup-mcp.sh` resolves tool paths on the machine it runs on (the uv-tool python, the lumen binary) instead of shipping one machine's absolute paths. Re-run it after installing on a new device.

## Project memory

Templates: `templates/memory/` and `templates/AGENTS.md`.

## Advisor (Layer B, judgment)

Never auto-enabled. The agent consults a stronger model only when it judges a second opinion helps. Task model: omit or `inherit` unless you name a slug from the session allowlist. See [`config/advisor/`](config/advisor/).

## Honest limits

- Rules and plugins must be enabled in Cursor Customize.
- The model can still skip a Read; hooks raise the odds, they do not guarantee.
- The headroom LaunchAgent is macOS-only.
- Native Windows does not support the RTK hook or the lumen plugin binary.
- Claude Context needs colima/Docker + Ollama + Milvus.
- token-optimizer is PolyForm Noncommercial and is not vendored here; install it yourself for personal use.
- Not editor settings, themes, or keybindings.

## License

See [LICENSE](LICENSE).
