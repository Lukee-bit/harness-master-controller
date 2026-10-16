#!/usr/bin/env bash
# Install + force-enable the token-optimizer stack for Cursor.
# Tools: rtk, sqz (+sqz-mcp), squeez, mcptoon, context-mode, jcodemunch-mcp.
# Each compresses context before the model reads it. All are forced via
# ~/.cursor/rules/*.mdc (alwaysApply) plus MCP entries in ~/.cursor/mcp.json.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURSOR_HOME="${CURSOR_HOME:-$HOME/.cursor}"
RULES_DIR="${CURSOR_HOME}/rules"
mkdir -p "${RULES_DIR}"

export PATH="/opt/homebrew/bin:${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
have() { command -v "$1" >/dev/null 2>&1; }

echo "=== Token optimizer stack setup ==="

# 1. rtk (Rust Token Killer) - brew; integrates via preToolUse hook
if ! have rtk; then
  have brew && brew install rtk || echo "WARN install rtk manually"
fi
if have rtk; then
  rtk init -g --agent cursor >/dev/null 2>&1 || true
  echo "OK  rtk $(rtk --version 2>/dev/null | head -1)"
fi

# 2. sqz (+ sqz-mcp) - brew tap
if ! have sqz; then
  have brew && brew install ojuschugh1/sqz/sqz || echo "WARN install sqz manually"
fi
if have sqz; then
  sqz init >/dev/null 2>&1 || true
  sqz init --global >/dev/null 2>&1 || true
  echo "OK  sqz $(sqz --version 2>/dev/null | head -1)"
fi

# 3. squeez - npm (claudioemmanuel variant)
if ! have squeez; then
  have npm && npm install -g squeez || echo "WARN install squeez manually"
fi
have squeez && echo "OK  squeez $(squeez --version 2>/dev/null | head -1)"

# 4. mcptoon - uv tool
if ! have mcptoon; then
  have uv && uv tool install mcptoon || echo "WARN install mcptoon manually"
fi
have mcptoon && echo "OK  mcptoon $(mcptoon --version 2>/dev/null | head -1)"

# 5. context-mode - npm, needs native build scripts allowed
if ! have context-mode; then
  have npm && npm install -g --allow-scripts=context-mode,better-sqlite3 context-mode || echo "WARN install context-mode manually"
fi
have context-mode && echo "OK  context-mode $(context-mode --version 2>/dev/null | head -1)"

# 6. jcodemunch - uv tool; init for Cursor
if ! have jcodemunch-mcp; then
  have uv && uv tool install jcodemunch-mcp || echo "WARN install jcodemunch manually"
fi
if have jcodemunch-mcp; then
  jcodemunch-mcp init --client cursor --yes >/dev/null 2>&1 || true
  echo "OK  jcodemunch-mcp $(jcodemunch-mcp --version 2>/dev/null | head -1)"
fi

# 7. Code Context Engine - uv tool with local fastembed backend
if ! have cce; then
  have uv && uv tool install "code-context-engine[local]" || echo "WARN install cce manually"
fi
have cce && echo "OK  cce $(cce --version 2>/dev/null | head -1)"
echo "    note: run 'cce init' inside each project to index + register its MCP entry"

# 8. Claude Context backend (local Milvus + Ollama)
if ! have ollama; then
  have brew && brew install ollama || echo "WARN install ollama manually"
fi
if have ollama; then
  brew services start ollama >/dev/null 2>&1 || true
  ollama pull nomic-embed-text >/dev/null 2>&1 || true
  echo "OK  ollama + nomic-embed-text (local embeddings)"
fi
if have docker; then
  MILVUS_DIR="${HOME}/.milvus-standalone"
  if [[ -f "${MILVUS_DIR}/docker-compose.yml" ]]; then
    (cd "${MILVUS_DIR}" && docker compose up -d >/dev/null 2>&1) && echo "OK  Milvus standalone on 127.0.0.1:19530" || echo "WARN start Milvus manually (${MILVUS_DIR})"
  else
    echo "WARN Milvus compose missing at ${MILVUS_DIR}; claude-context needs Milvus"
  fi
fi

# 9. Install forced rules
for r in rtk.mdc mcptoon.mdc context-mode.mdc sqz-squeez.mdc jcodemunch.mdc claude-context.mdc cce.mdc caveman.mdc token-efficient.mdc; do
  if [[ -f "${ROOT}/vendor/rules/${r}" ]]; then
    cp "${ROOT}/vendor/rules/${r}" "${RULES_DIR}/${r}"
    echo "OK  rule ${r}"
  fi
done

# 10. caveman (output compression skill + Cursor session hook)
if ! have caveman; then
  npx -y github:JuliusBrussee/caveman -- --only cursor >/dev/null 2>&1 || echo "WARN install caveman manually"
fi
if [[ -d "${CURSOR_HOME}/caveman" ]]; then
  mkdir -p "${HOME}/.config/caveman"
  [[ -f "${HOME}/.config/caveman/config.json" ]] || echo '{"defaultMode": "caveman"}' > "${HOME}/.config/caveman/config.json"
  echo "OK  caveman skill + hook (default mode caveman)"
fi

# 11. claude-token-efficient is a pure rule (token-efficient.mdc above); nothing to install.

echo ""
echo "=== Token optimizer stack setup complete ==="
echo "Restart Cursor so MCP servers + rules load."
