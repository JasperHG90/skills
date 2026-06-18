# Backlog

Triaged work items for this skills repository, to be picked up in a later run.

## Triage context

All 26 open GitHub issues were filed automatically by the `insight-linker`
bot. The bot draws on a Memex knowledge base from a broader private "Hermes
Agent" ecosystem and references ~20 skills (`insight-linker`, `blog-scraper`,
`cluster-watchdog`, `daily-reflect`, `trader-advisor`, `researcher`,
`kanban-*`, `subagent-driven-development`, `evaluating-llms-harness`,
`hermes-agent-skill-authoring`, etc.) that **do not exist in this repo**.

This repo actually contains 9 general-purpose skills: `blueprint`, `dev-team`,
`pr-review-cycle`, `python-review`, `doc-write`, `readme-creator`,
`generate-art`, `deep-explain`, `release`.

Issues were sorted into: (a) actionable patterns that map onto the real skills
or the authoring guide (`AGENTS.md`) — captured as tickets below; (b) won't-do
items that presuppose missing skills/infrastructure or propose non-spec
frontmatter — closed on GitHub with a comment.

This repo follows the [agentskills.io](https://agentskills.io/specification)
spec. Any ticket that touches `SKILL.md` frontmatter must stay within the
spec's allowed fields (`name`, `description`, `license`, `compatibility`,
`metadata`, `allowed-tools`). Proposals to add custom top-level fields are
out of scope.

---

## T1 — Expand skill-authoring guidance — DONE (slimmed)

**Type:** incorporate (docs — `AGENTS.md`)
**Status:** done (2026-06-18)
**Consolidated GitHub issues:** #3, #8, #9, #10, #13 (partial), #17, #21 (partial), #26

Originally scoped as a broad authoring-guide rewrite. On review, most of it is
already covered upstream by Anthropic's
[`skill-creator`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md),
so the ticket was slimmed to only the non-redundant residue.

**Covered upstream — dropped, not re-documented here:**

- **Discovery-first descriptions** (#10) — `skill-creator` covers this and then
  some (treats `description` as the primary triggering mechanism; warns about
  *under*-triggering).
- **Three-tier progressive disclosure** (#9, #21) — already in `AGENTS.md` and
  identical in `skill-creator`.
- **Contract-to-validation mapping** (#3) — subsumed by `skill-creator`'s
  eval/assertion/benchmark harness.

**Implemented in `AGENTS.md` (the residue):**

- **"When NOT to use" / anti-conditions** (#17, #26).
- **End-state over step-by-step** (#17).
- **Explicit mapping tables over prose** (#26).
- **"Don't touch" / exclusion zones** for code-modifying skills (#26).
- Added a **Further reading** pointer to `skill-creator` for the upstream
  mechanics.

**Deliberately not done (out of scope):**

- **Tool/response design** (#8) — really about MCP *tool* design, tangential to
  authoring skills; no tool-wrapping skills in this repo.
- **Permission-budget / approval-fatigue frontmatter** (#13, #21) — proposed
  fields (`status`, `tested_models`, `permission_intensity`) are outside the
  agentskills.io spec.

---

## T2 — Scope-compliance and noise-reduced verification — DONE

**Type:** incorporate (`skills/development/pr-review-cycle`, `skills/development/dev-team`)
**Status:** done (2026-06-18)
**Consolidated GitHub issues:** #14, #18

Implemented in `pr-review-cycle`:

- **Reviewer-overreach guard** (#14, Phase 3): verify each finding against the
  cited code before patching; reject spurious findings rather than "fixing"
  correct code.
- **Scope discipline — pause and file** (#14, Phase 4): keep fixes scoped to
  the finding; file a follow-up issue instead of ballooning into a refactor.
- **Noise-reduced verification + scope-check + push gate** (#18, Phase 5):
  report a one-line verdict plus only relevant errors (no raw logs);
  `git diff --stat` to confirm every change traces to a finding; never push
  with failing tests/lint.
- **Stopping criterion** (#14, Phase 6): exit on "no NEW findings", not a
  theoretical zero.

Implemented in `dev-team`:

- Phase 3 rework limit now also terminates early on "no new adversarial
  findings" — same convergence criterion.

The `verifiers` frontmatter field proposed in #18 was intentionally not added
(outside the agentskills.io spec); the noise-reduction guidance is expressed in
prose instead.

---

## T3 — Multi-agent review-quality patterns for dev-team and python-review — DONE

**Type:** incorporate (`skills/development/dev-team`, `skills/development/python-review`)
**Status:** done (2026-06-18)
**Consolidated GitHub issues:** #15, #19

Implemented in `python-review`:

- **Lensed passes for high-stakes reviews** (#15): optional security /
  performance / correctness-concurrency focused passes, merged into the single
  review structure. Kept optional so small reviews stay one-pass.

Implemented in `dev-team`:

- **Reflect-and-evolve plan pass** (#19): added to Phase 1 convergence —
  generate → reflect → evolve before the plan is approved.
- **Design for LLM limitations** (#15): new Core Principle #8 — scoped tasks
  with explicit effort budgets and fresh agents per task. (Per-workstream
  worktree isolation already covers the git-task-lock idea from #15.)

---

## Closed as won't-do (for the record)

Closed on GitHub with a comment; listed here so the decision is traceable.

| # | Title | Reason |
|---|-------|--------|
| 2 | Throttling async gather | Niche Hermes/Jetson concern; no unbounded `asyncio.gather` in this repo's scripts. |
| 4 | Symphony board-driven orchestration | Presupposes Hermes board infra; overlaps existing `dev-team`. |
| 5 | Eval-driven self-improvement loop | Presupposes a non-existent `evaluating-llms-harness` skill. |
| 6 | Evaluation funnel | Same — no eval-harness skill exists here. |
| 7 | Background-coding-agent fleet pattern | Targets missing `subagent-driven-development`; fleet/Slack-dispatch infra out of scope. Context-file lessons captured via T1. |
| 11 | Security containment / egress / sandbox | Environment/infra layer (gVisor, Vault), not skill content; proposes non-spec `trust_level` frontmatter. |
| 12 | OpenAPI Links / `transitions` frontmatter | Proposes non-spec frontmatter; no API-wrapping skills in this repo. |
| 16 | D-MEM fast/slow routing | Targets missing `daily-reflect`/`insight-linker`/`memex-ops`; proposes non-spec `processing_gating` frontmatter. |
| 20 | Scraper Cloudflare resiliency | Targets missing `blog-scraper`/`hermes-maintenance`. |
| 22 | Long-running harness / checkpointing | Targets missing `cluster-watchdog`/`blog-scraper`/`researcher`; proposes spec changes. |
| 23 | Domain-expert context layer | Targets missing `trader-advisor`/`researcher`. |
| 24 | Name-based fallback for discovery | Targets missing `blog-scraper` KV indexing. |
| 25 | Elo tournament ranking | Presupposes non-existent eval skills. |
