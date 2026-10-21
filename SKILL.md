---
name: model-router
description: Route each task to the cheapest Claude model that can do it well — Haiku, Sonnet, Opus, or Fable — instead of running everything on one model. Use this whenever the user is setting up or running a multi-model / multi-agent workflow, wants to cut token cost or latency by delegating work across model tiers, asks which model to use for a task, is defining Claude Code subagents with per-agent `model` fields, or is building an orchestrator/dispatcher (Claude Code, Conductor, or a custom API harness) that fans work out to subagents. Trigger even when the user just says "route this", "pick the right model", "which tier", "delegate to a cheaper model", or hands over a batch of mixed-difficulty tasks — this skill supplies the tier-selection rubric, ready-to-drop subagent definitions, and a portable classifier.
---

# Model Router

Pick the **cheapest model that can do the job well**, then escalate only on evidence. Running every task on your smartest model is the most common and most expensive mistake in agentic workflows; running everything on your cheapest model quietly burns money on retries. This skill encodes a policy that avoids both.

The unit of decision is not the task's *topic* — it's its **judgment load** (how much ambiguity and reasoning it demands) and its **blast radius** (how costly a wrong answer is). A "delete these temp files" task and a "design the migration strategy" task can both mention databases; only one needs Opus.

## The tiers

| Tier | Claude Code `model` | API model string | Route here for | Don't route here for |
|---|---|---|---|---|
| **Haiku** | `haiku` | `claude-haiku-5-5` | Mechanical, well-specified, verifiable work: file search / grep, log & output scanning, format/text conversion, simple extraction or classification, boilerplate, deterministic transforms, cheap high-volume fan-out | Anything ambiguous or needing cross-context judgment — it will look confident and be wrong |
| **Sonnet** *(default)* | `sonnet` | `claude-sonnet-5-5` | Most real work: feature implementation, in-component refactors, writing tests, drafting, moderate multi-step reasoning, standard analysis | Trivial fan-out (waste) or genuinely hard architecture |
| **Opus** | `opus` | `claude-opus-5-5` | Hard reasoning: system architecture, debugging that spans many files/subsystems, ambiguous or underspecified planning, high-blast-radius or irreversible decisions — and running the orchestrator itself | Routine coding — it's overkill and you pay for it |
| **Fable** | *(no alias — use full ID)* `claude-fable-5-1` | `claude-fable-5-1` | **Every code review and every security review, regardless of size** (standing policy); the top of the difficulty distribution; work in biology / cybersecurity / LLM-R&D where you want frontier capability with safety measures in place | General hard tasks that aren't reviews — marginal gain over Opus at higher cost and latency |

`sonnet`/`opus`/`haiku` are family aliases that resolve to the current default in each family. Fable is Mythos-tier and has no short alias, so pin it by full ID. Pin full IDs anywhere you need version determinism.

## The decision procedure

Apply this in order. Stop at the first tier that plausibly succeeds on the first try.

0. **First, check what the data allows.** Sensitivity is a hard constraint, not a preference: resolve the permitted set of models, then run the rest of this procedure *inside* that set. Everything below assumes the whole set is available.
1. **Default to Sonnet.** It is the right answer more often than anything else. Deviate only for a reason you can name.
2. **Drop to Haiku** when the task is mechanical, fully specified, and cheap to verify. If you can't state the pass/fail check in one sentence, it's not a Haiku task.
3. **Raise to Opus** when *any* of these is true: the task is ambiguous or underspecified, it requires reasoning across many files or systems, a cheaper tier has already failed, or a wrong answer is expensive or irreversible.
4. **Raise to Fable** on a review trigger, an explicit frontier trigger (this is at the ceiling of what Opus can do), or a safety-domain trigger (bio / cyber / LLM-R&D where you want the hardened model). The **review trigger is a standing policy override**: any code review or security review goes to Fable, whatever its size or apparent difficulty — a one-file diff review routes to Fable even though steps 1–3 would have said Sonnet. Outside reviews, do not treat "smartest available" as "the default for hard things" — Opus is the default hard tier, and Fable stays a deliberate, sparse choice.
5. **Run the orchestrator on a capable model (Opus).** The dispatcher's judgment is the highest-leverage decision in the system: a cheap router that misroutes to a cheap worker that fails and retries costs more than routing correctly once. Spend on the decision, save on the labor.

