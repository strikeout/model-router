# Constraints, budgets, and fallbacks

The tier rubric answers *how capable* a model needs to be. This file covers the three things that sit **outside** that axis: data sensitivity (a hard constraint that can override the tier choice), context budget (an escalation signal about the *task*, not the model), and what to do when a provider is unavailable.

## 1. Data classification overrides tier choice

Capability routing picks the cheapest model that can do the job. Sensitivity routing picks the set of models that are *allowed* to see the data. Sensitivity wins. Resolve it first, then apply the tier rubric inside whatever set is left.

| Sensitivity | Allowed routing | Examples |
|---|---|---|
| **Public** | Any model, any hosting | Open-source code, public docs, synthetic fixtures |
| **Internal** | Cloud APIs, given acceptable ToS and retention terms | Internal tooling, non-regulated business logic |
| **Sensitive** | Private/enterprise endpoints, or self-hosted | PII, financial calculations, health data, customer records |
| **Restricted** | Self-hosted only | Data-residency-mandated, contractually siloed, classified |

Practical consequences:

- Classify by what actually enters the context window, not by the repo's overall label. A schema file from a PII-bearing service is usually Internal; a dump of its rows is Sensitive.
- Redaction changes the class. Routing a Sensitive task to a cheap cloud tier *after* stripping identifiers is legitimate; pretending the raw payload is Internal is not.
- If a task is Restricted and no self-hosted model can do it well, that is a decomposition problem, not a routing problem — split out the part that needs frontier judgment and pose it against redacted or synthetic data.

## 2. Local models as a floor, not a peer

Where self-hosting is required or cost at scale dominates, open-weight models cover part of the tier map — but not evenly.

| Role | Local option | When local is fine |
|---|---|---|
| Mechanical fan-out, transforms, extraction | Any competent small local model | Almost always — this is the Haiku band, and it is the easiest to verify |
| Implementation | Qwen 2.5-Coder, DeepSeek-Coder V2, or similar | Sensitive data, or high-volume work with tight per-token economics |
| Procedural workflow / integration | Any capable local model | No sensitive-data concern, steps are scripted |
| Review, architecture, orchestration | *Frontier API recommended* | Rarely — judgment-heavy roles are exactly where local models underperform, and a missed review finding is the expensive failure |

The asymmetry is the point: local models substitute well for *throughput*, poorly for *judgment*. Route the labor local, keep the decisions on frontier.

## 3. Context budget is a decomposition signal

Track tokens per role. The numbers below are working bands, not limits — their value is the **escalation signal**: blowing through the band usually means the task is wrong-sized, not that it needs a bigger model.

| Role | Typical band | If you exceed it |
|---|---|---|
| Planning / spec writing | 50–100k | Scope is too large — decompose before writing more |
| Test authoring | 50–150k | Too many scenarios in one pass — split by behaviour |
| Implementation | 100–250k | Task needs decomposition into separately verifiable units |
| Review | 50–100k | Too many files — batch the review |
| Integration / CI wrangling | 30–80k | Something is actually broken — investigate, don't grind |

Escalating the model to rescue an over-budget task is the wrong reflex. A task that overflows its band on Sonnet will usually overflow it on Opus too, just more expensively. Split first; escalate only if the split parts are still hard.

## 4. Cost shape: what you actually pay for

In subagent-heavy, long-context workflows, spend is dominated by **cache reads and output tokens**, not fresh input. Cache reads bill at roughly a tenth of the input rate, so a session that re-reads a large stable context many times can land far below its list-price estimate, while a chatty high-output session lands above it.

Two implications for routing:

- **Don't re-route a tier on a headline price alone.** A big-context Opus orchestrator that mostly reads cache is often cheaper in practice than list rates suggest. Measure the blended rate on your own traffic before concluding a tier is misrouted.
- **Optimise output volume and cache stability, not just tier.** Stable prompt prefixes and terse subagent returns move the bill more than shaving a tier off one worker.

Treat any specific blended figure as an observation from one sample, with a date attached — re-measure rather than inheriting someone else's number.

## 5. Provider fallback

When the primary provider is degraded or unavailable:

1. **Route non-frontier work local.** Mechanical and procedural tasks are the portable ones — move them first.
2. **Queue frontier-required work.** Do not silently downgrade architecture, review, or orchestration to a model that cannot carry them; a wrong plan produced during an outage outlives the outage.
3. **Lean on written specs.** Precise specs are the recovery mechanism — they let any capable model regenerate the work later, which is what makes queueing cheap.
