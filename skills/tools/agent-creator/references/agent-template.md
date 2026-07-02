# Agent File Templates (annotated)

Two templates — one per flavor. Copy the matching one, then replace the
`{{...}}` placeholders. The `# >>` lines are guidance: **delete them** in the
finished file. Both are modeled on real agents in this repo
(`agents/feature-planner.md`, `agents/adversarial-reviewer.md`,
`skills/architecture/blueprint/agents/pattern-analyst.md`).

---

## A. Registered subagent (full frontmatter)

Saved as `agents/{{name}}.md` (repo) or `~/.claude/agents/{{name}}.md`.

```markdown
---
name: {{kebab-case-name}}          # >> MUST equal the filename without .md.
                                   # >> The name steers when the agent is spawned —
                                   # >> callers pattern-match tasks against it before
                                   # >> reading the description. Mis-firing agent?
                                   # >> Rename before rewriting.
description: >
  # >> Lead with the artifact/verb the agent produces. Then WHEN to delegate
  # >> (phrasings a caller would actually use). Then explicit NOT-for clauses
  # >> naming sibling agents it might be confused with. Anti-conditions carry
  # >> equal weight to triggers. The description also shapes the spawn prompt —
  # >> the parent briefs the agent from it — so name the inputs it expects.
  {{One-line what-it-does, leading with the verb}}. Use when {{caller phrasings
  / contexts}}. Provide it {{the inputs every spawn must include}}. NOT for:
  {{adjacent-but-wrong task}} (use {{sibling}}); {{another near-miss}}.
tools: {{Read, Grep, Glob, ...}}   # >> Least privilege. List explicitly — omitting
                                   # >> this inherits ALL tools (silent over-grant).
                                   # >> Read-only agents omit Edit/Write by design.
model: {{haiku | sonnet | opus}}   # >> Match the hardest thing it must do.
color: {{blue | green | ...}}      # >> Optional, cosmetic — tints this agent's output
                                   # >> in the UI so parallel agents are tellable apart.
---

# {{Agent Name}}

# >> ROLE: one paragraph. Who this agent is and its single responsibility.
# >> Write in second person ("You ..."). Remember it shares NO context with the
# >> parent — state assumptions here, don't assume they're known.
You {{single-sentence responsibility}}. {{One or two sentences of framing —
what good looks like, the spirit of the job.}}

## Inputs (provided at spawn)
# >> The injected-context contract. List exactly what every spawn prompt MUST
# >> supply. This turns an implicit assumption into a checkable interface and is
# >> the #1 thing that prevents "body assumed context it never got" failures.
- {{e.g. target path / file / PR number}}
- {{e.g. task-specific parameters}}
- {{facts the parent already discovered and is sharing}}

## Operating contract
# >> Hard boundaries and constraints. What it must never do; read-only vs
# >> write-where; citation/evidence rules; the no-mid-run-questions rule.
- {{Read-only? Write only to X? Never touch Y?}}
- You run in a fresh, isolated context and cannot ask the user questions
  mid-run. When something is ambiguous, make the reasonable call and record it
  under Open questions rather than blocking.
- You cannot spawn subagents (one-level nesting). Do all work yourself.

## Method
# >> HOW it approaches this class of problem. Procedures/phases over a rigid
# >> script — describe end states where the agent reasons better from a goal.
# >> Explain WHY a step matters instead of stacking bare MUSTs.
1. {{phase}}
2. {{phase}}

## Output
# >> The return value is DATA FOR THE CALLER, not a user message. Give an exact
# >> template (or a JSON schema if a Workflow consumes it) — agents struggle to
# >> wrap up once the work is done, and this template is what lands the ending.
# >> Tell it to summarise, not dump its working notes. For research/review
# >> agents, the default section set is: Summary, Critical issues, Major
# >> issues, Recommendations, Obstacles encountered. Keep "Obstacles
# >> encountered" whatever the shape — the parent must not have to re-discover
# >> what this agent already ran into.
Return exactly this structure:

```markdown
## Summary
{{the two-sentence answer}}

## {{Critical issues / main findings}}
{{must-know findings, each with evidence (path:line)}}

## Recommendations
{{what the caller should do next}}

## Obstacles encountered
{{what you could NOT do — missing files, denied tools, dead ends, assumptions
you had to make. Write "none" rather than omitting the section.}}

## Open questions
{{ambiguities you flagged instead of guessing}}
```

## Quality bar
# >> What "good" looks like; a self-critique pass before returning.
{{The standard the result must meet. e.g. "Every claim cites path:line; the
summary is tight enough that the caller needn't re-read the source."}}
```

---

## B. Skill-bundled, body-only agent (NO frontmatter)

Saved as `{{parent-skill}}/agents/{{name}}.md`. The parent skill reads this file
and spawns it via `subagent_type: general-purpose`, injecting context in the
spawn prompt. **There is no frontmatter**: no `name`, no `description`, no
`tools`, no `model`. Triggering and tool grants live in the parent skill.

```markdown
# {{Agent Name}}

# >> ROLE paragraph, same as above — isolated context, state assumptions.
You {{single-sentence responsibility}}.

## What to examine / Inputs
# >> What the parent injects at spawn (target dir, shared facts) and what the
# >> agent should look at. Keep it generic — no hardcoded paths; the parent
# >> supplies specifics.
{{...}}

## Strategy / Method
# >> The procedure. Same "explain the why" discipline.
{{...}}

## Output Format
# >> Exact shape the parent expects back, so it can aggregate across siblings.
# >> Summarise — the parent pays context for everything returned. Include an
# >> "Obstacles encountered" section here too, so the parent aggregating N
# >> siblings can see which ones hit walls.
```markdown
## {{Section}}
{{...}}

## Obstacles encountered
{{what you could not do; "none" if clean}}
```
```

### Wiring the parent skill (body-only only)

In the parent `SKILL.md`, read the agent file and spawn it, injecting per-run
context. Pattern (from `skills/architecture/blueprint/SKILL.md`):

```
Spawn Agent:
  subagent_type: "general-purpose"
  prompt: |
    {contents of agents/{{name}}.md}

    ## Your task
    {injected per-run context: target dir, shared facts, where to write outputs}
```

Restrict the agent's reach by what the parent grants and instructs — the
body-only file cannot carry a `tools:` allowlist itself.

---

## Checklist before you ship the file

- [ ] `name` (registered) equals the filename; body-only has **no** frontmatter.
- [ ] Single responsibility — the role sentence has no "and".
- [ ] Inputs-at-spawn section lists everything the body assumes.
- [ ] Output section gives an exact shape and says "summarise, don't dump".
- [ ] Output shape includes an "Obstacles encountered" section — the caller
      must not have to re-discover what the agent already ran into.
- [ ] `tools` (registered) is the narrowest set that does the job, listed
      explicitly.
- [ ] No "tell the user…" language — the result is data for the caller.
- [ ] Ambiguity is flagged, never blocked on (no mid-run questions).
- [ ] `description` (registered) leads with the artifact and has explicit
      NOT-for clauses.
