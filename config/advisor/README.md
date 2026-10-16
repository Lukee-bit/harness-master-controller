# Advisor (judgment) — Layer B

## What this is

Judgment-based Advisor for the light (and fat) controller:

1. The agent reasons whether a second opinion helps, and consults only when it does. No auto-enable.
2. **Model:** omit Task `model` or pass `inherit` (parent chat model), unless the user names a slug from this session's Task `available_subagent_models`. There is no light model-pool file. Cursor's Task allowlist is the only gate.
3. Consults follow the stock Advisor plugin checkpoints (major decision / stuck / before done).

Advisor is not a catalog skill. Install the Cursor Advisor plugin (local `~/.cursor/plugins/local/advisor` or marketplace when available).

## Install Advisor plugin

Prefer local install from https://github.com/cursor/plugins/tree/main/advisor if marketplace mis-resolves. Then Reload Window.

## Model policy

| Action | Model |
|--------|--------|
| Default consult / enable | `inherit` (or omit) |
| User names a slug | Use it only if Task accepts it |
| Task rejects a slug | Fall back to `inherit`; say so in one line |

Do not invent or prefer a slug list. Stock plugin docs may still mention Grok; if Task rejects that slug, keep `inherit`.

## Judgment behavior

Consult when warranted: major decision, stuck after real attempts, or before declaring a substantial task done. On request, one-off consult. Enable mode for a conversation only when a checkpoint consult is warranted. Never enable as a default.

```text
/advisor
/advisor inherit
/advisor off
/advisor status
/advisor ask …
/advisor nudge off
```

Prefer `/advisor nudge off` (or `"nudge": false` in state) so Advisor stays available for judgment consults without end-of-turn spam. The agent still consults only when a second opinion is useful (major decision / stuck / before done / on request).

## State example

See `state.example.json`. `"model": "inherit"` is the light default.
