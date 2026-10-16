#!/usr/bin/env bash
# Bundle ONLY the light allowlist from ~/.cursor into vendor/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CURSOR_HOME="${CURSOR_HOME:-${HOME}/.cursor}"
MANIFEST="${ROOT}/config/keep-manifest.json"

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

if [[ ! -f "${MANIFEST}" ]]; then
  echo "ERROR: Missing ${MANIFEST}" >&2
  exit 1
fi

echo "=== Bundling Cursor Master Controller Light ==="

# Resolve cache plugin hashes for every manifest plugin under cache/cursor-public
python3 - <<'PY' "${MANIFEST}" "${CURSOR_HOME}"
import json, sys
from pathlib import Path
manifest_path = Path(sys.argv[1])
cursor_home = Path(sys.argv[2])
data = json.loads(manifest_path.read_text())
changed = False

def latest_hash(cache: Path):
    if not cache.is_dir():
        return None
    hashes = [p for p in cache.iterdir() if p.is_dir()]
    if not hashes:
        return None
    return sorted(hashes, key=lambda p: p.stat().st_mtime)[-1]

resolved = {}
for pl in data.get("plugins", []):
    install_path = str(pl.get("install_path", ""))
    source = pl.get("source", "cursor_home")
    if source != "cursor_home" or not install_path.startswith("cache/cursor-public/"):
        continue
    name = pl["name"]
    cache = cursor_home / "plugins" / "cache" / "cursor-public" / name
    h = latest_hash(cache)
    if not h:
        raise SystemExit(f"ERROR: {name} not found under ~/.cursor/plugins/cache/cursor-public")
    resolved[name] = h.name
    want = f"cache/cursor-public/{name}/{h.name}"
    if install_path != want:
        pl["install_path"] = want
        changed = True

tk = resolved.get("cursor-team-kit")
for rule in data.get("rules", []):
    if rule.get("name") in ("no-inline-imports", "typescript-exhaustive-switch") and tk:
        new_path = f"~/.cursor/plugins/cache/cursor-public/cursor-team-kit/{tk}/rules/{rule['name']}.mdc"
        if rule.get("path") != new_path:
            rule["path"] = new_path
            changed = True
        cid = f"cursor-team-kit/rules/{rule['name']}.mdc"
        if rule.get("catalog_id") != cid:
            rule["catalog_id"] = cid
            changed = True

if changed:
    manifest_path.write_text(json.dumps(data, indent=2) + "\n")
    print("Updated manifest hashes " + " ".join(f"{k}={v}" for k, v in resolved.items()))
else:
    print("Using " + " ".join(f"{k}={v}" for k, v in resolved.items()))
PY

echo "Bundling allowlisted skills..."
rm -rf "${ROOT}/vendor/skills"
mkdir -p "${ROOT}/vendor/skills"
python3 - <<'PY' "${MANIFEST}" "${CURSOR_HOME}" "${ROOT}"
import json, shutil, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text())
cursor = Path(sys.argv[2])
root = Path(sys.argv[3])
skills_src = cursor / "skills"
skills_dst = root / "vendor" / "skills"
for entry in manifest["skills"]:
    rel = entry["relpath"]
    src = skills_src / rel
    if not src.is_dir():
        if rel == "my-workflow/project-memory":
            src = root / "plugin/always-use-all-skills/skills/project-memory"
        elif rel == "my-workflow/always-use-all-skills":
            src = root / "plugin/always-use-all-skills/skills/always-use-all-skills"
    if not src.is_dir():
        raise SystemExit(f"ERROR: missing skill {skills_src / rel}")
    dst = skills_dst / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    if not (dst / "SKILL.md").is_file():
        raise SystemExit(f"ERROR: no SKILL.md in {dst}")
    print(f"  skill {rel}")
PY

# Also ensure plugin-local copy of always-use-all-skills skill lives under my-workflow after install
# (install copies vendor/skills as-is)


# Ensure project-memory skill from this repo (may not exist yet in ~/.cursor/skills)
mkdir -p "${ROOT}/vendor/skills/my-workflow/project-memory"
cp "${ROOT}/plugin/always-use-all-skills/skills/project-memory/SKILL.md" \
  "${ROOT}/vendor/skills/my-workflow/project-memory/SKILL.md"

echo "Bundling plugins..."

