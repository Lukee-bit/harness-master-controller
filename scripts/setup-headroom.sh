#!/usr/bin/env bash
# Force-enable Headroom CLI, MCP, and local proxy for Cursor.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURSOR_HOME="${CURSOR_HOME:-$HOME/.cursor}"
PORT="${HEADROOM_PROXY_PORT:-8787}"
# Optional OpenAI-compatible upstream (e.g. OpenRouter). Cursor Base URL stays Headroom;
# Headroom forwards here. Env: HEADROOM_OPENAI_TARGET_API_URL or OPENAI_TARGET_API_URL.
# Persist last known upstream from prior setup when env unset.
UPSTREAM_URL_FILE="${CURSOR_HOME}/headroom-openai-upstream.txt"
if [[ -z "${HEADROOM_OPENAI_TARGET_API_URL:-${OPENAI_TARGET_API_URL:-}}" && -f "${UPSTREAM_URL_FILE}" ]]; then
  OPENAI_TARGET="$(cat "${UPSTREAM_URL_FILE}" 2>/dev/null || true)"
else
  OPENAI_TARGET="${HEADROOM_OPENAI_TARGET_API_URL:-${OPENAI_TARGET_API_URL:-}}"
fi
# Default OpenRouter when still empty (Cursor Override Base URL → Headroom → OpenRouter).
if [[ -z "${OPENAI_TARGET}" ]]; then
  OPENAI_TARGET="https://openrouter.ai/api/v1"
fi
HEADROOM_BACKEND_FLAG="${HEADROOM_BACKEND:-openrouter}"
PLIST_DIR="${HOME}/Library/LaunchAgents"
PLIST_LABEL="ai.headroom.proxy"
PLIST_PATH="${PLIST_DIR}/${PLIST_LABEL}.plist"
PROXY_URL_FILE="${CURSOR_HOME}/headroom-proxy-url.txt"
LOG_DIR="${CURSOR_HOME}/logs"
mkdir -p "${CURSOR_HOME}" "${LOG_DIR}"

echo "=== Headroom force setup ==="
echo "CURSOR_HOME=${CURSOR_HOME}"

have_cmd() { command -v "$1" >/dev/null 2>&1; }

ensure_uv() {
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if have_cmd uv; then
    return 0
  fi
  echo "Installing uv (required for headroom-ai Python 3.13)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  have_cmd uv
}

install_cli() {
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if have_cmd headroom; then
    echo "OK  headroom CLI already on PATH: $(command -v headroom)"
    return 0
  fi
  echo "Installing headroom-ai[all]..."
  ensure_uv || true
  if have_cmd uv; then
    uv tool install --python 3.13 "headroom-ai[all]" || uv tool install "headroom-ai[all]" || true
  fi
  if ! have_cmd headroom && have_cmd pip3; then
    pip3 install --user "headroom-ai[all]" || true
  fi
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if ! have_cmd headroom; then
    echo "ERROR: headroom CLI not on PATH after install. Add ~/.local/bin to PATH and re-run." >&2
    return 1
  fi
  echo "OK  installed headroom at $(command -v headroom)"
}

install_mcp_wrapper() {
  local src="${ROOT}/scripts/headroom-mcp-serve.py"
  local dest_dir="${CURSOR_HOME}/scripts"
  local dest="${dest_dir}/headroom-mcp-serve.py"
  mkdir -p "${dest_dir}"
  if [[ -f "${src}" ]]; then
    cp "${src}" "${dest}"
    chmod +x "${dest}"
    echo "OK  installed MCP wrapper -> ${dest}"
  else
    echo "WARN missing ${src}" >&2
  fi
}

write_recommended_mcp() {
  local src="${ROOT}/config/mcp/mcp-light-recommended.json"
  local dest="${CURSOR_HOME}/mcp-light-recommended.json"
  if [[ -f "${src}" ]]; then
    cp "${src}" "${dest}"
    echo "OK  wrote ${dest}"
  else
    echo "WARN missing ${src}" >&2
  fi
  if [[ -f "${ROOT}/config/headroom/README.md" ]]; then
    cp "${ROOT}/config/headroom/README.md" "${CURSOR_HOME}/headroom-README.md"
  fi
}

