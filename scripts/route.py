#!/usr/bin/env python3
"""
route.py — deterministic tier classifier for the model-router skill.

Policy: default to Sonnet, drop to Haiku for mechanical work, raise to Opus for
hard reasoning / high blast radius, raise to Fable only on an explicit frontier
or safety-domain trigger. Route down, escalate on evidence.

This is a transparent heuristic floor, not an oracle. An Opus orchestrator
reading references/routing-rubric.md will beat it on novel tasks. Its value is
determinism and an auditable reason trail for non-LLM harnesses.

CLI:
    python scripts/route.py "convert these logs to csv" --files 1
    python scripts/route.py "design the sharding strategy" --files 20 --irreversible
    python scripts/route.py "audit this parser for RCE" --domain cyber

Library:
    from route import route
    r = route("refactor auth middleware", files_touched=3)
    r["model_api"]   # -> the API model ID of the Sonnet tier
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# This table is the one source of the API model IDs. Edit it when the lineup changes.
# cc_alias is the Claude Code `model` value. api is the model ID for /v1/messages.
MODELS = {
    "haiku":  {"cc_alias": "haiku",           "api": "claude-haiku-5-5",          "effort": "low"},
    "sonnet": {"cc_alias": "sonnet",          "api": "claude-sonnet-5-5",         "effort": "medium"},
    "opus":   {"cc_alias": "opus",            "api": "claude-opus-5-5",           "effort": "high"},
    "fable":  {"cc_alias": "fable",           "api": "claude-fable-5-1",          "effort": "high"},
}
ORDER = ["haiku", "sonnet", "opus", "fable"]

# Mechanical / verifiable work -> Haiku is fine.
MECHANICAL = re.compile(
    r"\b(grep|find|search for|locate|list|count|rename|reformat|format|convert|"
    r"transcode|extract|scrape|parse out|deduplicate|dedupe|sort|filter|lint|"
    r"boilerplate|scaffold|stub|classify|tag|label|transform|batch|bulk)\b",
    re.I,
)

# Hard reasoning / design -> raise to Opus.
HARD = re.compile(
    r"\b(architect|architecture|design|redesign|strategy|plan the|planning|"
    r"trade-?off|root cause|debug across|cross-file|multi-file|refactor the (system|codebase)|"
    r"migrat(e|ion)|concurrency|distributed|race condition|orchestrat|ambiguous|"
    r"underspecified|figure out why|why (is|does|isn't))\b",
    re.I,
)

# Review pass -> Fable by standing policy, regardless of size or difficulty.
REVIEW = re.compile(
    r"\b(code[ -]?review|security[ -]?review|sec[ -]?review"
    # "review this 30-line PR", "review the auth changes", "reviewing my diff"
    r"|review(ing)? (this|the|my|our)\b[^.]{0,40}?\b"
    r"(pr|pull request|diff|branch|change|patch|code|commit|file|work)s?"
    r"|security audit|threat ?model|vulnerability assessment"
    r"|audit (this|the) (code|diff|pr|branch|repo|dependenc))\b",
    re.I,
)

# Acting on a review's output is ordinary work, not a review pass.
REVIEW_FOLLOWUP = re.compile(
    r"\b(apply|implement|fix|address|resolve|respond to|action) (the |these |those |all )?"
    r"(\w+ )?(review|findings|comments|feedback|nits)\b",
    re.I,
)

# Explicit frontier signal -> consider Fable (only when also hard).
FRONTIER = re.compile(
    r"\b(frontier|hardest|state of the art|novel (algorithm|proof)|research-grade|"
    r"prove that|formal proof|beyond opus|push the limit)\b",
    re.I,
)

# Safety-hardened domains -> Fable is the right specialist tier.
DOMAINS = {"bio", "cyber", "llm_rd"}
DOMAIN_HINTS = {
    "bio":    re.compile(r"\b(pathogen|virology|genom|protein design|biosecurity|wet lab)\b", re.I),
    "cyber":  re.compile(r"\b(exploit|vulnerabilit|rce|malware|red team|pen ?test|0day|zero-day)\b", re.I),
    "llm_rd": re.compile(r"\b(train(ing)? a (frontier|large) model|rlhf|model weights|pretrain|eval harness for models)\b", re.I),
}


def _bump(tier: str, steps: int = 1) -> str:
    i = min(len(ORDER) - 1, max(0, ORDER.index(tier) + steps))
    return ORDER[i]


def route(
    task: str,
    files_touched: int = 0,
    est_input_tokens: int = 0,
    domain: str | None = None,
    prior_failures: int = 0,
    irreversible: bool = False,
) -> dict:
    """Return {tier, model_cc, model_api, effort, reasons}.

    Signals, in order of influence:
      - code or security review pass                 -> Fable (policy override)
      - mechanical language + small scope           -> Haiku
      - hard-reasoning language / wide scope / risk  -> Opus
      - explicit frontier trigger (and already hard) -> Fable
      - named safety domain (bio/cyber/llm_rd)       -> Fable
      - each prior cheaper failure                   -> +1 tier
    """
    reasons: list[str] = []
    text = task or ""

    # 1) Default.
    tier = "sonnet"
    reasons.append("default: Sonnet")

    # 2) Mechanical + small -> Haiku.
    mechanical = bool(MECHANICAL.search(text))
    small = files_touched <= 1 and est_input_tokens <= 8000
    if mechanical and small and not HARD.search(text):
        tier = "haiku"
        reasons.append("mechanical language + small, verifiable scope -> Haiku")

    # 3) Hard reasoning / wide scope / irreversible -> Opus.
    if HARD.search(text):
        tier = _bump(tier if tier != "haiku" else "sonnet")  # never Haiku for hard work
        reasons.append("hard-reasoning language -> Opus")
    if files_touched >= 6:
        tier = max(tier, "opus", key=ORDER.index)
        reasons.append(f"wide blast radius ({files_touched} files) -> Opus")
    if irreversible:
        tier = max(tier, "opus", key=ORDER.index)
        reasons.append("irreversible / high-cost-if-wrong -> Opus")

    # 3.5) Review pass -> Fable, by standing policy. This is the one rule that
    # routes on task type rather than judgment load: every code or security
    # review takes the top tier, however small the diff. Implementing what a
    # review found is not a review and is excluded.
    is_review = bool(REVIEW.search(text)) and not REVIEW_FOLLOWUP.search(text)
    if is_review:
        tier = "fable"
        reasons.append("code/security review -> Fable (standing policy, size-independent)")

    # 4) Safety domain -> Fable specialist tier.
    d = (domain or "").strip().lower() or None
    if d and d not in DOMAINS:
        reasons.append(f"unknown domain '{d}' ignored (expected one of {sorted(DOMAINS)})")
        d = None
    if d is None:
        for name, rx in DOMAIN_HINTS.items():
            if rx.search(text):
                d = name
                reasons.append(f"domain inferred from text: {name}")
                break
    if d in DOMAINS:
        tier = "fable"
        reasons.append(f"safety-hardened domain ({d}) -> Fable")

    # 5) Explicit frontier trigger, but only when the task is already hard.
    if FRONTIER.search(text) and ORDER.index(tier) >= ORDER.index("opus"):
        tier = "fable"
        reasons.append("explicit frontier trigger on an already-hard task -> Fable")

    # 6) Escalate one tier per prior cheaper failure.
    if prior_failures > 0:
        tier = _bump(tier, prior_failures)
        reasons.append(f"escalated +{prior_failures} tier(s) after {prior_failures} prior failure(s)")

    m = MODELS[tier]
    return {
        "tier": tier,
        "model_cc": m["cc_alias"],
        "model_api": m["api"],
        "effort": m["effort"],
        "reasons": reasons,
    }


def _main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Route a task to a Claude model tier.")
    p.add_argument("task", help="task description")
    p.add_argument("--files", type=int, default=0, help="files the task will touch")
    p.add_argument("--tokens", type=int, default=0, help="estimated input tokens")
    p.add_argument("--domain", default=None, help="bio | cyber | llm_rd")
    p.add_argument("--prior-failures", type=int, default=0, help="cheaper attempts already failed")
    p.add_argument("--irreversible", action="store_true", help="wrong answer is costly/irreversible")
    p.add_argument("--json", action="store_true", help="emit JSON")
    a = p.parse_args(argv)

    r = route(a.task, a.files, a.tokens, a.domain, a.prior_failures, a.irreversible)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"tier={r['tier']}  cc={r['model_cc']}  api={r['model_api']}  effort={r['effort']}")
        for reason in r["reasons"]:
            print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
