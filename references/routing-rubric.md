# Routing rubric

The full policy behind the quick table in SKILL.md. Read this when a routing call isn't obvious, or when you need to explain a decision.

## The two axes that actually matter

Route on **judgment load** and **blast radius**, not topic.

- **Judgment load** — how much ambiguity, inference, and multi-step reasoning the task demands. "Rename every `getUser` to `fetchUser`" is low. "Decide whether to cache at the edge or the origin" is high.
- **Blast radius** — how expensive a wrong answer is. A throwaway script is low. A schema migration on the production users table is high.

Low/low → Haiku. Mid → Sonnet. High on either axis → Opus. Ceiling of difficulty, or a safety-hardened domain → Fable.

## Escalation triggers (Sonnet → Opus)

Raise a task to Opus when **any** hold:

- The spec is ambiguous or you'd have to invent requirements to proceed.
- Correct action depends on state spread across many files, services, or time.
- A cheaper tier already attempted it and failed or produced something subtly wrong.
- The change is irreversible or the cost of being wrong is high (data loss, security, money, user-facing breakage).
- The task *is* the coordination — planning the work, sequencing subagents, deciding what to delegate.

## Fable triggers (the sparse tier)

Route to Fable on:

- **Code review or security review** — a standing policy override. Every review goes to Fable regardless of diff size, file count, or apparent difficulty. This is the one place the rubric routes by *task type* rather than by judgment load, and it is deliberate: review is where a miss is silent and expensive, so the tier is fixed rather than judged per case.
- **Frontier difficulty** — the task is at or beyond the ceiling of what Opus reliably handles (novel algorithm design, formal proofs, research-grade synthesis).
- **Safety-hardened domain** — biology, cybersecurity, or LLM R&D, where you want frontier capability *with* the domain safeguards. This is Fable's distinctive value, not just raw IQ.

Outside those three, if a task is merely "hard," that's Opus, not Fable. The temptation to default hard work to the smartest model is exactly the cost trap this rubric exists to prevent.

**What counts as a review.** Reviewing a diff, a PR, a branch, a file, or a design for defects, regressions, or vulnerabilities — and any security audit, threat model, or vulnerability assessment. *Writing* the code is not a review: implementing a fix that a review surfaced is ordinary work and routes normally (usually Sonnet). Only the review pass itself takes the override.

## Worked examples

| Task | Tier | Why |
|---|---|---|
| "grep the repo for every TODO and dump them to a file" | Haiku | mechanical, verifiable, single-pass |
| "reformat these 400 JSON records to our schema" | Haiku | deterministic transform, cheap to check |
| "add pagination to the `/orders` endpoint and write tests" | Sonnet | real judgment, but scoped to one component |
| "refactor the notification module to use the new event bus" | Sonnet | non-trivial but bounded; escalate only if it fans out |
| "figure out why p99 latency tripled after the last deploy" | Opus | root-cause reasoning across systems, ambiguous |
| "design the multi-region failover strategy" | Opus | architecture, high blast radius, irreversible-ish |
| "run the orchestrator that dispatches this whole job" | Opus | misrouting is the expensive failure; spend here |
| "design and prove correctness of a novel CRDT for our sync layer" | Fable | frontier difficulty |
| "assess this parser for exploitable memory-safety bugs" | Fable | cybersecurity domain — the hardened specialist |
| "review this 30-line PR that renames a config key" | Fable | review policy — tier is fixed for reviews, not judged by size |
| "security-review the new auth flow" | Fable | review policy *and* cybersecurity domain |
| "apply the three fixes the review found" | Sonnet | implementing review findings is ordinary work, not a review |

## Role presets (when the pipeline is fixed)

If you run the same roles repeatedly, pin the tier once per role instead of re-deciding per task. The split follows judgment load, not seniority:

| Role | Tier | Why |
|---|---|---|
| Orchestrator / dispatcher | Opus | Coordination, decomposition, and the highest-leverage call in the system |
| Spec / plan author | Opus | Design judgment; the spec's quality bounds everything downstream |
| Adversarial reviewer ("what breaks this?") | Opus | Evidence-grounded objection is judgment-heavy, not throughput-heavy |
| Code reviewer | Opus | Nuance and quality judgment; a missed finding is the expensive failure |
| Test author from a spec | Sonnet | Structured output from an existing spec |
| Implementer | Sonnet (Opus if the task is genuinely hard) | The default working tier |
| Integration / CI wrangling | Sonnet | Procedural workflow |
| Estimator / report author against a fixed methodology | Sonnet | Follows a defined derivation and emits a conforming record |
| Threshold watcher / metric counter | Haiku | Counts observable proxies against fixed thresholds and emits a template |

The last two are the interesting cases. A role can *sound* weighty ("cost estimator", "compliance warden") and still be Sonnet or Haiku work, because the judgment lives in the methodology it applies, not in the model running it. Route on what the role actually has to decide.

## Anti-patterns

- **Everything on Opus "to be safe."** The default cost blowup. Sonnet clears most work; you're paying a premium for capability the task never used.
- **Everything on Haiku "to save money."** Haiku misroutes on ambiguity, then the orchestrator retries on a bigger model — net more expensive and slower than starting on Sonnet.
- **Fable as the smart default.** Fable is for its niche. Outside it, Opus matches quality at lower cost and latency, and without the occasional safeguard redirect.
- **A cheap orchestrator.** The dispatcher makes the highest-leverage call in the system. Running it on Haiku to save tokens optimizes the wrong line item — one bad route costs more than the dispatcher ever saves.
- **Routing by job title.** A role's name says nothing about its judgment load. "Warden", "auditor", and "estimator" are Haiku/Sonnet work when they apply a fixed methodology; the discipline lives in the written method, not in model IQ.
- **Escalating a tier to rescue an over-budget task.** Context overrun means the task is wrong-sized. Split it; a bigger model just overflows more expensively.
- **Routing by topic.** "It mentions security → Fable" is still wrong: "reset a test password" is Haiku. The review policy is an exception for a task *type* (an actual review pass), not for a subject matter — a task that merely touches security is routed on judgment load and blast radius, then let domain override *only* for genuinely hardened-domain work.

## The one-line policy

Default Sonnet. Drop to Haiku when it's mechanical and checkable. Raise to Opus when it's ambiguous, wide, risky, or the coordination itself. Route every code or security review to Fable. Otherwise raise to Fable only for frontier work or the hardened domains. Route down, escalate on evidence.
