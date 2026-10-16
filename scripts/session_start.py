#!/usr/bin/env python3
"""sessionStart hook: initialize the session manifest.

The full force policy lives in the always-on rules (voice.mdc, project-memory.mdc,
mcptoon.mdc, always-use-all-skills.mdc), which are already in context. Repeating
it here would add ~1.9KB of persistent context for no new information, so this
hook writes the manifest and emits only a short pointer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from master_hook_lib import MANDATORY_READS, fresh_manifest, save_manifest


def main() -> int:
    manifest = fresh_manifest()
    save_manifest(manifest)

    print("Master controller session manifest written.", file=sys.stderr)
    for item in MANDATORY_READS:
        print(f"  MANDATORY READ: {item['path']}", file=sys.stderr)

    payload = {
        "additional_context": (
            "Master controller active. Always-on rules govern voice bans, project "
            "memory, Headroom, and the mcptoon gateway; Read the mandatory spines "
            "before non-trivial work."
        )
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
