#!/usr/bin/env python3
"""postToolUse hook: track mandatory/routed reads and .cursor/memory writes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from master_hook_lib import (
    extract_read_path,
    extract_tool_path,
    load_manifest,
    mark_memory_write,
    mark_path_read,
    parse_hook_input,
    save_manifest,
)


def _tool_output_bytes(hook: dict) -> int:
    """Best-effort size of a tool result, for the Headroom guardrail.

    Cursor payloads vary by event shape; look for common result keys and count
    the string length. Returns 0 when unknown.
    """
    for key in ("tool_output", "output", "result", "tool_result", "content", "text"):
        val = hook.get(key)
        if isinstance(val, str):
            return len(val)
        if isinstance(val, list):
            total = 0
            for item in val:
                if isinstance(item, str):
                    total += len(item)
                elif isinstance(item, dict):
                    total += len(json.dumps(item))
            if total:
                return total
        if isinstance(val, dict):
            return len(json.dumps(val))
    return 0


def main() -> int:
    raw = sys.stdin.read()
    hook = parse_hook_input(raw)

    tool_name = str(
        hook.get("tool_name")
        or hook.get("toolName")
        or hook.get("tool")
        or ""
    ).lower()

    manifest = load_manifest()
    changed = False

    # Track the largest tool output seen this turn (Headroom guardrail evidence).
    out_bytes = _tool_output_bytes(hook)
    if out_bytes > int(manifest.get("max_tool_output_bytes") or 0):
        manifest["max_tool_output_bytes"] = out_bytes
        changed = True

    # Any MCP headroom_* call marks Headroom as used this turn.
    if "headroom" in tool_name or "headroom" in raw.lower():
        if not manifest.get("headroom_used"):
            manifest["headroom_used"] = True
            changed = True

    read_path = extract_read_path(hook) or (
        extract_tool_path(hook) if "read" in tool_name else ""
    )
    if read_path and mark_path_read(manifest, read_path):
        changed = True
        print(f"Marked read: {read_path}", file=sys.stderr)

    write_path = extract_tool_path(hook)
    if write_path and (
        "write" in tool_name
        or "edit" in tool_name
        or "strreplace" in tool_name
        or tool_name in ("write", "editnotebook", "applypatch")
    ):
        if mark_memory_write(manifest, write_path):
            changed = True
            print(f"Marked memory write: {write_path}", file=sys.stderr)
            manifest["nontrivial"] = True
        elif write_path:
            # any file edit counts as nontrivial work
            if not manifest.get("nontrivial"):
                manifest["nontrivial"] = True
                changed = True

    if changed:
        save_manifest(manifest)

    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
