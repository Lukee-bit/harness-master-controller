#!/usr/bin/env python3
"""Force-start Headroom MCP with agent-90 compression for Cursor.

Seeds the agent-90 savings profile into the process env, patches MCP compress
to always pass CompressConfig(agent-90), then runs the MCP stdio server.

Proxy token savings still require Cursor Override OpenAI Base URL →
http://127.0.0.1:8787/v1.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

AGENT_ENV_DEFAULTS = {
    "HEADROOM_FORCE_KOMPRESS": "1",
    "HEADROOM_MODE": "token",
    "HEADROOM_TARGET_RATIO": "0.10",
    "HEADROOM_MIN_TOKENS": "120",
    "HEADROOM_COMPRESS_SYSTEM_MESSAGES": "1",
    "HEADROOM_COMPRESS_USER_MESSAGES": "1",
    "HEADROOM_CODE_AWARE_ENABLED": "1",
    "HEADROOM_PROTECT_ANALYSIS_CONTEXT": "1",
    # MCP wraps one tool message; do not skip it as "recent".
    "HEADROOM_PROTECT_RECENT": "0",
    "HEADROOM_ACCURACY_GUARD": "strict",
    "HEADROOM_PROXY_URL": "http://127.0.0.1:8787",
}


def _seed_env() -> None:
    os.environ["HEADROOM_SAVINGS_PROFILE"] = "agent-90"
    for key, value in AGENT_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)


# Seed the env BEFORE importing headroom: some headroom modules read os.environ
# at import time, so the profile must be present first.
_seed_env()

try:
    import headroom.ccr.mcp_server as mcp_mod
    from headroom.agent_savings import apply_agent_savings_profile, seed_proxy_env_defaults
    from headroom.ccr.mcp_server import main as mcp_main
    from headroom.compress import CompressConfig, compress

    HEADROOM_IMPORT_OK = True
except Exception:
    mcp_mod = None
    HEADROOM_IMPORT_OK = False


def _finish_env() -> None:
    if HEADROOM_IMPORT_OK:
        try:
            seed_proxy_env_defaults()
        except Exception:
            pass
    # Profile seed sets protect_recent=2; MCP single-message calls need 0.
    os.environ["HEADROOM_PROTECT_RECENT"] = "0"
    os.environ["HEADROOM_SAVINGS_PROFILE"] = "agent-90"


def _patch_mcp_compress() -> None:
    """Make headroom_compress always use agent-90 CompressConfig."""
    if not HEADROOM_IMPORT_OK:
        return

    server_cls = getattr(mcp_mod, "HeadroomMCPServer", None)
    if server_cls is None:
        return

    def _compress_content(self, content: str):  # type: ignore[no-untyped-def]
        messages = [{"role": "tool", "content": content}]
        cfg = CompressConfig(savings_profile="agent-90")
        apply_agent_savings_profile(cfg, "agent-90")
        cfg.protect_recent = 0
        cfg.min_tokens_to_compress = min(int(cfg.min_tokens_to_compress or 120), 120)
        result = compress(messages, model="claude-sonnet-4-5-20250929", config=cfg)

        compressed_content = result.messages[0].get("content", content)
        input_tokens = result.tokens_before
        output_tokens = result.tokens_after

        store = self._get_local_store()
        hash_key = store.store(
            original=content,
            compressed=compressed_content
            if isinstance(compressed_content, str)
            else json.dumps(compressed_content),
            original_tokens=input_tokens,
            compressed_tokens=output_tokens,
            compression_strategy="mcp_compress",
            ttl=mcp_mod.MCP_SESSION_TTL,
        )
        strategy = (
            ", ".join(result.transforms_applied) if result.transforms_applied else "passthrough"
        )
        self._stats.record_compression(input_tokens, output_tokens, strategy)
        savings_pct = (
            round((1 - output_tokens / input_tokens) * 100, 1) if input_tokens > 0 else 0
        )
        return {
            "compressed": compressed_content,
            "hash": hash_key,
            "original_tokens": input_tokens,
            "compressed_tokens": output_tokens,
            "tokens_saved": max(0, input_tokens - output_tokens),
            "savings_percent": savings_pct,
            "transforms": result.transforms_applied,
            "note": (
                f"Original stored with hash={hash_key}. "
                f"Use mcp__headroom__{mcp_mod.CCR_TOOL_NAME} to get full content later."
            ),
        }

    server_cls._compress_content = _compress_content  # type: ignore[method-assign]


def main() -> None:
    _seed_env()
    _finish_env()
    _patch_mcp_compress()
    sys.argv = [sys.argv[0], *sys.argv[1:]]
    asyncio.run(mcp_main())


if __name__ == "__main__":
    main()
