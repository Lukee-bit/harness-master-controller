#!/usr/bin/env bash
# Install Cursor Master Controller Light (macOS/Linux).
# Backs up existing ~/.cursor/skills, then replaces with the light allowlist.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CURSOR_HOME="${CURSOR_HOME:-${HOME}/.cursor}"
PLUGIN_DEST="${CURSOR_HOME}/plugins/local/always-use-all-skills"
SCRIPTS_DEST="${CURSOR_HOME}/scripts/master-controller"
HOOKS_DIR="${CURSOR_HOME}/hooks"
RULES_DIR="${CURSOR_HOME}/rules"
SKILLS_DEST="${CURSOR_HOME}/skills"
BACKUP_ROOT="${CURSOR_HOME}/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"

echo "=== Cursor Master Controller Light Installer ==="
echo "CURSOR_HOME=${CURSOR_HOME}"

if [[ ! -d "${ROOT}/vendor/skills" ]] || [[ -z "$(find "${ROOT}/vendor/skills" -name SKILL.md 2>/dev/null | head -1)" ]]; then
  echo "ERROR: No bundled skills in vendor/skills/" >&2
  echo "Run ./bundle-from-cursor.sh first." >&2
  exit 1
fi

copy_tree() {
  local src="$1"
  local dst="$2"
  mkdir -p "${dst}"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "${src}/" "${dst}/"
  else
    cp -R "${src}/." "${dst}/"
  fi
}

mirror_tree() {
  local src="$1"
  local dst="$2"
  mkdir -p "${dst}"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${src}/" "${dst}/"
  else
    rm -rf "${dst}"
    mkdir -p "${dst}"
    cp -R "${src}/." "${dst}/"
  fi
}

mkdir -p "${CURSOR_HOME}/state" "${CURSOR_HOME}/plugins/local" "${RULES_DIR}" "${HOOKS_DIR}" "${SCRIPTS_DEST}" "${BACKUP_ROOT}"

# Backup existing skills if present and non-empty
if [[ -d "${SKILLS_DEST}" ]] && [[ -n "$(find "${SKILLS_DEST}" -name SKILL.md 2>/dev/null | head -1)" ]]; then
  BACKUP_DIR="${BACKUP_ROOT}/skills-full-${STAMP}"
  echo "Backing up existing skills to ${BACKUP_DIR} ..."
  mkdir -p "${BACKUP_DIR}"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "${SKILLS_DEST}/" "${BACKUP_DIR}/"
  else
    cp -R "${SKILLS_DEST}/." "${BACKUP_DIR}/"
  fi
  echo "${BACKUP_DIR}" > "${BACKUP_ROOT}/skills-full-latest.txt"
  echo "Backup recorded in ${BACKUP_ROOT}/skills-full-latest.txt"
fi

echo "Installing light skills to ${SKILLS_DEST} (mirror/delete)..."
mirror_tree "${ROOT}/vendor/skills" "${SKILLS_DEST}"

