#!/usr/bin/env bash
# Generate a portable ~/.cursor/mcp.json from THIS machine's installed tools.
#
# The live mcp.json hardcodes absolute paths (the headroom uv-tool python, the
# lumen binary). Those differ per user, OS, and CPU arch, so shipping a fixed
# file breaks on another device. This script resolves each path at install time
# with `which` / known install locations and writes the entries.
#
# Run after install.sh (which installs the CLIs) and after the token-optimizer
# / lumen / claude-mem plugins are present. Idempotent; it read-merges so it
# never drops foreign entries.
set -euo pipefail

CURSOR_HOME="${CURSOR_HOME:-$HOME/.cursor}"
MCP_FILE="${CURSOR_HOME}/mcp.json"
export PATH="/opt/homebrew/bin:${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

have() { command -v "$1" >/dev/null 2>&1; }
echo "=== Portable MCP config generator ==="

# --- Resolve the headroom launcher -------------------------------------------
# Prefer the force wrapper (agent-90) with the uv-tool python; fall back to the
# headroom binary on PATH with `mcp serve`.
HEADROOM_WRAPPER="${CURSOR_HOME}/scripts/headroom-mcp-serve.py"
HEADROOM_PY=""
for cand in \
  "${HOME}/.local/share/uv/tools/headroom-ai/bin/python" \
  "$(have python3 && command -v python3)"; do
  if [[ -n "${cand}" && -x "${cand}" ]]; then HEADROOM_PY="${cand}"; break; fi
done
HEADROOM_BIN="$(have headroom && command -v headroom || true)"

# --- Resolve lumen -----------------------------------------------------------
LUMEN_BIN=""
for cand in \
  "${CURSOR_HOME}/plugins/local/lumen/bin/lumen-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')" \
  "${CURSOR_HOME}/plugins/local/lumen/bin/lumen"; do
  if [[ -x "${cand}" ]]; then LUMEN_BIN="${cand}"; break; fi
done
LUMEN_PLUGIN="${CURSOR_HOME}/plugins/local/lumen"

MCP_FILE="${MCP_FILE}" \
HEADROOM_WRAPPER="${HEADROOM_WRAPPER}" \
HEADROOM_PY="${HEADROOM_PY}" \
HEADROOM_BIN="${HEADROOM_BIN}" \
LUMEN_BIN="${LUMEN_BIN}" \
LUMEN_PLUGIN="${LUMEN_PLUGIN}" \
python3 - <<'PY'
import json, os, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

mcp = Path(os.environ["MCP_FILE"])
wrapper = os.environ["HEADROOM_WRAPPER"]
py = os.environ["HEADROOM_PY"]
hb = os.environ["HEADROOM_BIN"]
lumen_bin = os.environ["LUMEN_BIN"]
lumen_plugin = os.environ["LUMEN_PLUGIN"]

data = {"mcpServers": {}}
if mcp.is_file() and mcp.stat().st_size:
    try:
        data = json.loads(mcp.read_text())
    except Exception:
        bak = mcp.with_suffix(".json.bak-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        shutil.copy2(mcp, bak)
        print(f"WARN corrupt mcp.json; backed up to {bak}", file=sys.stderr)
        data = {"mcpServers": {}}
servers = data.setdefault("mcpServers", {})

agent_env = {
    "HEADROOM_SAVINGS_PROFILE": "agent-90",
    "HEADROOM_FORCE_KOMPRESS": "1",
    "HEADROOM_MODE": "token",
    "HEADROOM_TARGET_RATIO": "0.10",
    "HEADROOM_MIN_TOKENS": "120",
    "HEADROOM_COMPRESS_SYSTEM_MESSAGES": "1",
    "HEADROOM_COMPRESS_USER_MESSAGES": "1",
    "HEADROOM_CODE_AWARE_ENABLED": "1",
    "HEADROOM_PROTECT_ANALYSIS_CONTEXT": "1",
    "HEADROOM_PROTECT_RECENT": "0",
    "HEADROOM_ACCURACY_GUARD": "strict",
    "HEADROOM_PROXY_URL": "http://127.0.0.1:8787",
}

# Headroom: force wrapper + resolved python, else the headroom binary.
if Path(wrapper).is_file() and py:
    servers["headroom"] = {"command": py, "args": [wrapper], "env": agent_env}
    print(f"OK  headroom -> {py} {wrapper}")
elif hb:
    servers["headroom"] = {"command": hb, "args": ["mcp", "serve"], "env": agent_env}
    print(f"OK  headroom -> {hb} mcp serve")
else:
    print("WARN headroom CLI not found; install via setup-headroom.sh", file=sys.stderr)

# mcptoon gateway (resolves from PATH).
server = {"command": "mcptoon", "args": ["serve", "--format", "toon"]}
servers["mcptoon"] = server
print("OK  mcptoon -> mcptoon serve --format toon")

# lumen is a plugin-level server: Cursor auto-loads it from the plugin dir, so
# it must NOT also be a mcp.json entry (that would run it twice). Only rewrite
# the plugin's own mcp config to the absolute binary, so Cursor does not resolve
# a relative path against the workspace root.
if lumen_bin:
    cfg = {
        "mcpServers": {
            "lumen": {"type": "stdio", "command": lumen_bin, "args": ["stdio"]}
        }
    }
    for name in (".mcp.json", "mcp.json"):
        p = Path(lumen_plugin) / name
        if p.parent.is_dir():
            p.write_text(json.dumps(cfg, indent=2) + "\n")
            print(f"OK  lumen plugin config -> {p}")
    # Remove any stale direct lumen entry from a prior run.
    servers.pop("lumen", None)
else:
    print("WARN lumen binary not found; run the lumen plugin install", file=sys.stderr)

mcp.write_text(json.dumps(data, indent=2) + "\n")
print(f"OK  wrote {mcp}")
print("servers:", list(servers))
PY

# Register the remaining tools behind the mcptoon gateway on this machine.
if have mcptoon; then
  mcptoon import --from cursor --write >/dev/null 2>&1 || mcptoon import --from cursor --write || true
  # Ensure the gateway knows the servers we expect to exist.
  for srv in sqz squeez context-mode jcodemunch claude-context context-engine claude-mem; do
    : # presence depends on each tool's installer; import --write captures those already registered
  done
  echo "OK  mcptoon gateway refreshed from Cursor config"
fi

echo ""
echo "=== Portable MCP config complete ==="
echo "Restart Cursor so the resolved paths load."
