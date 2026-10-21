# Claude Code setup

In Claude Code you don't write a dispatcher — the orchestrator model *is* the dispatcher. It reads each subagent's `description` and delegates to the best match. So installing this "router" means: install four model-pinned worker subagents with sharp descriptions, run the orchestrator on a capable model, and give it the routing policy.

## 1. Install the worker subagents

Copy the four files from `assets/agents/` into one of:

- `.claude/agents/` — project scope (highest priority, checked into the repo)
- `~/.claude/agents/` — user scope (applies across your projects)

```bash
mkdir -p .claude/agents
cp assets/agents/*.md .claude/agents/
```

Each file's `model` field pins its tier: `haiku`, `sonnet`, `opus`, and `claude-fable-5-1` (full ID — Fable has no short alias). The aliases resolve to the current default in each family, so they track upgrades automatically; pin full IDs if you need a fixed version.

**Restart gotcha:** file-based subagents load at session start. After adding the *first* agent file to a new `agents/` directory, restart Claude Code so the watcher picks up the directory. Edits to existing files are detected within a few seconds without a restart; agents created via the `/agents` interface take effect immediately.

## 2. Run the orchestrator on Opus

The dispatcher's judgment is the highest-leverage decision, so don't cheap out on it:

```bash
claude --model opus
```

## 3. Give the orchestrator the policy

Put the decision procedure where the orchestrator will see it — a `CLAUDE.md` at the repo root is the natural home. Minimum viable version:

```markdown
## Delegation policy
Default to sonnet-worker. Use haiku-worker only for mechanical, fully-specified,
verifiable tasks. Escalate to opus-worker when a task is ambiguous, spans many
files/systems, is irreversible/high-risk, or a cheaper tier already failed.
Use fable-worker only for frontier-difficulty work or the bio/cyber/LLM-R&D
domains. Route down, escalate on evidence.
```

The orchestrator now matches each incoming task against the four descriptions and this policy, and delegates. That's the whole router.

## 4. Optional: default model for `inherit` agents

Any subagent without a `model` field inherits the main conversation's model. To set a cheaper floor for those:

```bash
export CLAUDE_CODE_SUBAGENT_MODEL="claude-sonnet-5-5"
```

## Caveats

- **`availableModels` allowlist wins.** Claude Code checks env var, per-invocation param, and frontmatter against your org's allowlist, and **silently skips** a value that resolves to an excluded model, running the subagent on the inherited model instead. If `fable-worker` quietly runs as something else, the allowlist is the first place to look — not your config.
- **Fable may be gated.** Fable/Mythos-tier access depends on plan and org policy. If it's not enabled, the Fable subagent falls back per the rule above.
- **Extended thinking inherits.** Recent Claude Code versions have subagents inherit the main session's thinking configuration. If you want a worker to reason harder or less, set its `effort` field explicitly rather than relying on inheritance.