rm -rf "${ROOT}/vendor/plugins"
mkdir -p "${ROOT}/vendor/plugins"

python3 - <<'PY' "${MANIFEST}" "${CURSOR_HOME}" "${ROOT}"
import json, shutil, sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
cursor = Path(sys.argv[2])
root = Path(sys.argv[3])

def copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".DS_Store"))

for entry in manifest["plugins"]:
    name = entry["name"]
    install_path = entry["install_path"]
    source = entry.get("source", "cursor_home")
    dest = root / "vendor" / "plugins" / install_path
    if source == "project":
        src = root / "plugin" / "always-use-all-skills"
    else:
        src = cursor / "plugins" / install_path
    if not src.is_dir():
        raise SystemExit(f"ERROR: missing plugin {name}: {src}")
    copytree(src, dest)
    print(f"  plugin {name} -> {install_path}")
PY

# Overlay project light plugin into vendor local always-use-all-skills
# (project source already copied; catalogs built next)

echo "Bundling user rules (light set)..."
rm -rf "${ROOT}/vendor/rules"
mkdir -p "${ROOT}/vendor/rules"
# Canonical rules are the project plugin copies. The always-on set lives in
# plugin/always-use-all-skills/rules/ + plugin/rules/ after install; here we
# take the workspace rules when present, else the vendored copies.
BUNDLE_RULE_SOURCES=(
  "${CURSOR_HOME}/rules"
  "${ROOT}/plugin/always-use-all-skills/rules"
)
for srcdir in "${BUNDLE_RULE_SOURCES[@]}"; do
  if [[ -d "${srcdir}" ]]; then
    for f in "${srcdir}"/*.mdc; do
      [[ -f "${f}" ]] || continue
      cp "${f}" "${ROOT}/vendor/rules/$(basename "${f}")"
    done
  fi
done
# humanizer-stack rule must exist in the bundle.
if [[ ! -f "${ROOT}/vendor/rules/humanizer-stack.mdc" ]]; then
  for cand in \
    "${CURSOR_HOME}/rules/humanizer-stack.mdc" \
    "${CURSOR_HOME}/plugins/local/humanizer-stack/rules/humanizer-stack.mdc" \
    "${ROOT}/vendor/plugins/local/humanizer-stack/rules/humanizer-stack.mdc"; do
    if [[ -f "${cand}" ]]; then
      cp "${cand}" "${ROOT}/vendor/rules/humanizer-stack.mdc"
      break
    fi
  done
fi
if [[ ! -f "${ROOT}/vendor/rules/humanizer-stack.mdc" ]]; then
  echo "ERROR: humanizer-stack.mdc not found" >&2
  exit 1
fi

# Overlay light controller skill into vendor (not the fat copy from ~/.cursor)
mkdir -p "${ROOT}/vendor/skills/my-workflow/always-use-all-skills"
cp "${ROOT}/plugin/always-use-all-skills/skills/always-use-all-skills/SKILL.md" \
  "${ROOT}/vendor/skills/my-workflow/always-use-all-skills/SKILL.md"

echo "Building light catalogs..."
python3 "${ROOT}/scripts/build_light_catalogs.py"

# Re-sync catalogs into vendored always-use-all-skills plugin
if [[ -d "${ROOT}/vendor/plugins/local/always-use-all-skills" ]]; then
  rsync -a "${ROOT}/plugin/always-use-all-skills/catalogs/" \
    "${ROOT}/vendor/plugins/local/always-use-all-skills/catalogs/"
  rsync -a "${ROOT}/plugin/always-use-all-skills/rules/" \
    "${ROOT}/vendor/plugins/local/always-use-all-skills/rules/"
  rsync -a "${ROOT}/plugin/always-use-all-skills/skills/" \
    "${ROOT}/vendor/plugins/local/always-use-all-skills/skills/"
  rsync -a "${ROOT}/plugin/always-use-all-skills/.cursor-plugin/" \
    "${ROOT}/vendor/plugins/local/always-use-all-skills/.cursor-plugin/"
fi

echo ""
echo "=== Bundle complete ==="
echo "Skills: $(find "${ROOT}/vendor/skills" -name SKILL.md | wc -l | tr -d ' ')"
echo "Catalog skills: $(python3 -c "import json;print(json.load(open('${ROOT}/plugin/always-use-all-skills/catalogs/skills-index.json'))['count'])")"
