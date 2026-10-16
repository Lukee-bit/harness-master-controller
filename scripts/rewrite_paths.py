#!/usr/bin/env python3
"""Rewrite machine-specific absolute paths in catalog files.

Catalogs are built with portable `~/.cursor/...` paths, but older artifacts (or
a bundle taken from a different machine) may contain a hardcoded home path. This
rewrites any `${HOME}`-rooted absolute path back to `~`, so light installs on any
machine. It does not hardcode a username.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Any "/Users/<name>/" or "/home/<name>/" absolute home prefix.
HOME_ABS_RE = re.compile(r"^(?:/Users/[^/]+|/home/[^/]+)")

OLD_HASH = "68836ddaf5697224520f1847d90cdb90ca8babaa"
NEW_HASH = "fd878692de15a3069c21c8f429eb0b9f2fe178fa"


def rewrite_text(text: str) -> str:
    home = str(Path.home())
    # Home-rooted .cursor paths -> portable ~/.cursor form.
    text = text.replace(f"{home}/.cursor/", "~/.cursor/")
    text = text.replace(f"{home}/.cursor", "~/.cursor")
    # Any other user's /Users/<name> or /home/<name> root -> ~ (defensive).
    text = HOME_ABS_RE.sub("~", text)
    text = text.replace(OLD_HASH, NEW_HASH)
    return text


def rewrite_file(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    path.write_text(rewrite_text(content), encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: rewrite_paths.py <catalogs-dir>", file=sys.stderr)
        return 1
    catalogs = Path(sys.argv[1])
    for path in catalogs.glob("*"):
        if path.suffix in {".json", ".md"}:
            rewrite_file(path)
            print(f"Rewrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
