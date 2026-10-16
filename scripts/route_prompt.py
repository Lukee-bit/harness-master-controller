#!/usr/bin/env python3
"""beforeSubmitPrompt hook: route skills and persist manifest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from master_hook_lib import (
    build_enforcement_message,
    extract_prompt,
    is_hook_followup_prompt,
    load_manifest,
    parse_hook_input,
    save_manifest,
    update_manifest_routing,
)


def main() -> int:
    raw = sys.stdin.read()
    hook = parse_hook_input(raw)
    prompt = extract_prompt(hook)

    manifest = load_manifest()
    if prompt and not is_hook_followup_prompt(prompt):
        env = {
            **os.environ,
            "MC_CATALOGS_DIR": str(
                Path.home() / ".cursor/plugins/local/always-use-all-skills/catalogs"
            ),
        }
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "skill-router.py"), prompt],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        try:
            routed = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            routed = {}
        update_manifest_routing(manifest, prompt, routed)
        save_manifest(manifest)
        agent_message = build_enforcement_message(routed)
    elif prompt and is_hook_followup_prompt(prompt):
        manifest["routed_items"] = []
        manifest["prompt"] = prompt[:200]
        save_manifest(manifest)
        agent_message = (
            "Complete the hook follow-up: apply fixes from the prior message, then respond. "
            "Do not re-route this meta message."
        )
    else:
        agent_message = build_enforcement_message({})

    print(json.dumps({"agent_message": agent_message}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