merge_live_mcp() {
  local live=""
  for candidate in \
    "${CURSOR_HOME}/mcp.json" \
    "${HOME}/.cursor/mcp.json" \
    "${HOME}/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/mcp.json"; do
    if [[ -f "${candidate}" ]]; then
      live="${candidate}"
      break
    fi
  done

  # Cursor often stores MCP in settings; also try common mcp.json only.
  if [[ -z "${live}" ]]; then
    # Create ~/.cursor/mcp.json as the merge target for Cursor to import
    live="${CURSOR_HOME}/mcp.json"
    echo '{"mcpServers":{}}' > "${live}"
    echo "OK  created ${live} (merge Headroom into Cursor Settings → MCP if not auto-loaded)"
  fi

  HEADROOM_LIVE_MCP="${live}" HEADROOM_CURSOR_HOME="${CURSOR_HOME}" HEADROOM_ROOT="${ROOT}" python3 - <<'PY'
import json, os, shutil
from pathlib import Path
from datetime import datetime, timezone

live = Path(os.environ["HEADROOM_LIVE_MCP"])
cursor_home = Path(os.environ["HEADROOM_CURSOR_HOME"])
rec = cursor_home / "mcp-light-recommended.json"
snippet = Path(os.environ["HEADROOM_ROOT"]) / "config/mcp/headroom.json"
wrapper = cursor_home / "scripts/headroom-mcp-serve.py"

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

# Prefer uv-tool python + force wrapper so MCP compress always applies agent-90.
uv_python = Path.home() / ".local/share/uv/tools/headroom-ai/bin/python"
headroom_bin = shutil.which("headroom")
if wrapper.is_file() and uv_python.is_file():
    headroom = {
        "command": str(uv_python),
        "args": [str(wrapper)],
        "env": agent_env,
    }
elif headroom_bin:
    headroom = {
        "command": headroom_bin,
        "args": ["mcp", "serve"],
        "env": agent_env,
    }
else:
    headroom = None

if headroom is None and snippet.is_file():
    headroom = json.loads(snippet.read_text()).get("mcpServers", {}).get("headroom")
if headroom is None and rec.is_file():
    headroom = json.loads(rec.read_text()).get("mcpServers", {}).get("headroom")
if headroom is None:
    headroom = {
        "command": "uvx",
        "args": ["--from", "headroom-ai[mcp]", "headroom", "mcp", "serve"],
        "env": agent_env,
    }
else:
    # Always force agent-90 env onto whatever command we selected.
    env = dict(headroom.get("env") or {})
    env.update(agent_env)
    headroom["env"] = env

data = {"mcpServers": {}}
if live.is_file() and live.stat().st_size > 0:
    try:
        data = json.loads(live.read_text())
    except Exception:
        bak = live.with_suffix(live.suffix + ".bak-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        shutil.copy2(live, bak)
        print(f"WARN corrupt MCP JSON; backed up to {bak}", flush=True)
        data = {"mcpServers": {}}

if "mcpServers" not in data or not isinstance(data.get("mcpServers"), dict):
    data["mcpServers"] = {}

bak = live.with_suffix(live.suffix + ".bak-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
if live.is_file():
    shutil.copy2(live, bak)
    print(f"OK  backup {bak}", flush=True)

data["mcpServers"]["headroom"] = headroom
live.write_text(json.dumps(data, indent=2) + "\n")
print(f"OK  merged headroom into {live}", flush=True)
PY
}

install_launchagent_proxy() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "WARN non-macOS: start proxy manually: headroom proxy --port ${PORT}"
    echo "http://127.0.0.1:${PORT}/v1" > "${PROXY_URL_FILE}"
    return 0
  fi

  local headroom_bin
  headroom_bin="$(command -v headroom)"
  mkdir -p "${PLIST_DIR}"

  local extra_args=""
  # token mode = compress for savings (cache mode prioritizes prefix cache).
  extra_args+="    <string>--mode</string>
    <string>token</string>
"
  if [[ -n "${OPENAI_TARGET}" ]]; then
    extra_args+="    <string>--openai-api-url</string>
    <string>${OPENAI_TARGET}</string>
    <string>--provider-name</string>
    <string>OpenRouter</string>
"
    echo "${OPENAI_TARGET}" > "${UPSTREAM_URL_FILE}"
    echo "OK  OpenAI-compatible upstream -> ${OPENAI_TARGET}"
  fi
  if [[ -n "${HEADROOM_BACKEND_FLAG}" ]]; then
    extra_args+="    <string>--backend</string>
    <string>${HEADROOM_BACKEND_FLAG}</string>
"
  fi

  cat > "${PLIST_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${headroom_bin}</string>
    <string>proxy</string>
    <string>--port</string>
    <string>${PORT}</string>
${extra_args}  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HEADROOM_SAVINGS_PROFILE</key>
    <string>agent-90</string>
    <key>HEADROOM_FORCE_KOMPRESS</key>
    <string>1</string>
    <key>HEADROOM_MODE</key>
    <string>token</string>
    <key>HEADROOM_TARGET_RATIO</key>
    <string>0.10</string>
    <key>HEADROOM_MIN_TOKENS</key>
    <string>120</string>
    <key>HEADROOM_COMPRESS_SYSTEM_MESSAGES</key>
    <string>1</string>
    <key>HEADROOM_COMPRESS_USER_MESSAGES</key>
    <string>1</string>
    <key>HEADROOM_CODE_AWARE_ENABLED</key>
    <string>1</string>
    <key>HEADROOM_PROTECT_ANALYSIS_CONTEXT</key>
    <string>1</string>
    <key>HEADROOM_PROTECT_RECENT</key>
    <string>2</string>
    <key>HEADROOM_SAVINGS_TARGET</key>
    <string>0.90</string>
    <key>HEADROOM_ACCURACY_GUARD</key>
    <string>strict</string>
EOF
  if [[ -n "${OPENAI_TARGET}" ]]; then
    cat >> "${PLIST_PATH}" <<EOF
    <key>OPENAI_TARGET_API_URL</key>
    <string>${OPENAI_TARGET}</string>
EOF
  fi
  cat >> "${PLIST_PATH}" <<EOF
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/headroom-proxy.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/headroom-proxy.err.log</string>
</dict>
</plist>
EOF

  launchctl unload "${PLIST_PATH}" 2>/dev/null || true
  launchctl load "${PLIST_PATH}" 2>/dev/null || launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}" 2>/dev/null || true
  echo "http://127.0.0.1:${PORT}/v1" > "${PROXY_URL_FILE}"
  echo "OK  LaunchAgent ${PLIST_LABEL} loaded; proxy URL -> ${PROXY_URL_FILE}"
  # Proxy preloads models; wait for liveness
  for _i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if curl -sf "http://127.0.0.1:${PORT}/livez" >/dev/null 2>&1; then
      echo "OK  proxy live at http://127.0.0.1:${PORT}"
      break
    fi
    sleep 1
  done
}

