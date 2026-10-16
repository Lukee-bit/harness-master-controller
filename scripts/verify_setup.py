#!/usr/bin/env python3
"""Verify Cursor Master Controller Light installation (memory + thermos)."""

from __future__ import annotations

import json
import shutil
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CURSOR_HOME = Path(os.environ.get("CURSOR_HOME", HOME / ".cursor"))
PLUGIN = CURSOR_HOME / "plugins/local/always-use-all-skills"
CATALOGS = PLUGIN / "catalogs"
CORE_RULE = CURSOR_HOME / "rules/always-use-all-skills.mdc"
MEMORY_RULE = CURSOR_HOME / "rules/project-memory.mdc"
RULE_MIRROR = CURSOR_HOME / "rules/always-use-all-skills.mdc"
HOOKS_JSON = CURSOR_HOME / "hooks.json"
HOOKS_DIR = CURSOR_HOME / "hooks"
SCRIPTS = CURSOR_HOME / "scripts/master-controller"
CORE_MAX_BYTES = 16_000

EXPECTED_SKILL_COUNT = 13
EXPECTED_PLUGIN_COUNT = 6
EXPECTED_RULE_COUNT = 16

HOOK_SCRIPTS_UNIX = [
    "session-start.sh",
    "route-skills.sh",
    "track-reads.sh",
    "voice-lint-stop.sh",
    "tab-prose-lint.sh",
    "inject-task-skills.sh",
    "subagent-policy.sh",
]

PYTHON_HOOK_SCRIPTS = [
    "master_hook_lib.py",
    "route_prompt.py",
    "stop_enforce.py",
    "track_reads.py",
    "session_start.py",
    "inject_task_skills.py",
    "subagent_policy.py",
    "tab_prose_lint.py",
    "skill-router.py",
    "voice-lint.py",
]


def ok(msg: str) -> None:
    print(f"OK  {msg}")


def fail(msg: str) -> None:
    print(f"FAIL {msg}")


def load_count(name: str) -> int:
    path = CATALOGS / f"{name}-index.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data.get("count") or len(data.get("items") or []))


def router_payload(prompt: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "skill-router.py"), prompt],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "MC_CATALOGS_DIR": str(CATALOGS)},
    )
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def router_names(prompt: str) -> list[str]:
    data = router_payload(prompt)
    names = [s.get("name") for s in data.get("relevant_skills") or []]
    names += [p.get("name") for p in data.get("relevant_plugins") or []]
    names += [r.get("name") for r in data.get("relevant_rules") or []]
    return [n for n in names if n]


