#!/usr/bin/env python3
"""subagentStart hook: remind subagents of skill policy."""

from __future__ import annotations

import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from master_hook_lib import build_enforcement_message, load_manifest


def main() -> int:
    manifest = load_manifest()
    routed = {
        "relevant_skills": [
            {"path": i.get("path"), "name": i.get("name")}
            for i in manifest.get("routed_items", [])
            if i.get("type") == "skill"
        ],
        "catalog_evaluation_required": True,
    }
    msg = build_enforcement_message(routed, for_subagent=True)
    print(json.dumps({"user_message": msg, "permission": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