print_cursor_ui_steps() {
  local url
  url="$(cat "${PROXY_URL_FILE}" 2>/dev/null || echo "http://127.0.0.1:${PORT}/v1")"
  local upstream
  upstream="$(cat "${UPSTREAM_URL_FILE}" 2>/dev/null || echo "${OPENAI_TARGET}")"
  cat <<EOF

=== REQUIRED Cursor UI steps (Headroom + OpenRouter) ===
1. Settings → Models → Override OpenAI Base URL
   Set to: ${url}
   (This is Headroom on your Mac — not OpenRouter's URL.)
2. Keep your OpenRouter API key in the OpenAI API Key field.
3. Confirm Settings → MCP shows server "headroom".
4. Developer: Reload Window

Traffic: Cursor → Headroom (${url}) → upstream (${upstream:-default provider})
If you use OpenRouter models, upstream should be https://openrouter.ai/api/v1
(re-run with HEADROOM_OPENAI_TARGET_API_URL=https://openrouter.ai/api/v1).
EOF
}

run_doctor() {
  export PATH="${HOME}/.local/bin:${PATH}"
  if have_cmd headroom; then
    headroom doctor 2>&1 || echo "WARN headroom doctor reported issues (proxy may still be starting)"
  fi
}

install_cli
install_mcp_wrapper
write_recommended_mcp
merge_live_mcp
install_launchagent_proxy
print_cursor_ui_steps
run_doctor

echo ""
echo "=== Headroom force setup complete ==="
