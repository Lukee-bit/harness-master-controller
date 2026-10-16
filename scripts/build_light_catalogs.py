#!/usr/bin/env python3
"""Build light catalog indexes from config/keep-manifest.json + vendored skill frontmatter."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "config" / "keep-manifest.json"
CATALOGS = ROOT / "plugin" / "always-use-all-skills" / "catalogs"
VENDOR_SKILLS = ROOT / "vendor" / "skills"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    data: dict = {}
    # minimal YAML: name/description only (description may be folded)
    name_m = re.search(r"^name:\s*(.+)$", block, re.M)
    if name_m:
        data["name"] = name_m.group(1).strip().strip("\"'")
    desc_m = re.search(r"^description:\s*>-?\s*\n((?:[ \t]+.+\n)+)", block, re.M)
    if desc_m:
        lines = [ln.strip() for ln in desc_m.group(1).splitlines() if ln.strip()]
        data["description"] = " ".join(lines)
    else:
        desc_m2 = re.search(r'^description:\s*[\'"]?(.*?)[\'"]?\s*$', block, re.M)
        if desc_m2:
            data["description"] = desc_m2.group(1).strip()
        else:
            # multiline quoted description
            desc_m3 = re.search(r'^description:\s*[\'"]([\s\S]*?)[\'"]\s*$', block, re.M)
            if desc_m3:
                data["description"] = re.sub(r"\s+", " ", desc_m3.group(1)).strip()
    return data


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def skill_items(manifest: dict) -> list[dict]:
    items = []
    for entry in manifest.get("skills", []):
        rel = entry["relpath"]
        skill_md = VENDOR_SKILLS / rel / "SKILL.md"
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8")) if skill_md.is_file() else {}
        name = fm.get("name") or Path(rel).name
        desc = fm.get("description") or entry.get("description") or name
        items.append(
            {
                "catalog_id": entry["catalog_id"],
                "name": name,
                "path": f"~/.cursor/skills/{rel}/SKILL.md",
                "mode": entry.get("mode", "apply when relevant"),
                "description": desc[:500],
                "triggers": list(entry.get("triggers") or []),
                "domain": entry.get("domain", ""),
            }
        )
    return items


def plugin_items(manifest: dict) -> list[dict]:
    items = []
    for entry in manifest.get("plugins", []):
        name = entry["name"]
        install_path = entry["install_path"]
        items.append(
            {
                "name": name,
                "display_name": name,
                "path": f"~/.cursor/plugins/{install_path}/.cursor-plugin",
                "mode": entry.get("mode", "apply when relevant"),
                "description": entry.get("note") or name,
                "triggers": list(entry.get("triggers") or []),
                "domain": entry.get("domain", ""),
            }
        )
    return items


def rule_items(manifest: dict) -> list[dict]:
    items = []
    for entry in manifest.get("rules", []):
        items.append(
            {
                "catalog_id": entry["catalog_id"],
                "name": entry["name"],
                "path": entry["path"],
                "mode": entry.get("mode", "apply when relevant"),
                "native_always_apply": entry.get("mode") == "always apply",
                "description": entry.get("description") or entry["name"],
                "triggers": list(entry.get("triggers") or []),
                "domain": entry.get("domain", ""),
            }
        )
    return items


def write_index(name: str, items: list[dict]) -> None:
    CATALOGS.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "edition": "light",
        "count": len(items),
        "items": items,
    }
    path = CATALOGS / f"{name}-index.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md_lines = [f"# {name.title()} catalog (light)", "", f"Count: {len(items)}", ""]
    for it in items:
        md_lines.append(f"- **{it.get('name')}** (`{it.get('catalog_id', it.get('path'))}`) — {it.get('mode')}")
        md_lines.append(f"  - {it.get('description', '')[:160]}")
    (CATALOGS / f"{name}.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"Wrote {path} ({len(items)} items)")


def main() -> None:
    if not MANIFEST.is_file():
        raise SystemExit(f"Missing {MANIFEST}")
    manifest = load_manifest()
    write_index("skills", skill_items(manifest))
    write_index("plugins", plugin_items(manifest))
    write_index("rules", rule_items(manifest))


if __name__ == "__main__":
    main()
