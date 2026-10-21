# API / custom-harness orchestration

For dispatchers you build yourself (Conductor, a FastAPI service, an n8n flow). The pattern is: classify → resolve model string → call → optionally verify and escalate.

## Minimal loop

```python
from route import route  # scripts/route.py

def dispatch(task, **signals):
    r = route(task, **signals)                 # tier decision + reasons
    resp = call_claude(model=r["model_api"],   # your Anthropic client
                       task=task,
                       effort=r["effort"])
    return resp, r
```

`route()` gives you `model_api` (the `/v1/messages` model string), `model_cc` (the Claude Code alias, if you're generating agent files), a suggested `effort`, and a `reasons` list — log the reasons so every routing decision is auditable.

## Escalation on failure

The classifier is a first guess. Close the loop with a cheap verify-and-escalate step so a Haiku miss becomes a Sonnet retry rather than a silent wrong answer:

```python
resp, r = dispatch(task, files_touched=n)
if not passes_check(resp):                     # your task-specific verifier
    resp, r = dispatch(task, files_touched=n,
                       prior_failures=1)        # bumps one tier
```

`prior_failures` escalates one tier per failure — the "route down, escalate on evidence" policy, made mechanical. Cap retries; don't loop into Fable on a task that's simply broken.

## The review override

`route()` routes every code review and security review to Fable regardless of scope — it is the one rule that ignores judgment load and blast radius. Two consequences for a harness:

- **Don't let a cost guard downgrade a review.** A budget check that caps tier by diff size will silently undo the policy; exempt reviews from it, or the policy exists only on paper.
- **Expect refusals on the security path.** Security review is the workload most likely to return `stop_reason: "refusal"` with a `cyber` category, or to be redirected to Opus 4.8. Handle both in the review path specifically; see below.

Acting on a review's findings is not a review — implementation routes normally, so dispatch it as its own task rather than continuing the review call.

## Handling the Fable → Opus redirect

Fable's safeguards route a minority of sessions (under ~5%, tuned conservatively) to Opus 4.8. Your harness should treat a response that comes back as Opus when you asked for Fable as **normal**, not a failure:

- Don't assert `response.model == requested_model`. Read the actual model off the response and log it if you need the paper trail.
- Don't retry-loop trying to "force" Fable. The redirect is deliberate; hammering it wastes calls and won't change the outcome.
- If a workflow strictly requires Fable-specific behavior and got Opus, fail gracefully and surface it to a human rather than silently proceeding as if nothing changed.

## Keeping model strings current

`route.py` hardcodes the lineup in its `MODELS` dict. When Anthropic ships new versions, edit that dict in one place — the aliases (`sonnet`/`opus`/`haiku`) track family defaults on the Claude Code side, but the API strings are explicit and need updating. Don't scatter model strings through your codebase; import them from the router.

## Cost note

The whole point is spend discipline: run the classifier (free, local) and the cheapest viable worker, and reserve Opus for coordination and hard problems. The dominant cost in a naive multi-agent system is defaulting workers to the top tier "to be safe" — the rubric in `routing-rubric.md` is what prevents that.
