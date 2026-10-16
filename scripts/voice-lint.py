#!/usr/bin/env python3
"""Shared voice-policy linter for master controller hooks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

EM_DASH = "\u2014"
EN_DASH = "\u2013"

CLICHES = [
    "innovation",
    "utilize",
    "leverage",
    "seamless",
    "robust",
    "transforming",
    "enhance",
    "cutting-edge",
    "game-changer",
    "delve",
    "tapestry",
    "landscape",
    "paradigm",
    "synergy",
    "holistic",
    "streamline",
    "empower",
    "unlock",
    "elevate",
    "foster",
    "navigate",
    "comprehensive",
    "pivotal",
    "underscore",
    "testament",
    "crucial",
    "vibrant",
    "bustling",
    "nestled",
]

META_PHRASES = [
    "here's your draft",
    "here is your draft",
    "i hope this helps",
    "let me know if",
    "feel free to",
    "happy to help",
    "great question",
    "certainly!",
    "absolutely!",
    "of course!",
    "as an ai",
    "as a language model",
    "in conclusion",
    "to summarize",
    "in summary",
    "hope that helps",
    "does that make sense",
]

WORKFLOW_RE = re.compile(r"\bworkflow\b", re.IGNORECASE)

HOOK_META_MARKERS = (
    "stop blocked",
    "voice lint failed",
    "hook enforcement",
    "read-gate",
    "stop hook",
    "beforesubmitprompt",
    "session-manifest",
)


def strip_literals(text: str) -> str:
    """Remove quoted/backticked spans so policy mentions do not false-positive."""
    text = re.sub(r'"[^"]*"', '""', text)
    text = re.sub(r"'[^']*'", "''", text)
    text = re.sub(r"`[^`]*`", "``", text)
    return text


def is_hook_meta_text(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in HOOK_META_MARKERS)


def excerpt(text: str, start: int, length: int = 60) -> str:
    snippet = text[max(0, start - 20) : start + length]
    return snippet.replace("\n", " ").strip()


def lint_text(text: str) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    lower = text.lower()
    prose = strip_literals(text)
    prose_lower = prose.lower()

    for idx, ch in enumerate(text):
        if ch in (EM_DASH, EN_DASH):
            violations.append({"rule": "em_dash", "excerpt": excerpt(text, idx)})

    for match in WORKFLOW_RE.finditer(prose):
        violations.append({"rule": "workflow", "excerpt": excerpt(text, match.start())})

    for cliche in CLICHES:
        for match in re.finditer(rf"\b{re.escape(cliche)}\b", prose_lower):
            violations.append({"rule": f"cliche:{cliche}", "excerpt": excerpt(text, match.start())})

    for phrase in META_PHRASES:
        pos = lower.find(phrase)
        if pos >= 0:
            violations.append({"rule": f"meta:{phrase}", "excerpt": excerpt(text, pos)})

    return {"pass": len(violations) == 0, "violations": violations}


def last_assistant_text_from_transcript(path: Path) -> str:
    if not path.is_file():
        return ""

    parts: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
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
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))

    return parts[-1] if parts else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint text against voice policy")
    parser.add_argument("text", nargs="?", help="Text to lint")
    parser.add_argument("--from-transcript", type=Path, help="Read last assistant message")
    parser.add_argument("--file", type=Path, help="Lint file contents")
    args = parser.parse_args()

    text = args.text or ""
    if args.from_transcript:
        text = last_assistant_text_from_transcript(args.from_transcript)
    elif args.file:
        text = args.file.read_text(encoding="utf-8", errors="replace")
    elif not text and not sys.stdin.isatty():
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw)
            text = (
                payload.get("text")
                or payload.get("content")
                or payload.get("response")
                or payload.get("agent_response")
                or payload.get("last_agent_response")
                or ""
            )
            if not text and payload.get("transcript_path"):
                text = last_assistant_text_from_transcript(Path(str(payload["transcript_path"])))
        except json.JSONDecodeError:
            text = raw

    result = lint_text(text)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    if not result["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
