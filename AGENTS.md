# AGENTS.md

Instructions for AI coding agents (OpenAI Codex, GitHub Copilot, Cursor,
Windsurf, Amp, Devin) working in this repository. See <https://agentsmd.io>.

<!-- BEGIN sqz-guidance (auto-installed by sqz init; remove this block to disable) -->

## sqz

Pipe shell commands with long output (git log or diff, tests, builds,
`ls -la`) through sqz:

```bash
git status 2>&1 | /opt/homebrew/bin/sqz compress
```

Don't pipe interactive commands (REPLs, `ssh`), chains with `&&`, `||`
or `;`, output redirected to a file, or short output. If that binary is
missing, run commands without it.

When the sqz MCP tools are available, prefer `sqz_read_file`, `sqz_grep`
and `sqz_list_dir` over the built-in read, grep and `ls` for long or
repeated reads, and use `sqz_recall` to find output seen earlier.

A `§ref:HASH§` stands in for output you have already seen, and
`§ref:HASH:L40-80§` for lines 40-80 of it. Get the text back with the
`expand` tool or `/opt/homebrew/bin/sqz expand <token>`. `«A1»` stands for the
phrase listed for it under `[Abbreviations]` at the top of the output.
For output without refs or abbreviations, put `SQZ_NO_DEDUP=1` or
`SQZ_NO_ABBREV=1` right before `/opt/homebrew/bin/sqz compress`.

<!-- END sqz-guidance -->

## Code Exploration Policy

jCodeMunch-MCP indexes this repository's symbols and how they relate. Use it where it is the cheaper route, and the built-in tools (Grep, Glob, Read) where they are.
- **Relationships are what the index is for:** who imports a symbol, where a name is used, what a change breaks, who calls a function, what is unreachable.
- **A name you already know, or a file you are about to work in:** the built-in search and `Read` are often as cheap. Take whichever is fewer steps.
- **On a small repository** the built-in tools are usually the cheaper route for finding and reading code.
- The harness requires a `Read` before `Edit`/`Write`.

This server runs the **front door** surface: three tools reach every jCodeMunch capability, so the tool list stays small and the catalogue is fetched only when you need it.

**Before the first jCodeMunch call in a session** (skip it when the task needs none):
- `order { "action": "resolve_repo", "args": { "path": "." } }` — confirm the project is indexed. If it is not: `order { "action": "index_folder", "args": { "path": "." } }`

**Then, for a task the index suits:**
- Know what you want → `order { "action": "<name>", "args": { ... } }`
- Know the goal, not the tool → `route { "query": "your task in a sentence" }` picks the action and shapes the arguments
- Want to see what exists → `menu { "query": "what you are trying to do" }` returns matching actions with example arguments
- Want the whole catalogue and the usage rules → `jcodemunch_guide`

`menu` and `jcodemunch_guide` list every action this server can run, including ones absent from your tool list. That is expected: the front door is the way to call them.

**Interpreting results:**
- A search proves absence only when the scan is citable: `_meta.verdict.evidence_ref` holds an `absent:` token, or, where `_meta.verdict` is not shown, `_meta.absence_evidence.citable` is `true`. Then report the gap; do not re-search with different wording. A `no_implementation_found` verdict, a `state` of `absent` or an empty result is not proof on its own: read the note or `absence_blocked_by`, re-index if it names the index, then search again.
- `source: ""` alongside `source_status` means the body could not be read, not that the symbol is empty.

**After editing files:**
- With PostToolUse hooks installed (Claude Code), edited files are reindexed automatically.
- Otherwise `order { "action": "register_edit", "args": { "paths": [...] } }` after an edit, batched for bulk changes.

**Optional:** announce your model once so the server can size its answers: `announce_model { "model": "<your-model-id>" }`.