The governing bias is **route down, escalate on evidence** — start low, and let observed failure or observed complexity pull you up one tier at a time, rather than starting high "to be safe."

## Constraints that outrank the tier choice

Capability is one axis. Three others can override it, and all three are cheaper to handle up front than to discover mid-run:

- **Data sensitivity.** Public → any model; Internal → cloud APIs with acceptable terms; Sensitive → private endpoints or self-hosted; Restricted → self-hosted only. Classify by what actually enters the context window, not by the repo's overall label. If a Restricted task exceeds what a self-hosted model can do, decompose it and pose the hard part against redacted or synthetic data — don't reclassify the data to fit the model.
- **Context budget.** Track tokens per role and treat the overrun as a signal about the *task*, not the model: planning >100k, test authoring >150k, implementation >250k, review >100k all mean "decompose", not "escalate". A task that overflows on Sonnet overflows on Opus too, just more expensively.
- **Provider availability.** On an outage, move mechanical and procedural work to local models and *queue* the frontier-required work. Never silently downgrade architecture, review, or orchestration — a bad plan made during an outage outlives the outage.

Local open-weight models substitute well for throughput and poorly for judgment: fine for transforms, extraction, and scripted workflow; keep review, architecture, and the orchestrator on frontier models. And when comparing costs, note that long-context subagent workflows are dominated by cache reads (~0.1x input) and output tokens — measure your own blended rate before concluding a tier is misrouted on list price alone.

Full tables, local-model options, and the fallback procedure: `references/constraints-and-budgets.md`.

## Two ways to implement this

**Claude Code (subagents).** Routing here is *description-driven*: the orchestrator model reads each subagent's `description` and delegates to the match. So "a router" is really four model-pinned subagents with sharp descriptions plus this policy in the orchestrator's context. Drop the four files in `assets/agents/` into `.claude/agents/` (project) or `~/.claude/agents/` (user), then tell the orchestrator to follow the decision procedure above. Details, env vars, and the availability caveats: `references/claude-code-setup.md`.

**API / custom harness (Conductor, FastAPI, etc.).** Classify the task, resolve a model string, then call. Use the bundled classifier as the deterministic floor:

```bash
python scripts/route.py "refactor the auth middleware to support API keys" --files 3
# -> tier=sonnet  model=claude-sonnet-5-5  effort=medium  reasons=[...]
```

`route.py` is a transparent, dependency-free heuristic — import `route()` or run it as CLI. It returns the tier, both the Claude Code alias and the API string, a suggested `effort`, and the signals that fired, so every routing decision is explainable. Treat it as a floor: an Opus orchestrator reading the rubric will out-route the heuristic on genuinely novel tasks, but the script gives you determinism and a paper trail. Wiring and the Fable-redirect handling: `references/api-orchestration.md`.

Full rubric with worked examples and anti-patterns: `references/routing-rubric.md`.

## Caveats that will bite you if ignored

- **Fable access is not guaranteed.** It depends on your org's `availableModels` allowlist and plan. Claude Code silently skips a `model` value that resolves to an excluded model and falls back to the inherited model — so if your Fable subagent quietly runs as something else, check the allowlist, not your config.
- **Fable redirects a minority of queries to Opus 4.8 by design.** Its safeguards are tuned conservatively and trigger in under 5% of sessions, sometimes on harmless requests. Don't build a pipeline that breaks when a Fable call comes back as Opus — treat that as expected behavior, not an error.
- **The review policy is a deliberate cost/refusal tradeoff.** Fable bills roughly 2.5x Opus per token, and routing *all* reviews there — not just the hard ones — means routine diff reviews pay frontier rates. Security review is also the workload most likely to hit the `refusal` stop reason (`category: "cyber"`) or the Opus 4.8 redirect, so a review pipeline must handle both rather than treating them as errors.
- **Routing to Fable does not bypass Fable's safeguards.** They operate on the model regardless of how it's invoked. This skill routes *to* models; it does not, and cannot, route *around* their safety measures — nor should it be modified to try.
- **The `effort` field is separate from model choice.** A hard task on Opus with low effort can underperform a medium task on Sonnet with high effort. The classifier suggests an `effort`; tune it independently.
