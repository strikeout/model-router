# model-router

model-router is a Claude Code skill. It sends each task to the cheapest Claude model that can do the task well.

The skill does not run every task on one model. It reads two properties of a task:

- **Judgment load.** This is the quantity of ambiguity and reasoning that the task needs.
- **Blast radius.** This is the cost of a wrong answer.

The governing rule is "route down, escalate on evidence". The skill starts at a low tier. A failure or a complexity that you can see moves the task up by one tier.

## The tiers

| Tier | Claude Code `model` | API model ID | Use it for |
|---|---|---|---|
| Haiku | `haiku` | `claude-haiku-5-5` | Mechanical work with a clear specification and a cheap check: search, log scans, format conversion, simple extraction |
| Sonnet (default) | `sonnet` | `claude-sonnet-5-5` | Most work: features, refactors in one component, tests, drafts, standard analysis |
| Opus | `opus` | `claude-opus-5-5` | Hard reasoning: architecture, debugging across many files, plans with no clear specification, decisions that you cannot reverse. Opus also runs the orchestrator. |
| Fable | `claude-fable-5-1` | `claude-fable-5-1` | All code reviews and security reviews, the hardest tasks, and work in biology, cybersecurity and LLM research |

The `haiku`, `sonnet` and `opus` aliases follow the newest model in each family. Fable has no alias, so the skill pins Fable by its full ID.

## What the repository contains

| Path | Contents |
|---|---|
| `SKILL.md` | The routing policy. Claude Code reads this file when the skill starts. |
| `references/routing-rubric.md` | The full rubric, with worked examples and anti-patterns |
| `references/constraints-and-budgets.md` | Data sensitivity, context budgets, local models and the outage procedure |
| `references/claude-code-setup.md` | The setup of the worker subagents in Claude Code |
| `references/api-orchestration.md` | The integration with a custom API harness, and the Fable redirect |
| `assets/agents/` | Four worker subagents, one for each tier |
| `agents/` | A copy of `assets/agents/` |
| `scripts/route.py` | A deterministic tier classifier with no dependencies |

## Install the skill

1. Clone the repository into the skill directory of Claude Code:

   ```bash
   git clone https://github.com/strikeout/model-router ~/.claude/skills/model-router
   ```

2. Copy the worker subagents into your user scope:

   ```bash
   mkdir -p ~/.claude/agents
   cp ~/.claude/skills/model-router/assets/agents/*.md ~/.claude/agents/
   ```

3. Restart Claude Code. The new agent directory loads only when a session starts.

For a single project, copy the subagents into `.claude/agents/` in that project.

## Use the skill in Claude Code

Claude Code starts the skill when you ask which model to use, or when you give it a batch of tasks to delegate. You can also start it with `/model-router`.

The orchestrator reads the `description` of each worker subagent. Then it sends each task to the subagent that matches. Run the orchestrator on Opus, because its routing decision has the largest effect on the cost:

```bash
claude --model opus
```

## Use the classifier in a custom harness

`scripts/route.py` gives a tier, the Claude Code alias, the API model ID and a suggested `effort` value. It also lists the signals that caused the decision.

```bash
python3 scripts/route.py "refactor the auth middleware to support API keys" --files 3
# tier=sonnet  cc=sonnet  api=claude-sonnet-5-5  effort=medium
```

The script accepts these options:

| Option | Meaning |
|---|---|
| `--files N` | The number of files that the task changes |
| `--tokens N` | The estimated number of input tokens |
| `--domain bio\|cyber\|llm_rd` | A safety domain that sends the task to Fable |
| `--prior-failures N` | The number of cheaper attempts that failed. Each failure adds one tier. |
| `--irreversible` | The task has a wrong answer that is costly or permanent |
| `--json` | The script writes JSON output |

You can also import the function: `from route import route`. The script is a heuristic floor. An Opus orchestrator that reads the rubric makes better decisions on new types of task.

## Caveats

- **Fable access is not certain.** Your plan and your organization's `availableModels` list control the access. If Claude Code cannot use a model, it runs the subagent on the model of the main session. It does not show a warning.
- **Fable sends some requests to Opus 4.8.** The Fable safeguards decline a small number of requests. Opus 4.8 then answers them. Your harness must accept a response from Opus when it asks for Fable.
- **Reviews cost more on Fable.** Fable costs about 2.5 times as much as Opus for each token. Security reviews also cause the most `refusal` stop reasons. A review pipeline must handle the refusal and the redirect.
- **The skill does not go around safeguards.** The Fable safeguards apply to every request. The skill selects a model. It does not change the behavior of that model.
- **Effort is a separate control.** The `effort` value and the model choice are two different settings. Tune each one separately.

## Update the model IDs

When Anthropic releases new models, edit these locations:

1. Edit the `MODELS` table in `scripts/route.py`.
2. Edit the tier table in `SKILL.md`.
3. Edit the tier table in this README.
4. Edit the `model` field in `assets/agents/fable-worker.md` and `agents/fable-worker.md`.

## License

The MIT License covers this repository. Read `LICENSE` for the full text.
