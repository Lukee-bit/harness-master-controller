#!/usr/bin/env python3
"""afterTabFileEdit hook: lint prose edits for voice policy."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def main() -> int:
    raw = sys.stdin.read()
    try:
        hook = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return 0

    file_path = str(hook.get("file_path") or hook.get("path") or "")
    content = hook.get("content") or hook.get("new_content") or hook.get("edited_content") or ""
    if not content and file_path:
        path = Path(file_path).expanduser()
        if path.is_file():
            content = path.read_text(encoding="utf-8", errors="replace")

    if not content:
        print("{}")
        return 0

    lower_path = file_path.lower()
    if not lower_path.endswith((".md", ".txt", ".mdc")):
        print("{}")
        return 0

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "voice-lint.py"), content],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        print("{}")
        return 0

    try:
        lint = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        print("{}")
        return 0

    violations = lint.get("violations") or []
    if not violations:
        print("{}")
        return 0

    summary = "; ".join(f"{v.get('rule')}: {v.get('excerpt')}" for v in violations[:5])
    print(
        json.dumps(
            {
                "agent_message": (
                    "Tab prose lint: remove banned voice patterns before accepting this edit. "
                    + summary
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
