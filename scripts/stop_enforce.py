#!/usr/bin/env python3
"""stop hook: unread routes + memory nudge + voice lint."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from master_hook_lib import (  # noqa: E402
    is_hook_followup_prompt,
    is_hook_meta_text,
    last_assistant_text,
    load_manifest,
    parse_hook_input,
    unread_mandatory,
)

MAX_LOOPS = 3
HIGH_SCORE = 12.0


def unread_high_score_routes(manifest: dict) -> list[dict]:
    out = []
    for item in manifest.get("routed_items") or []:
        if item.get("read"):
            continue
        if item.get("type") not in ("skill", "plugin", "rule"):
            continue
        score = item.get("score")
        try:
            score_f = float(score) if score is not None else 0.0
        except (TypeError, ValueError):
            score_f = 0.0
        if score_f >= HIGH_SCORE:
            out.append(item)
    return out


def main() -> int:
    raw = sys.stdin.read()
    hook = parse_hook_input(raw)

    loop_count = int(hook.get("loop_count") or 0)
    status = str(hook.get("status", ""))

    if status != "completed":
        print("{}")
        return 0

    if loop_count >= MAX_LOOPS:
        print("{}")
        return 0

    assistant_text = last_assistant_text(hook)
    if not assistant_text.strip():
        print("{}")
        return 0

    if is_hook_followup_prompt(assistant_text) or is_hook_meta_text(assistant_text):
        print("{}")
        return 0

    try:
        manifest = load_manifest()
    except Exception:
        manifest = {}

    unread = unread_high_score_routes(manifest)
    if unread and loop_count == 0:
        names = ", ".join(f"{u.get('name')} ({u.get('path')})" for u in unread[:5])
        msg = (
            "STOP BLOCKED: high-score light catalog routes were not Read this turn. "
            "Use the Read tool on each path, apply them, then finish the task. Missing: "
            + names
        )
        print(json.dumps({"followup_message": msg}))
        return 0

    missing_mandatory = unread_mandatory(manifest)
    if missing_mandatory and loop_count == 0:
        names = ", ".join(missing_mandatory[:5])
        msg = (
            "STOP BLOCKED: mandatory reads were not completed this turn. "
            "Use the Read tool on each path, apply them, then finish the task. Missing: "
            + names
        )
        print(json.dumps({"followup_message": msg}))
        return 0

    # Memory nudge after routes cleared, before voice lint
    nontrivial = bool(manifest.get("nontrivial") or manifest.get("routed_items"))
    memory_writes = manifest.get("memory_writes") or []
    if nontrivial and not memory_writes and loop_count <= 1:
        msg = (
            "MEMORY FORCE: This turn looks non-trivial but no writes under "
            "`.cursor/memory/` were tracked. Create the tree if missing, then update "
            "`activeContext.md` and append a dated entry to `progress.md` "
            "(or append `no durable updates`). Never store secrets. Then finish."
        )
        print(json.dumps({"followup_message": msg}))
        return 0

    # Headroom guardrail: fire only when a genuinely large tool output was seen
    # this turn and no Headroom call happened. The always-on rules already carry
    # the mandate, so an unconditional reminder just costs tokens on turns with
    # nothing to compress. Threshold ~1500 tokens (~6000 bytes).
    HEADROOM_OUTPUT_BYTES = 6000
    max_out = int(manifest.get("max_tool_output_bytes") or 0)
    if (
        max_out >= HEADROOM_OUTPUT_BYTES
        and loop_count <= 1
        and not (manifest.get("headroom_used") or False)
    ):
        lower = assistant_text.lower()
        if "headroom_compress" not in lower and "headroom_stats" not in lower and "headroom_retrieve" not in lower:
            msg = (
                "HEADROOM FORCE: a large tool result (~"
                + str(max_out // 4)
                + " tokens) was seen this turn but no Headroom call was made. "
                "Call headroom_compress on it before finishing."
            )
            print(json.dumps({"followup_message": msg}))
            return 0

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "voice-lint.py"), assistant_text],
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

    summary = "; ".join(f"{v.get('rule')}: {v.get('excerpt')}" for v in violations[:6])
    msg = (
        "VOICE LINT FAILED. Rewrite your last user-facing response before stopping. "
        "Re-apply humanizer-stack (humanizer + structural-humanizer), human-voice-rewrite, and unslop. Fix: "
        + summary
    )
    print(json.dumps({"followup_message": msg}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
