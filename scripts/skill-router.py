#!/usr/bin/env python3
"""Score a user prompt against LIGHT catalog indexes (stopwords + domain boosts)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CATALOGS_DIR = Path(
    os.environ.get(
        "MC_CATALOGS_DIR",
        str(Path.home() / ".cursor/plugins/local/always-use-all-skills/catalogs"),
    )
)
TOP_N = 6
MIN_SCORE = 4.0
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{1,}")

STOPWORDS = frozenset(
    """
    a an the and or but if to of in on at by for with from as is are was were be been being
    this that these those it its they them their you your we our my me i he she his her
    not no yes do does did done have has had can could should would will just than then
    also only into over under about after before between through during without within
    help fix make get set put use used using run running please thanks thank hey hi ok
    something anything everything nothing thing things way ways need needs wanted want
    """.split()
)

GENERIC_PROMPT_RE = re.compile(
    r"\b(help|fix|build|create|implement|review|audit|improve|optimize|setup|configure|debug|write|draft|plan|design)\b",
    re.IGNORECASE,
)

DOMAIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "design": re.compile(
        r"\b(landing|portfolio|awwwards|linear|stripe|ui|ux|hero|typography|palette|"
        r"redesign|website|webpage|frontend.?design|visual|aesthetic|mockup|comp|"
        r"image.?to.?code|beautiful\s+site|reference\s+site)\b",
        re.I,
    ),
    "browser": re.compile(
        r"\b(browser|devtools|dev\s*tools|console\s+error|dom\s+inspect|network\s+request|"
        r"chrome\s+devtools|check\s+in\s+(the\s+)?browser)\b",
        re.I,
    ),
    "seo": re.compile(
        r"\b(seo|sitemap|robots\.txt|schema|json-?ld|core\s+web\s+vitals|lighthouse|"
        r"search\s+ranking|meta\s+tags?|e-?e-?a-?t|ai\s+overview)\b",
        re.I,
    ),
    "coding": re.compile(
        r"\b(typescript|javascript|refactor|exhaustive\s+switch|inline\s+import|"
        r"ponytail|yagni|simplest|shortest\s+diff|implement|bugfix|compile)\b",
        re.I,
    ),
    "review": re.compile(
        r"\b(thermos|thermo-?nuclear|security\s+audit|maintainability|"
        r"branch\s+review|deep\s+review|code\s+quality\s+review|"
        r"pull\s+request\s+review|pr\s+review|review\s+this\s+(pr|branch|diff))\b",
        re.I,
    ),
}

# Prose signal: user-facing writing tasks. Voice skills load only when this hits,
# so their large bodies stay out of context on pure-code turns.
PROSE_RE = re.compile(
    r"\b(write|rewrite|draft|edit|prose|copy|article|blog|post|email|essay|"
    r"humanize|de-?slop|unslop|tone|voice|wording|paragraph|sentence|"
    r"readme|docs?|documentation|summary|summarize|announcement|newsletter|"
    r"caption|bio|description|letter|message|reply|response)\b",
    re.I,
)

VOICE_NAMES = ("humanizer", "structural-humanizer", "human-voice-rewrite", "unslop")


def is_prose_prompt(prompt: str) -> bool:
    return bool(PROSE_RE.search(prompt))


def tokenize(text: str) -> set[str]:
    tokens = {t for t in TOKEN_RE.findall(text.lower()) if len(t) > 2}
    return tokens - STOPWORDS


def prompt_has_phrase(prompt_l: str, phrase: str) -> bool:
    phrase = phrase.lower().strip()
    if not phrase:
        return False
    if phrase in prompt_l:
        return True
    phrase_tokens = phrase.split()
    if len(phrase_tokens) > 1:
        return phrase in prompt_l
    if phrase in STOPWORDS:
        return False
    return bool(re.search(rf"\b{re.escape(phrase)}\b", prompt_l))


def detect_domains(prompt: str) -> set[str]:
    return {name for name, pat in DOMAIN_PATTERNS.items() if pat.search(prompt)}


def score_item(
    prompt_l: str,
    prompt_tokens: set[str],
    item: dict[str, Any],
    domains: set[str],
) -> tuple[float, str]:
    name = str(item.get("name", ""))
    description = str(item.get("description", ""))
    triggers = item.get("triggers") or []
    mode = str(item.get("mode", ""))
    catalog_id = str(item.get("catalog_id", ""))
    domain = str(item.get("domain") or "")

    score = 0.0
    reasons: list[str] = []

    if mode == "always apply":
        for trigger in triggers:
            if prompt_has_phrase(prompt_l, str(trigger)):
                score += 10.0
                reasons.append(f"always-on-trigger:{trigger}")
        name_l = name.replace("-", " ")
        if name_l and prompt_has_phrase(prompt_l, name_l):
            score += 8.0
            reasons.append(f"always-on-name:{name}")
        if score > 0:
            return score, "; ".join(reasons)
        return 0.0, "always-on (no prompt overlap)"

    name_tokens = tokenize(name.replace("-", " "))
    name_overlap = prompt_tokens & name_tokens
    if name_overlap:
        score += 5.0 * len(name_overlap)
        reasons.append(f"name:{','.join(sorted(name_overlap))}")

    for trigger in triggers:
        trigger_l = str(trigger).lower().strip()
        if not trigger_l:
            continue
        if prompt_has_phrase(prompt_l, trigger_l):
            score += 12.0
            reasons.append(f"trigger-phrase:{trigger_l}")
            continue
        trigger_tokens = tokenize(trigger_l.replace("-", " "))
        overlap = prompt_tokens & trigger_tokens
        if overlap:
            score += 3.0 * len(overlap)
            reasons.append(f"trigger-tokens:{trigger_l}")

    # Description overlap: only meaningful tokens, capped
    desc_tokens = tokenize(description)
    desc_overlap = prompt_tokens & desc_tokens
    if desc_overlap:
        score += min(6.0, 1.5 * len(desc_overlap))
        reasons.append(f"description:{','.join(sorted(list(desc_overlap)[:5]))}")

    if name and prompt_has_phrase(prompt_l, name.replace("-", " ")):
        score += 7.0
        reasons.append(f"name-match:{name}")

    if catalog_id:
        tail = catalog_id.split("/")[-1].replace("-", " ")
        if tail and len(tail) > 3 and prompt_has_phrase(prompt_l, tail):
            score += 4.0
            reasons.append(f"catalog-id:{tail}")

    if domain and domain in domains:
        score += 15.0
        reasons.append(f"domain-boost:{domain}")

    # Soft penalties for cross-domain noise
    if domains and domain and domain not in domains:
        if domain == "review" and "review" not in domains:
            score *= 0.15
            reasons.append("review-dampen")
        elif score < 12:
            score *= 0.35
            reasons.append("cross-domain-dampen")

    reason = "; ".join(reasons) if reasons else "no overlap"
    return score, reason


def rank_items(
    prompt: str,
    items: list[dict[str, Any]],
    *,
    dedupe_name: bool,
    min_score: float = MIN_SCORE,
) -> list[dict[str, Any]]:
    prompt_l = prompt.lower()
    prompt_tokens = tokenize(prompt)
    domains = detect_domains(prompt)
    prose = is_prose_prompt(prompt)
    scored: list[tuple[float, dict[str, Any], str]] = []

    for item in items:
        score, reason = score_item(prompt_l, prompt_tokens, item, domains)
        # Voice skills surface only on prose turns.
        name = str(item.get("name", ""))
        if any(v in name for v in VOICE_NAMES):
            if not prose:
                continue
            score += 14.0
            reason = (reason + "; " if reason else "") + "prose-voice"
        if score < min_score:
            continue
        scored.append((score, item, reason))

    scored.sort(key=lambda row: (-row[0], row[1].get("name", ""), row[1].get("path", "")))

    results: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for score, item, reason in scored:
        name = str(item.get("name", ""))
        if dedupe_name and name in seen_names:
            continue
        if dedupe_name:
            seen_names.add(name)
        results.append(
            {
                "path": item.get("path"),
                "name": name,
                "score": round(score, 2),
                "reason": reason,
                "mode": item.get("mode", ""),
                "domain": item.get("domain", ""),
            }
        )
        if len(results) >= TOP_N:
            break

    return results


def needs_light_judgment(prompt: str, skills: list[dict[str, Any]]) -> bool:
    # Light edition: always judge the small catalog; flag when router is weak
    if not skills:
        return True
    top_score = max((s.get("score", 0) for s in skills), default=0)
    if top_score < 10.0:
        return True
    if GENERIC_PROMPT_RE.search(prompt) and top_score < 18.0:
        return True
    return False


def route(prompt: str, catalogs_dir: Path = CATALOGS_DIR) -> dict[str, Any]:
    skills = load_index(catalogs_dir / "skills-index.json")
    plugins = load_index(catalogs_dir / "plugins-index.json")
    rules = load_index(catalogs_dir / "rules-index.json")

    relevant_skills = rank_items(prompt, skills, dedupe_name=True)
    relevant_plugins = rank_items(prompt, plugins, dedupe_name=True)
    relevant_rules = rank_items(prompt, rules, dedupe_name=False)

    return {
        "prompt_preview": prompt[:200],
        "edition": "light",
        "domains": sorted(detect_domains(prompt)),
        "catalog_evaluation_required": needs_light_judgment(prompt, relevant_skills),
        "relevant_skills": relevant_skills,
        "relevant_plugins": relevant_plugins,
        "relevant_rules": relevant_rules,
    }


def load_index(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("items", []))


def main() -> None:
    parser = argparse.ArgumentParser(description="Route prompts to light catalog items")
    parser.add_argument("prompt", nargs="?", help="User prompt text")
    parser.add_argument("--catalogs-dir", type=Path, default=CATALOGS_DIR)
    args = parser.parse_args()

    prompt = args.prompt
    if not prompt and not sys.stdin.isatty():
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw)
            prompt = (
                payload.get("prompt")
                or payload.get("user_message")
                or payload.get("message")
                or payload.get("text")
                or ""
            )
            if not prompt and isinstance(payload.get("messages"), list):
                for msg in reversed(payload["messages"]):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        prompt = str(msg.get("content", ""))
                        break
        except json.JSONDecodeError:
            prompt = raw

    if not prompt:
        parser.error("prompt required (arg or stdin)")

    result = route(prompt.strip(), args.catalogs_dir)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