if [[ -d "${ROOT}/vendor/plugins" ]]; then
  echo "Installing bundled plugins..."
  if [[ -d "${ROOT}/vendor/plugins/local" ]]; then
    for plugin_dir in "${ROOT}/vendor/plugins/local"/*; do
      [[ -d "${plugin_dir}" ]] || continue
      name="$(basename "${plugin_dir}")"
      mirror_tree "${plugin_dir}" "${CURSOR_HOME}/plugins/local/${name}"
    done
  fi
  if [[ -d "${ROOT}/vendor/plugins/cache" ]]; then
    mkdir -p "${CURSOR_HOME}/plugins/cache"
    # Merge cache trees without deleting unrelated marketplace plugins
    if command -v rsync >/dev/null 2>&1; then
      rsync -a "${ROOT}/vendor/plugins/cache/" "${CURSOR_HOME}/plugins/cache/"
    else
      cp -R "${ROOT}/vendor/plugins/cache/." "${CURSOR_HOME}/plugins/cache/"
    fi
  fi
fi

# Ensure light master plugin (project is source of truth)
echo "Installing light master plugin..."
mirror_tree "${ROOT}/plugin/always-use-all-skills" "${PLUGIN_DEST}"
# Re-apply catalogs from plugin (already included)
if [[ -d "${ROOT}/vendor/plugins/local/always-use-all-skills/catalogs" ]]; then
  copy_tree "${ROOT}/vendor/plugins/local/always-use-all-skills/catalogs" "${PLUGIN_DEST}/catalogs"
fi

if [[ -d "${ROOT}/vendor/rules" ]]; then
  echo "Installing user rules..."
  copy_tree "${ROOT}/vendor/rules" "${RULES_DIR}"
fi

echo "Installing hook scripts to ${SCRIPTS_DEST}..."
mirror_tree "${ROOT}/scripts" "${SCRIPTS_DEST}"
chmod +x "${SCRIPTS_DEST}"/*.py 2>/dev/null || true

write_hook_shim() {
  local name="$1"
  local py_script="$2"
  cat > "${HOOKS_DIR}/${name}" <<SH
#!/usr/bin/env bash
set -euo pipefail
exec python3 "${SCRIPTS_DEST}/${py_script}"
SH
  chmod +x "${HOOKS_DIR}/${name}"
}

write_hook_shim "session-start.sh" "session_start.py"
write_hook_shim "route-skills.sh" "route_prompt.py"
write_hook_shim "track-reads.sh" "track_reads.py"
write_hook_shim "voice-lint-stop.sh" "stop_enforce.py"
write_hook_shim "inject-task-skills.sh" "inject_task_skills.py"
write_hook_shim "subagent-policy.sh" "subagent_policy.py"
write_hook_shim "tab-prose-lint.sh" "tab_prose_lint.py"

cat > "${CURSOR_HOME}/hooks.json" <<'JSON'
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "command": "./hooks/session-start.sh"
      }
    ],
    "beforeSubmitPrompt": [
      {
        "command": "./hooks/route-skills.sh",
        "matcher": "UserPromptSubmit"
      }
    ],
    "preToolUse": [
      {
        "command": "./hooks/inject-task-skills.sh",
        "matcher": "Task"
      }
    ],
    "postToolUse": [
      {
        "command": "./hooks/track-reads.sh",
        "matcher": "Read"
      },
      {
        "command": "./hooks/track-reads.sh",
        "matcher": "Write"
      },
      {
        "command": "./hooks/track-reads.sh",
        "matcher": "StrReplace"
      }
    ],
    "subagentStart": [
      {
        "command": "./hooks/subagent-policy.sh"
      }
    ],
    "stop": [
      {
        "command": "./hooks/voice-lint-stop.sh",
        "loop_limit": 3
      }
    ],
    "afterTabFileEdit": [
      {
        "command": "./hooks/tab-prose-lint.sh"
      }
    ]
  }
}
JSON

# Rules install: user rules own the always-on set (single source, no duplicates).
# The master plugin and humanizer-stack plugin no longer ship rule copies.
if [[ -f "${ROOT}/vendor/rules/always-use-all-skills.mdc" ]]; then
  cp "${ROOT}/vendor/rules/always-use-all-skills.mdc" "${RULES_DIR}/always-use-all-skills.mdc"
fi
if [[ -f "${ROOT}/vendor/rules/project-memory.mdc" ]]; then
  cp "${ROOT}/vendor/rules/project-memory.mdc" "${RULES_DIR}/project-memory.mdc"
fi
if [[ -f "${ROOT}/vendor/rules/humanizer-stack.mdc" ]]; then
  cp "${ROOT}/vendor/rules/humanizer-stack.mdc" "${RULES_DIR}/humanizer-stack.mdc"
fi
# Remove duplicate plugin rule copies if a prior install left them (dedupe).
rm -f "${PLUGIN_DEST}/rules/always-use-all-skills.mdc" "${PLUGIN_DEST}/rules/project-memory.mdc" 2>/dev/null || true
rm -f "${CURSOR_HOME}/plugins/local/humanizer-stack/rules/humanizer-stack.mdc" 2>/dev/null || true

if [[ -f "${ROOT}/plugin/always-use-all-skills/skills/project-memory/SKILL.md" ]]; then
  mkdir -p "${SKILLS_DEST}/my-workflow/project-memory"
  cp "${ROOT}/plugin/always-use-all-skills/skills/project-memory/SKILL.md" \
    "${SKILLS_DEST}/my-workflow/project-memory/SKILL.md"
fi

# Memory templates for agents to copy from
mkdir -p "${CURSOR_HOME}/templates/light-memory"
if [[ -d "${ROOT}/templates" ]]; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "${ROOT}/templates/" "${CURSOR_HOME}/templates/light-memory/"
  else
    cp -R "${ROOT}/templates/." "${CURSOR_HOME}/templates/light-memory/"
  fi
fi

# Recommended MCP merge file (does not overwrite live mcp.json)
if [[ -f "${ROOT}/config/mcp/mcp-light-recommended.json" ]]; then
  cp "${ROOT}/config/mcp/mcp-light-recommended.json" "${CURSOR_HOME}/mcp-light-recommended.json"
fi

# Advisor Layer B: remove obsolete model pool; Task allowlist + inherit only
rm -f "${CURSOR_HOME}/advisor-light-model-pool.json"
if [[ -f "${ROOT}/config/advisor/README.md" ]]; then
  cp "${ROOT}/config/advisor/README.md" "${CURSOR_HOME}/advisor-light-README.md"
fi

# Headroom ALWAYS FORCE (CLI + MCP merge + proxy LaunchAgent)
if [[ -x "${ROOT}/scripts/setup-headroom.sh" ]]; then
  bash "${ROOT}/scripts/setup-headroom.sh" || echo "WARN setup-headroom.sh had errors; re-run manually" >&2
elif [[ -f "${ROOT}/scripts/setup-headroom.sh" ]]; then
  bash "${ROOT}/scripts/setup-headroom.sh" || echo "WARN setup-headroom.sh had errors; re-run manually" >&2
fi
if [[ -f "${ROOT}/config/headroom/README.md" ]]; then
  cp "${ROOT}/config/headroom/README.md" "${CURSOR_HOME}/headroom-README.md"
fi

# Token optimizer stack (rtk, sqz, squeez, mcptoon, context-mode, jcodemunch)
if [[ -x "${ROOT}/scripts/setup-token-optimizers.sh" ]]; then
  bash "${ROOT}/scripts/setup-token-optimizers.sh" || echo "WARN setup-token-optimizers.sh had errors; re-run manually" >&2
fi

# Portable MCP config: resolve tool paths on THIS machine (uv python, lumen binary)
if [[ -f "${ROOT}/scripts/setup-mcp.sh" ]]; then
  bash "${ROOT}/scripts/setup-mcp.sh" || echo "WARN setup-mcp.sh had errors; re-run manually" >&2
fi



if [[ -d "${PLUGIN_DEST}/catalogs" ]]; then
  python3 "${SCRIPTS_DEST}/rewrite_paths.py" "${PLUGIN_DEST}/catalogs" || true
fi

mkdir -p "${PLUGIN_DEST}/hooks"
cp "${CURSOR_HOME}/hooks.json" "${PLUGIN_DEST}/hooks/hooks.json"

# Sync light controller skill into skills tree (already mirrored from vendor)
cp "${PLUGIN_DEST}/skills/always-use-all-skills/SKILL.md" \
  "${SKILLS_DEST}/my-workflow/always-use-all-skills/SKILL.md"

echo ""
echo "=== Light install complete ==="
echo ""
if [[ -f "${BACKUP_ROOT}/skills-full-latest.txt" ]]; then
  echo "Skills backup: $(cat "${BACKUP_ROOT}/skills-full-latest.txt")"
fi
echo "Next steps:"
echo "  1. Reload Cursor"
echo "  2. Customize -> Rules: enable always-use-all-skills, humanizer-stack, project-memory"
echo "  3. Customize -> Plugins: Always Use All Skills (Light), Humanizer Stack, Ponytail, cursor-team-kit, thermos, Advisor"
echo "  4. cursor-subagent-creator is a judgment skill; Advisor is judgment-based; Headroom is ALWAYS FORCE"
echo "  5. Headroom FORCE: set Override OpenAI Base URL from ~/.cursor/headroom-proxy-url.txt; confirm MCP headroom"
echo "  6. Verify: python3 ${SCRIPTS_DEST}/verify_setup.py"
echo ""
