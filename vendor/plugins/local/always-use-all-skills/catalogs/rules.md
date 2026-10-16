# Rules catalog (light)

Count: 13

- **always-use-all-skills** (`.cursor/rules/always-use-all-skills.mdc`) — always apply
  - always-use-all-skills
- **humanizer-stack** (`.cursor/rules/humanizer-stack.mdc`) — always apply
  - Always-on binder for humanizer + structural-humanizer.
- **project-memory** (`.cursor/rules/project-memory.mdc`) — always apply
  - Forced .cursor/memory/ create-read-write protocol for every workspace.
- **ponytail** (`ponytail/rules/ponytail.mdc`) — apply when relevant
  - ponytail
- **no-inline-imports** (`cursor-team-kit/rules/no-inline-imports.mdc`) — apply when relevant
  - no-inline-imports
- **typescript-exhaustive-switch** (`cursor-team-kit/rules/typescript-exhaustive-switch.mdc`) — apply when relevant
  - typescript-exhaustive-switch
- **rtk** (`.cursor/rules/rtk.mdc`) — always apply
  - Force RTK shell-output compression via preToolUse hook plus direct rtk read/grep/find.
- **mcptoon** (`.cursor/rules/mcptoon.mdc`) — always apply
  - Force mcptoon skill/tool resolution so full schemas stay out of context.
- **context-mode** (`.cursor/rules/context-mode.mdc`) — always apply
  - Force context-mode ctx_execute/ctx_search so raw output stays in the sandbox.
- **sqz-squeez** (`.cursor/rules/sqz-squeez.mdc`) — always apply
  - Force sqz + squeez reversible compression of tool output.
- **jcodemunch** (`.cursor/rules/jcodemunch.mdc`) — always apply
  - Force jCodeMunch symbol-level retrieval over whole-file reads.
- **claude-context** (`.cursor/rules/claude-context.mdc`) — always apply
  - Force Claude Context semantic code search; local Milvus + Ollama.
- **cce** (`.cursor/rules/cce.mdc`) — always apply
  - Force Code Context Engine context_search over whole-file reads.
