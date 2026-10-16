#!/usr/bin/env python3
"""preToolUse Task hook: inject skill policy into subagent prompts."""

from __future__ import annotations

import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from master_hook_lib import build_enforcement_message, load_manifest, parse_hook_input


def main() -> int:
    raw = sys.stdin.read()
    hook = parse_hook_input(raw)

    tool_input = hook.get("tool_input") or hook.get("input") or {}
    prompt = str(tool_input.get("prompt") or "")
    if not prompt:
        print("{}")
        return 0

    manifest = load_manifest()
    routed = {
        "relevant_skills": [
            {
                "path": item.get("path"),
                "name": item.get("name"),
                "score": item.get("score"),
            }
            for item in manifest.get("routed_items", [])
            if item.get("type") == "skill"
        ],
        "relevant_plugins": [
            {
                "path": item.get("path"),
                "name": item.get("name"),
                "score": item.get("score"),
            }
            for item in manifest.get("routed_items", [])
            if item.get("type") == "plugin"
        ],
        "relevant_rules": [
            {
                "path": item.get("path"),
                "name": item.get("name"),
                "score": item.get("score"),
            }
            for item in manifest.get("routed_items", [])
            if item.get("type") == "rule"
        ],
        "catalog_evaluation_required": True,
    }

    policy = build_enforcement_message(routed, for_subagent=True)
    if policy in prompt:
        print("{}")
        return 0

    updated_prompt = f"{policy}\n\n---\n\n{prompt}"
    updated_input = {**tool_input, "prompt": updated_prompt}
    print(json.dumps({"updated_input": updated_input}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