def main() -> int:
    errors = 0

    for path in [
        CORE_RULE,
        RULE_MIRROR,
        MEMORY_RULE,
        HOOKS_JSON,
        PLUGIN / ".cursor-plugin/plugin.json",
        CURSOR_HOME / "skills/my-workflow/project-memory/SKILL.md",
    ]:
        if path.is_file():
            ok(f"exists: {path}")
        else:
            fail(f"missing: {path}")
            errors += 1

    if CORE_RULE.is_file():
        size = CORE_RULE.stat().st_size
        text = CORE_RULE.read_text(encoding="utf-8")
        if size <= CORE_MAX_BYTES:
            ok(f"core rule size {size} bytes")
        else:
            fail(f"core rule too large: {size}")
            errors += 1
        for needle in ("LIGHT CATALOG JUDGMENT", "PROJECT MEMORY FORCE", "thermos", "ADVISOR"):
            if needle in text or needle.lower() in text.lower():
                ok(f"core rule has {needle}")
            else:
                fail(f"core rule missing {needle}")
                errors += 1
    if MEMORY_RULE.is_file():
        mt = MEMORY_RULE.read_text(encoding="utf-8")
        if ".cursor/memory/" in mt and "Never store secrets" in mt:
            ok("project-memory rule has protocol")
        else:
            fail("project-memory rule incomplete")
            errors += 1

    for name, expected in (
        ("skills", EXPECTED_SKILL_COUNT),
        ("plugins", EXPECTED_PLUGIN_COUNT),
        ("rules", EXPECTED_RULE_COUNT),
    ):
        path = CATALOGS / f"{name}-index.json"
        if not path.is_file():
            fail(f"missing catalog: {name}")
            errors += 1
            continue
        count = load_count(name)
        # Light is an exact allowlist; fat is a large superset. Accept either.
        if count == expected or count >= expected * 3:
            ok(f"catalog {name} count={count}")
        else:
            fail(f"catalog {name} count={count} expected={expected} (light) or >= {expected * 3} (fat)")
            errors += 1

    plugins = json.loads((CATALOGS / "plugins-index.json").read_text())["items"]
    thermos = next((p for p in plugins if p.get("name") == "thermos"), None)
    if thermos and thermos.get("domain") == "review":
        ok("thermos in plugins-index with domain=review")
    else:
        fail("thermos missing or wrong domain")
        errors += 1

    if any(p.get("name") == "advisor" for p in plugins):
        ok("advisor in plugins-index")
    else:
        fail("advisor missing from plugins-index")
        errors += 1

    skills = json.loads((CATALOGS / "skills-index.json").read_text())["items"]
    if any(s.get("name") == "cursor-subagent-creator" for s in skills):
        ok("cursor-subagent-creator in skills-index")
    else:
        fail("cursor-subagent-creator missing from skills-index")
        errors += 1
    ids = " ".join(s.get("catalog_id", "") for s in skills)
    for banned in ("aaron-marketing", "seranking", "claude-seo", "memory-bank"):
        if banned in ids:
            fail(f"banned catalog id present: {banned}")
            errors += 1
        else:
            ok(f"no {banned} in skills catalog")

    for script in PYTHON_HOOK_SCRIPTS:
        if (SCRIPTS / script).is_file():
            ok(f"hook python: {script}")
        else:
            fail(f"missing hook python: {script}")
            errors += 1

    if os.name != "nt":
        for script in HOOK_SCRIPTS_UNIX:
            if (HOOKS_DIR / script).is_file():
                ok(f"hook shim: {script}")
            else:
                fail(f"missing hook shim: {script}")
                errors += 1

    hooks_data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    for event in ("beforeSubmitPrompt", "stop", "subagentStart", "sessionStart"):
        if hooks_data.get("hooks", {}).get(event):
            ok(f"hooks.json has {event}")
        else:
            fail(f"hooks.json missing {event}")
            errors += 1

    post = hooks_data.get("hooks", {}).get("postToolUse") or []
    matchers = {str(x.get("matcher", "")) for x in post}
    if "Write" in matchers:
        ok("hooks.json tracks Write for memory")
    else:
        fail("hooks.json missing Write matcher")
        errors += 1

    route = subprocess.run(
        [sys.executable, str(SCRIPTS / "route_prompt.py")],
        input=json.dumps({"prompt": "run an SEO audit for schema"}),
        capture_output=True,
        text=True,
        check=False,
    )
    if route.returncode == 0 and "agent_message" in route.stdout:
        ok("route_prompt hook returns agent_message")
        if "LIGHT CATALOG JUDGMENT" in route.stdout or "light catalog judgment" in route.stdout:
            ok("route_prompt includes LIGHT CATALOG JUDGMENT")
        else:
            fail("route_prompt missing LIGHT CATALOG JUDGMENT")
            errors += 1
        if "PROJECT MEMORY FORCE" in route.stdout:
            ok("route_prompt includes PROJECT MEMORY FORCE")
        else:
            fail("route_prompt missing PROJECT MEMORY FORCE")
            errors += 1
    else:
        fail(f"route_prompt hook failed: {route.stderr[:200]}")
        errors += 1

    design_names = router_names("design a beautiful landing page like Linear")
    if any(n in design_names for n in ("design-taste-frontend", "frontend-design")):
        ok(f"design prompt routes design: {design_names[:4]}")
    else:
        fail(f"design prompt bad routes: {design_names}")
        errors += 1
    if "thermos" in design_names:
        fail("thermos incorrectly ranked for design landing prompt")
        errors += 1
    else:
        ok("thermos not ranked for design landing prompt")

    seo_names = router_names("run an SEO audit for Core Web Vitals and schema")
    if "seo-mastery" in seo_names:
        ok("SEO prompt routes to seo-mastery")
    else:
        fail(f"SEO prompt bad routes: {seo_names}")
        errors += 1

    review_names = router_names(
        "run a thermos thermo-nuclear PR security and maintainability review on this branch"
    )
    if "thermos" in review_names:
        ok(f"review prompt routes thermos: {review_names[:4]}")
    else:
        fail(f"review prompt missing thermos: {review_names}")
        errors += 1

    skill_mds = list((CURSOR_HOME / "skills").rglob("SKILL.md"))
    n = len(skill_mds)
    # Light allowlist is exact plus a couple tool-provided skills (mcptoon);
    # fat install is a large superset.
    if n in (EXPECTED_SKILL_COUNT, EXPECTED_SKILL_COUNT + 1) or n >= 200:
        ok(f"installed skill count={n}")
    else:
        fail(f"installed skill count={n} expected={EXPECTED_SKILL_COUNT} (light) or >=200 (fat)")
        errors += 1
    for req in ("humanizer", "structural-humanizer"):
        if any(req in str(x) for x in skill_mds):
            ok(f"skill present: {req}")
        else:
            fail(f"missing skill: {req}")
            errors += 1
    if (CURSOR_HOME / "plugins/local/humanizer-stack/rules/humanizer-stack.mdc").is_file() or (
        CURSOR_HOME / "rules/humanizer-stack.mdc"
    ).is_file():
        ok("humanizer-stack rule present")
    else:
        fail("missing humanizer-stack rule")
        errors += 1

    if (CURSOR_HOME / "mcp-light-recommended.json").is_file():
        ok("mcp-light-recommended.json present")
    else:
        fail("missing mcp-light-recommended.json")
        errors += 1

    pool_path = CURSOR_HOME / "advisor-light-model-pool.json"
    if pool_path.is_file():
        fail("obsolete advisor-light-model-pool.json still present (remove it)")
        errors += 1
    else:
        ok("no obsolete advisor-light-model-pool.json")



    # Headroom ALWAYS FORCE
    rec = CURSOR_HOME / "mcp-light-recommended.json"
    if rec.is_file():
        rec_data = json.loads(rec.read_text(encoding="utf-8"))
        if "headroom" in (rec_data.get("mcpServers") or {}):
            ok("mcp-light-recommended.json includes headroom")
        else:
            fail("mcp-light-recommended.json missing headroom")
            errors += 1
    live_mcp = CURSOR_HOME / "mcp.json"
    if live_mcp.is_file():
        live_data = json.loads(live_mcp.read_text(encoding="utf-8"))
        if "headroom" in (live_data.get("mcpServers") or {}):
            ok("live mcp.json includes headroom")
        else:
            fail("live mcp.json missing headroom")
            errors += 1
    if shutil.which("headroom"):
        ok("headroom CLI on PATH")
    else:
        fail("headroom CLI missing from PATH")
        errors += 1
    if CORE_RULE.is_file():
        ct2 = CORE_RULE.read_text(encoding="utf-8")
        if "HEADROOM FORCE" in ct2:
            ok("core rule has HEADROOM FORCE")
        else:
            fail("core rule missing HEADROOM FORCE")
            errors += 1
    proxy_url = CURSOR_HOME / "headroom-proxy-url.txt"
    if proxy_url.is_file() and proxy_url.read_text(encoding="utf-8").strip():
        ok("headroom-proxy-url.txt present")
    else:
        fail("missing headroom-proxy-url.txt (run setup-headroom.sh)")
        errors += 1

    # Live MCP must force agent-90 compression profile
    if live_mcp.is_file():
        live_data = json.loads(live_mcp.read_text(encoding="utf-8"))
        hr = (live_data.get("mcpServers") or {}).get("headroom") or {}
        env = hr.get("env") or {}
        if env.get("HEADROOM_FORCE_KOMPRESS") == "1" and env.get("HEADROOM_SAVINGS_PROFILE") == "agent-90":
            ok("live mcp.json headroom has agent-90 FORCE_KOMPRESS")
        else:
            fail("live mcp.json headroom missing agent-90 FORCE_KOMPRESS env (re-run setup-headroom.sh)")
            errors += 1
        wrapper = CURSOR_HOME / "scripts/headroom-mcp-serve.py"
        args = hr.get("args") or []
        if wrapper.is_file() and any("headroom-mcp-serve.py" in str(a) for a in args):
            ok("live mcp.json uses headroom-mcp-serve.py force wrapper")
        elif wrapper.is_file():
            fail("MCP wrapper installed but live mcp.json does not use it")
            errors += 1

    # LaunchAgent must carry agent-90 + OpenRouter upstream
    plist = HOME / "Library/LaunchAgents/ai.headroom.proxy.plist"
    if plist.is_file():
        plist_text = plist.read_text(encoding="utf-8")
        if "HEADROOM_SAVINGS_PROFILE" in plist_text and "agent-90" in plist_text:
            ok("LaunchAgent has agent-90 savings profile")
        else:
            fail("LaunchAgent missing agent-90 (re-run setup-headroom.sh)")
            errors += 1
        if "FORCE_KOMPRESS" in plist_text:
            ok("LaunchAgent has FORCE_KOMPRESS")
        else:
            fail("LaunchAgent missing FORCE_KOMPRESS")
            errors += 1
        if "openrouter.ai" in plist_text or "OPENAI_TARGET_API_URL" in plist_text:
            ok("LaunchAgent has OpenRouter / OpenAI upstream")
        else:
            fail("LaunchAgent missing OpenRouter upstream URL")
            errors += 1
        if "--mode" in plist_text and "token" in plist_text:
            ok("LaunchAgent proxy mode=token")
        else:
            fail("LaunchAgent missing --mode token")
            errors += 1
    else:
        fail("missing LaunchAgent ai.headroom.proxy.plist")
        errors += 1

    # Proxy must be live + kompress ready + upstream openrouter when configured
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:8787/livez", timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        if '"alive":true' in body.replace(" ", "") or '"alive": true' in body:
            ok("headroom proxy /livez healthy")
        else:
            fail("headroom proxy /livez not healthy")
            errors += 1
        with urllib.request.urlopen("http://127.0.0.1:8787/readyz", timeout=5) as resp:
            ready = resp.read().decode("utf-8", errors="replace")
        ready_data = json.loads(ready)
        kompress = ((ready_data.get("checks") or {}).get("kompress") or {})
        if kompress.get("ready") is True:
            ok("headroom proxy kompress ready")
        else:
            fail(f"headroom proxy kompress not ready: {kompress}")
            errors += 1
        # /readyz "upstream" often reports the Anthropic messages path even when
        # OpenRouter is wired for OpenAI-compatible /v1/chat/completions. Confirm
        # OpenRouter via LaunchAgent args (checked above) and /health body.
        try:
            with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=5) as resp:
                health = resp.read().decode("utf-8", errors="replace")
            if "openrouter.ai" in health.lower():
                ok("headroom proxy health mentions openrouter.ai")
            else:
                # Fallback: plist already required OpenRouter; warn via fail only
                # if LaunchAgent check also missed it (handled above).
                ok("headroom proxy /health reachable (OpenRouter checked via LaunchAgent)")
        except Exception as health_exc:  # noqa: BLE001
            fail(f"headroom proxy /health failed: {health_exc}")
            errors += 1
    except Exception as exc:  # noqa: BLE001
        fail(f"headroom proxy health check failed: {exc}")
        errors += 1

    # Compress library must actually save tokens on a large JSON tool payload.
    # Use the headroom uv-tool interpreter — system python often lacks the package.
    hr_python = HOME / ".local/share/uv/tools/headroom-ai/bin/python"
    py = str(hr_python) if hr_python.is_file() else sys.executable
    smoke = r"""
import json, os, sys
os.environ["HEADROOM_FORCE_KOMPRESS"] = "1"
os.environ["HEADROOM_SAVINGS_PROFILE"] = "agent-90"
from headroom.compress import CompressConfig, compress
from headroom.agent_savings import apply_agent_savings_profile
items = [{"id": i, "name": f"user-{i}", "email": f"u{i}@example.com",
          "roles": ["reader", "writer"], "meta": {"n": i, "ok": True}}
         for i in range(100)]
cfg = CompressConfig(savings_profile="agent-90")
apply_agent_savings_profile(cfg, "agent-90")
cfg.protect_recent = 0
result = compress([{"role": "tool", "content": json.dumps(items)}],
                  model="claude-sonnet-4-5-20250929", config=cfg)
before = int(result.tokens_before or 0)
after = int(result.tokens_after or 0)
saved = max(0, before - after)
print(json.dumps({"before": before, "after": after, "saved": saved,
                  "transforms": list(result.transforms_applied or [])}))
sys.exit(0 if saved > 0 else 2)
"""
    try:
        proc = subprocess.run(
            [py, "-c", smoke],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if proc.returncode == 0:
            data = json.loads((proc.stdout or "").strip().splitlines()[-1])
            ok(
                f"headroom compress smoke saves tokens "
                f"({data['before']}->{data['after']}, saved={data['saved']})"
            )
        else:
            fail(
                "headroom compress smoke saved 0 tokens or failed: "
                f"rc={proc.returncode} err={(proc.stderr or proc.stdout or '')[-400:]}"
            )
            errors += 1
    except Exception as exc:  # noqa: BLE001
        fail(f"headroom compress smoke failed: {exc}")
        errors += 1

    # Policy must mention the judgment Advisor and must NOT auto-enable
    if CORE_RULE.is_file():
        ct = CORE_RULE.read_text(encoding="utf-8")
        if "ADVISOR" in ct and "judgment" in ct.lower():
            ok("core rule has judgment Advisor")
        else:
            fail("core rule missing judgment Advisor")
            errors += 1
        if "advisor-light-model-pool" in ct or "equal-weight pool" in ct:
            fail("core rule still references model-pool")
            errors += 1
        else:
            ok("core rule has no model-pool references")
        if "inherit" in ct and "available_subagent_models" in ct:
            ok("core rule uses Task inherit / available_subagent_models")
        else:
            fail("core rule missing inherit / available_subagent_models policy")
            errors += 1
        if "SUBAGENTS" in ct:
            ok("core rule has SUBAGENTS section")
        else:
            fail("core rule missing SUBAGENTS section")
            errors += 1
        auto_phrases = (
            "soft always-on",
            "without waiting for the user",
            "enable advisor without",
        )
        if any(b in ct.lower() for b in auto_phrases):
            fail("core rule still has auto-enable language")
            errors += 1
        else:
            ok("core rule has no auto-enable language")

    # The trimmed hook message points at the always-on rules instead of restating them.
    route2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "route_prompt.py")],
        input=json.dumps({"prompt": "explain project memory briefly"}),
        capture_output=True,
        text=True,
        check=False,
    )
    if route2.returncode == 0 and ("always-on rules" in route2.stdout or "HEADROOM FORCE" in route2.stdout):
        ok("route_prompt points at always-on policy")
    else:
        fail("route_prompt missing policy pointer")
        errors += 1

    if route2.returncode == 0 and "HEADROOM FORCE" in route2.stdout:
        ok("route_prompt includes HEADROOM FORCE")
    else:
        fail("route_prompt missing HEADROOM FORCE")
        errors += 1

    # No advisor skill in catalog
    skills = json.loads((CATALOGS / "skills-index.json").read_text())["items"]
    if any("advisor" == (s.get("name") or "").lower() for s in skills):
        fail("advisor incorrectly present in skills catalog")
        errors += 1
    else:
        ok("no advisor skill in catalog")

    # Token optimizer stack: rules + MCP servers present
    optimizer_rules = [
        "rtk.mdc",
        "mcptoon.mdc",
        "context-mode.mdc",
        "sqz-squeez.mdc",
        "jcodemunch.mdc",
        "claude-context.mdc",
        "cce.mdc",
        "voice.mdc",
        "token-optimizer.mdc",
        "lumen.mdc",
    ]
    for r in optimizer_rules:
        rp = CURSOR_HOME / "rules" / r
        if rp.is_file() and "alwaysApply: true" in rp.read_text(encoding="utf-8"):
            ok(f"optimizer rule present: {r}")
        else:
            fail(f"missing or non-forced optimizer rule: {r}")
            errors += 1
    live_mcp2 = CURSOR_HOME / "mcp.json"
    if live_mcp2.is_file():
        srv = json.loads(live_mcp2.read_text(encoding="utf-8")).get("mcpServers", {})
        # Gateway architecture: only headroom + mcptoon are connected directly;
        # the six optimizer servers run behind the mcptoon gateway.
        for name in ("headroom", "mcptoon"):
            if name in srv:
                ok(f"live mcp.json has direct server: {name}")
            else:
                fail(f"live mcp.json missing direct server: {name}")
                errors += 1
        gateway_only = ("jcodemunch", "sqz", "squeez", "context-mode", "claude-context", "context-engine", "claude-mem")
        leaks = [n for n in gateway_only if n in srv]
        if leaks:
            fail(f"live mcp.json has gateway servers as direct entries (schema cost): {leaks}")
            errors += 1
        else:
            ok("live mcp.json routes optimizer servers through mcptoon only")
        # Gateway must list all six.
        gw = Path.home() / ".mcptoon/config.json"
        if gw.is_file():
            servers = json.loads(gw.read_text(encoding="utf-8")).get("servers", {})
            missing = [n for n in gateway_only if n not in servers]
            if missing:
                fail(f"mcptoon gateway missing servers: {missing}")
                errors += 1
            else:
                ok(f"mcptoon gateway lists {len(gateway_only)} optimizer servers")
        else:
            fail("mcptoon config missing (~/.mcptoon/config.json)")
            errors += 1
    for binary in ("rtk", "sqz", "squeez", "mcptoon", "context-mode", "jcodemunch-mcp", "cce"):
        if shutil.which(binary):
            ok(f"optimizer CLI on PATH: {binary}")
        else:
            fail(f"optimizer CLI missing: {binary}")
            errors += 1

    # Caveman skill present, injection disabled, skill still callable.
    if (CURSOR_HOME / "caveman/skills/caveman/SKILL.md").is_file():
        ok("caveman skill installed")
    else:
        fail("caveman skill missing")
        errors += 1
    try:
        cav_cfg = json.loads((HOME / ".config/caveman/config.json").read_text(encoding="utf-8"))
        cav_mode = str(cav_cfg.get("defaultMode", "")).lower()
        if cav_mode in ("manual", "off"):
            ok(f"caveman injection disabled (defaultMode={cav_mode})")
        else:
            fail(f"caveman injects a ruleset every session (defaultMode={cav_mode}); set manual to save tokens")
            errors += 1
    except Exception:
        fail("caveman config missing (~/.config/caveman/config.json)")
        errors += 1
    hooks_txt = HOOKS_JSON.read_text(encoding="utf-8") if HOOKS_JSON.is_file() else ""
    if "caveman-host-session-start" not in hooks_txt:
        ok("caveman sessionStart injection removed")
    else:
        fail("caveman sessionStart hook still wired (injects ~1.1k tok/session)")
        errors += 1

    # Portable MCP config generator installed.
    if (SCRIPTS / "setup-mcp.sh").is_file() or (CURSOR_HOME / "scripts/master-controller/setup-mcp.sh").is_file():
        ok("portable MCP setup script installed")
    else:
        fail("portable MCP setup script missing (scripts/setup-mcp.sh)")
        errors += 1

    print()
    if errors:
        print(f"Verification failed ({errors} issues).")
        return 1
    print("Verification passed (light edition + memory + judgment advisor + headroom force + token optimizers).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
