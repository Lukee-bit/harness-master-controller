#!/usr/bin/env python3
"""Shared utilities for master controller hooks."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".cursor/state"
MANIFEST_PATH = STATE_DIR / "session-manifest.json"
CATALOGS_DIR = Path.home() / ".cursor/plugins/local/always-use-all-skills/catalogs"

# Two cheap spines only. Voice and other skills are conditional (router-driven)
# so their large bodies are not force-read on every turn.
MANDATORY_READS: list[dict[str, str]] = [
    {
        "id": "rule",
        "path": "~/.cursor/rules/always-use-all-skills.mdc",
    },
    {
        "id": "project-memory",
        "path": "~/.cursor/skills/my-workflow/project-memory/SKILL.md",
    },
]

PROJECT_MEMORY_FORCE = (
    "PROJECT MEMORY FORCE: If workspace `.cursor/memory/` is missing, create "
    "`project.md`, `activeContext.md`, `progress.md`, `decisions.md`, and `research/`. "
    "Before non-trivial work, Read those core files. During and after work, update them "
    "(append dated progress/decisions; refresh activeContext). Never store secrets. "
    "Before ending, run a memory pass or append `no durable updates`. "
    "Single memory system only — no Memory Bank modes or parallel context/ trees."
)

ADVISOR_JUDGMENT = (
    "ADVISOR (Layer B, judgment): Not auto-enabled. Reason about whether a second opinion "
    "materially helps; consult only when it does (major decision, stuck, before done), or on "
    "request. When consulting, omit Task model or pass inherit unless the user names a slug "
    "from this session's Task available_subagent_models. If Task rejects a slug, use inherit "
    "and say so in one line. Enabling the mode for a conversation is allowed only when a "
    "checkpoint consult is warranted, never as a default. Do not invent or prefer a model-pool file."
)

HEADROOM_FORCE = (
    "HEADROOM FORCE (always on): Headroom MCP and local proxy are mandatory. "
    "Before reasoning on tool output, file dumps, logs, JSON, or search results, "
    "call headroom_compress. Use headroom_retrieve by hash when you need the full "
    "original. Use headroom_stats when checking savings or health. Never disable, "
    "skip, or work around Headroom for convenience. Do not run headroom learn into "
    ".cursor/rules (project memory stays .cursor/memory/ only)."
)

SUBAGENT_FORCE = (
    "SUBAGENTS: Use only subagent_type values listed for this session's Task tool "
    "(built-ins, loaded plugin agents such as advisor-subagent, and custom agents already "
    "in the enum). Omit model or pass inherit unless the user names a Task-accepted slug. "
    "After writing .cursor/agents/<name>.md (valid frontmatter plus non-empty body, "
    "model: inherit), tell the user to Reload Window before Task can use "
    "subagent_type=<name>. Until then use stock or plugin types. Never prefer a removed "
    "model-pool list."
)



CATALOG_INDEX_PATHS = {
    "skills": "~/.cursor/plugins/local/always-use-all-skills/catalogs/skills-index.json",
    "plugins": "~/.cursor/plugins/local/always-use-all-skills/catalogs/plugins-index.json",
    "rules": "~/.cursor/plugins/local/always-use-all-skills/catalogs/rules-index.json",
}


def expand_path(path: str) -> str:
    return os.path.expanduser(path)


def normalize_path(path: str) -> str:
    expanded = expand_path(path)
    try:
        return os.path.realpath(expanded)
    except OSError:
        return expanded


def paths_equal(a: str, b: str) -> bool:
    return normalize_path(a) == normalize_path(b)


def is_hook_followup_prompt(prompt: str) -> bool:
    upper = prompt.strip().upper()
    prefixes = (
        "STOP BLOCKED",
        "VOICE LINT FAILED",
        "HOOK ENFORCEMENT",
        "MEMORY FORCE",
        "HEADROOM FORCE",
        "[RALPH LOOP",
    )
    return any(upper.startswith(prefix) for prefix in prefixes)


def is_hook_meta_text(text: str) -> bool:
    lower = text.lower()
    markers = (
        "stop blocked",
        "voice lint failed",
        "hook enforcement",
        "read-gate",
        "stop hook",
        "beforesubmitprompt",
        "session-manifest",
        "memory force",
        "headroom force",
        "project memory",
    )
    return any(marker in lower for marker in markers)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Always-on mandatory ids: satisfied by alwaysApply rules / voice stack (no stop spam).
ALWAYS_APPLY_MANDATORY_IDS: frozenset[str] = frozenset(
    item["id"] for item in MANDATORY_READS
)


def _mark_always_apply_mandatory(entry: dict[str, Any]) -> bool:
    """Set read + satisfied_by for always-on mandatory entries. Returns True if changed."""
    if entry.get("id") not in ALWAYS_APPLY_MANDATORY_IDS:
        return False
    changed = False
    if not entry.get("read"):
        entry["read"] = True
        changed = True
    if entry.get("satisfied_by") != "alwaysApply":
        entry["satisfied_by"] = "alwaysApply"
        changed = True
    return changed


def fresh_manifest() -> dict[str, Any]:
    mandatory = []
    for item in MANDATORY_READS:
        entry = {**item, "read": False}
        _mark_always_apply_mandatory(entry)
        mandatory.append(entry)
    return {
        "generated_at": now_iso(),
        "prompt": "",
        "mandatory_reads": mandatory,
        "routed_items": [],
        "conditional_reads": [],
        "memory_writes": [],
        "nontrivial": False,
        "headroom_used": False,
        "max_tool_output_bytes": 0,
    }


def repair_manifest(data: dict[str, Any]) -> bool:
    changed = False

    for item in data.get("mandatory_reads", []):
        if _mark_always_apply_mandatory(item):
            changed = True

    prompt = str(data.get("prompt", ""))
    if is_hook_followup_prompt(prompt):
        if data.get("routed_items"):
            data["routed_items"] = []
            changed = True

    return changed


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        return fresh_manifest()
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fresh_manifest()
    if "mandatory_reads" not in data:
        data["mandatory_reads"] = [{**item, "read": False} for item in MANDATORY_READS]
    if "routed_items" not in data:
        data["routed_items"] = []
    if "conditional_reads" not in data:
        data["conditional_reads"] = []
    if "memory_writes" not in data:
        data["memory_writes"] = []
    if "nontrivial" not in data:
        data["nontrivial"] = False
    if "headroom_used" not in data:
        data["headroom_used"] = False
    if "max_tool_output_bytes" not in data:
        data["max_tool_output_bytes"] = 0
    # Ensure new mandatory ids exist
    existing_ids = {item.get("id") for item in data.get("mandatory_reads", [])}
    for item in MANDATORY_READS:
        if item["id"] not in existing_ids:
            data.setdefault("mandatory_reads", []).append({**item, "read": False})
    if repair_manifest(data):
        save_manifest(data)
    return data


def save_manifest(manifest: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def parse_hook_input(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"prompt": raw}


def extract_prompt(hook: dict[str, Any]) -> str:
    for key in ("prompt", "user_message", "message", "text"):
        val = hook.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    msgs = hook.get("messages")
    if isinstance(msgs, list):
        for msg in reversed(msgs):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
    return ""


def find_transcript_path(hook: dict[str, Any]) -> Path | None:
    direct = hook.get("transcript_path")
    if direct:
        path = Path(str(direct))
        if path.is_file():
            return path

    conversation_id = hook.get("conversation_id")
    if not conversation_id:
        return None

    roots = [
        Path.home() / ".cursor/projects",
        Path.home() / ".cursor" / "agent-transcripts",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        matches = list(root.rglob(f"{conversation_id}.jsonl"))
        if matches:
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return matches[0]
    return None


def last_assistant_text(hook: dict[str, Any]) -> str:
    for key in (
        "last_agent_response",
        "agent_response",
        "response",
        "text",
        "content",
    ):
        val = hook.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    transcript = find_transcript_path(hook)
    if not transcript:
        return ""

    parts: list[str] = []
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("role") != "assistant":
            continue
        message = event.get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = str(block.get("text", "")).strip()
                    if text:
                        parts.append(text)
    return parts[-1] if parts else ""


def unread_mandatory(manifest: dict[str, Any]) -> list[str]:
    unread: list[str] = []
    for item in manifest.get("mandatory_reads", []):
        if item.get("read"):
            continue
        if item.get("satisfied_by") == "alwaysApply":
            continue
        unread.append(str(item.get("path", "")))
    return [p for p in unread if p]


def unread_routed(manifest: dict[str, Any], *, min_score: float = 15.0, max_items: int = 3) -> list[str]:
    unread: list[str] = []
    skills = [
        item
        for item in manifest.get("routed_items", [])
        if item.get("type") == "skill" and not item.get("read")
    ]
    skills.sort(key=lambda i: float(i.get("score") or 0), reverse=True)
    for item in skills[:max_items]:
        score = float(item.get("score") or 0)
        if score < min_score:
            continue
        path = str(item.get("path", ""))
        if path:
            unread.append(path)
    return unread


def extract_read_path(hook: dict[str, Any]) -> str:
    candidates: list[str] = []
    tool_input = hook.get("tool_input") or hook.get("input") or {}
    if isinstance(tool_input, dict):
        for key in ("path", "target_file", "file_path"):
            val = tool_input.get(key)
            if isinstance(val, str) and val.strip():
                candidates.append(val.strip())

    tool_use = hook.get("tool_use") or {}
    if isinstance(tool_use, dict):
        inner = tool_use.get("input") or tool_use.get("arguments") or {}
        if isinstance(inner, dict):
            for key in ("path", "target_file", "file_path"):
                val = inner.get(key)
                if isinstance(val, str) and val.strip():
                    candidates.append(val.strip())

    return candidates[0] if candidates else ""


def mark_path_read(manifest: dict[str, Any], read_path: str) -> bool:
    changed = False
    normalized = normalize_path(read_path)

    for item in manifest.get("mandatory_reads", []):
        if paths_equal(str(item.get("path", "")), read_path):
            if not item.get("read"):
                item["read"] = True
                changed = True

    for item in manifest.get("routed_items", []):
        if paths_equal(str(item.get("path", "")), read_path):
            if not item.get("read"):
                item["read"] = True
                changed = True

    skills_root = normalize_path("~/.cursor/skills/")
    plugins_root = normalize_path("~/.cursor/plugins/")
    is_catalog_path = (
        normalized.startswith(skills_root)
        or normalized.startswith(plugins_root)
        or normalized.endswith(".mdc")
        or "/SKILL.md" in normalized
    )
    if is_catalog_path and normalized not in manifest.get("conditional_reads", []):
        manifest.setdefault("conditional_reads", []).append(normalized)
        changed = True

    return changed


def build_enforcement_message(
    routed: dict[str, Any],
    *,
    for_subagent: bool = False,
) -> str:
    parts: list[str] = []

    skills = routed.get("relevant_skills") or []
    plugins = routed.get("relevant_plugins") or []
    rules = routed.get("relevant_rules") or []

    if skills:
        paths = ", ".join(s["path"] for s in skills if s.get("path"))
        parts.append(f"ROUTER MATCHES (Read and apply): {paths}")
    if plugins:
        paths = ", ".join(p["path"] for p in plugins if p.get("path"))
        parts.append(f"ROUTER PLUGINS (Read and apply if relevant): {paths}")
    if rules:
        paths = ", ".join(r["path"] for r in rules if r.get("path"))
        parts.append(f"ROUTER RULES (Read and apply if relevant): {paths}")

    if routed.get("catalog_evaluation_required"):
        parts.append("ROUTER CONFIDENCE LOW: re-check the light catalog judgment map in the always-on rule.")

    # Short pointer only. The full force text lives in the always-on rules
    # (already in context) so it is not repeated here every prompt.
    parts.append(
        "Always-on rules govern PROJECT MEMORY FORCE, HEADROOM FORCE, ADVISOR "
        "(judgment), SUBAGENTS, and the light catalog judgment. The stop hook enforces "
        "mandatory reads, memory, Headroom, and voice lint. Route matches above are the "
        "only per-prompt additions; Read and apply those that fit."
    )

    if for_subagent:
        parts.insert(0, "SUBAGENT: inherit the parent skill/plugin/rule policy.")

    return " | ".join(parts)


def update_manifest_routing(manifest: dict[str, Any], prompt: str, routed: dict[str, Any]) -> None:
    manifest["prompt"] = prompt[:2000]
    manifest["routed_at"] = now_iso()
    routed_items: list[dict[str, Any]] = []
    for kind, key in (
        ("skill", "relevant_skills"),
        ("plugin", "relevant_plugins"),
        ("rule", "relevant_rules"),
    ):
        for item in routed.get(key) or []:
            path = item.get("path")
            if not path:
                continue
            routed_items.append(
                {
                    "type": kind,
                    "name": item.get("name", ""),
                    "path": path,
                    "score": item.get("score"),
                    "read": False,
                }
            )
    manifest["routed_items"] = routed_items
    if routed_items:
        manifest["nontrivial"] = True


def is_memory_path(path: str) -> bool:
    norm = normalize_path(path).replace("\\", "/").lower()
    return "/.cursor/memory/" in norm or norm.endswith("/.cursor/memory")


def mark_memory_write(manifest: dict[str, Any], path: str) -> bool:
    if not path or not is_memory_path(path):
        return False
    normalized = normalize_path(path)
    writes = manifest.setdefault("memory_writes", [])
    if normalized not in writes:
        writes.append(normalized)
        manifest["nontrivial"] = True
        return True
    return False


def extract_tool_path(hook: dict[str, Any]) -> str:
    """Best-effort path from Read/Write/StrReplace/Edit hook payloads."""
    for key in ("path", "file_path", "filePath", "target"):
        val = hook.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    tool_input = hook.get("tool_input") or hook.get("input") or hook.get("args") or {}
    if isinstance(tool_input, dict):
        for key in ("path", "file_path", "filePath", "target"):
            val = tool_input.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    # nested common shapes
    for nest in ("tool", "params", "arguments"):
        block = hook.get(nest)
        if isinstance(block, dict):
            for key in ("path", "file_path", "filePath"):
                val = block.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    return ""
