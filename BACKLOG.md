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

---

## Run 2 — insight-linker back-catalogue triage (2026-09-12)

The second bot run left 100 open issues (#30–#133; #37 and #91–#93 were
already closed). Every open issue was re-read and mapped onto this repo's
real artifacts (the 9 skills, `AGENTS.md`, `rules/`, `templates/`, repo
conventions). Three late June issues (#27–#29) missed the run-1 window and
were incorporated in run 2 as well. Result:

| Outcome | Count | Where |
|---|---|---|
| Incorporated into new tickets | 43 | T4–T7 below |
| Actioned by the triage itself | 2 | #131, #132 |
| Closed won't-do / duplicate / out-of-scope | 58 | tables below |

Tickets below consolidate the incorporations; each lists the GitHub issues it
subsumes. Pick up tickets in later runs; do not re-open closed issues to
track them.

### T4 — AGENTS.md authoring-guide additions

**Type:** incorporate (docs — `AGENTS.md`)
**Consolidated GitHub issues:** #27, #28, #29, #31, #39, #41, #50, #79, #90, #95, #117, #118, #120, #122

Additions to the body-content guidelines (all within the agentskills.io spec —
guidance, not frontmatter):

- **VHS demo-tape conventions** (#27, #28, #29): avoid blobless partial clones
  in git-heavy skills; standardise browser-rendered GIF demos (VHS pattern)
  with Wait+Screen timing for piped output.
- **Subagent vs skill convention** (#31): document when to author a skill vs
  define an agent, plus the **cite-or-flag evidence discipline** — claims in
  skill instructions must cite a source file/reference or be flagged
  unverified.
- **Context engineering boundary** (#39): when authoring, state which context
  is static (baked into the skill) vs dynamic (assembled at runtime); evaluate
  agent trajectory, not just final output.
- **Curated context pairs** (#41): prefer human-curated example pairs over
  auto-generated ones in skill instructions.
- **Normalization-of-deviance guardrails** (#50): skills that touch code or
  infrastructure carry a safety checklist and an explicit escalation note.
- **Repo knowledge architecture** (#79): treat `AGENTS.md` as the
  table-of-contents for repo conventions; keep structured detail in each
  skill's `references/`.
- **Artifact-anchored references** (#90): pin API/CLI references in
  `references/` to specific versions.
- **Tool-use examples** (#95): include concrete usage examples with parameter
  correlations and format constraints, not just parameter lists.
- **Deterministic steps → scripts** (#117): prefer `scripts/` + direct
  execution over LLM tool-call round-trips for deterministic steps.
- **Contextual retrieval** (#118): prepend section-specific context to skill
  sections intended for retrieval.
- **Enforcement levels** (#120): mark instructions as advisory or
  deterministic so agents know which are hard gates.
- **Progressive verification ladder** (#122): in-prompt checks →
  goal-conditions → deterministic checks, escalating with stakes.

### T5 — dev-team orchestration hardening

**Type:** incorporate (`skills/development/dev-team`)
**Consolidated GitHub issues:** #62, #63, #64, #65, #66, #68, #71, #78, #80, #88, #98, #104, #105, #107, #125

- **Evaluator skepticism + dissent log** (#62): the QA agent logs
  disagreements with implementer claims instead of silently deferring.
- **Context-reset with structured handoff** (#63): long-running QA/PO agents
  reset context between phases via a structured handoff document.
- **Harness-assumption register** (#64): record which environment assumptions
  are Sacred vs Adaptable per phase.
- **Single-agent baseline** (#65): Phase 0 must justify any escalation to
  multi-agent.
- **Earned autonomy** (#66): grade task permissions on demonstrated
  reliability across runs.
- **"When agentic is the wrong fit"** (#68): six-case decision tree as a
  Phase 0 gate.
- **Evidence-backed stage transitions** (#71): a phase may not transition on
  unverified claims; worktree isolation stays mandatory.
- **Ralph Loop execution mode** (#78): stateless-but-iterative
  pick → implement → validate → commit loop as an alternative run mode.
- **Multi-prompt state graph** (#80): focused stages behind deterministic APIs
  instead of one monolithic prompt.
- **Issue-tracker-as-orchestrator** (#88): DAG decomposition with
  dependency-aware parallelism for workstream planning.
- **Git-based file locking** (#98): complements existing worktree isolation
  for agents sharing a worktree.
- **Wrong-log** (#104): one-sentence mistake entries, surfaced at phase
  review.
- **Back-pressure** (#105): calibrate agent autonomy to verification
  capacity.
- **Accountability contract** (#107): phase exit requires a checklist,
  evidence, and a named decision-maker.
- **Heterogeneous-model diversity** (#125): vary reviewer/agent models where
  available (PlanFlip failure mode).

### T6 — review-skill upgrades

**Type:** incorporate (`skills/development/pr-review-cycle`, `skills/development/python-review`)
**Consolidated GitHub issues:** #54, #67, #70, #72, #75, #87, #99, #100, #103, #110, #128

- **Test-change scrutiny** (#54): flag assertion-rewriting diffs for manual
  review; apply mutation testing where available.
- **Journey-level evaluation** (#67): assess intermediate agent decisions,
  not just final output.
- **Peer-advisory review** (#70): production-bound changes get human review
  beyond automated gates.
- **Verdict fingerprint binding** (#72): bind review verdicts to the commit
  SHA they reviewed; reject stale re-use.
- **Deterministic self-verification** (#75): recompute-then-compare instead of
  trusting agent recall; confirm required calls were actually made.
- **Risk-calibrated review depth** (#87): tier changes by risk and calibrate
  review depth accordingly.
- **Ensemble diverse reviewers** (#99): run architecturally distinct review
  passes in parallel for high-risk changes.
- **Reasoning-trace capture** (#100): agent-generated PRs embed intent and
  decision rationale.
- **Structured review rubric** (#103): correctness, maintainability,
  efficiency, security, tests.
- **Stale-eval detection** (#110): re-derive evaluations from updated data
  after any rewrite.
- **Detection-style validation ladder** (#128): anti-overfit checks and
  replay against real inputs for agent-generated artifacts.

### T7 — repo governance & behavioural baseline

**Type:** incorporate (repo-level: `rules/`, CI, `AGENTS.md` governance)
**Consolidated GitHub issues:** #76, #94, #109

- **AGENTS.md as diagnostic** (#76): review context files for codebase smells
  when they keep growing; prune stale guidance.
- **Behavioural principles** (#94): encode honor-the-request,
  protect-existing-work, and scale-proportional-response as repo rules.
- **Skills-as-system-of-record** (#109): immutable versioning, ownership
  metadata, CI validation of skill structure.

### Actioned in run 2

- **#131** — wire `AGENTS.md` to `BACKLOG.md`: done — `AGENTS.md` gained a
  "Triage & backlog" section pointing here, with the per-change context-draft
  requirement.
- **#132** — this triage: all 100 open issues processed; counts in the table
  above.

### Closed as won't-do (run 2, for the record)

Closed on GitHub with a comment; listed so the decision is traceable.

**Hermes-ecosystem (8)** — presuppose Hermes infrastructure absent from this repo:

| # | Title (short) | Reason |
|---|---|---|
| 106 | typed-object agent pattern | No agent-framework code layer in this repo. |
| 108 | graph-over-loop control flow | Hermes orchestration infra; dev-team's phase graph is already fixed. |
| 111 | evaluation funnel | No eval-harness skill here (June #5/#6 class). |
| 112 | plan readiness evaluator | Same missing-eval-harness class. |
| 113 | memory decay/consolidation | Hermes memory services, not skill content. |
| 114 | Zombie Agent defense | Memory-provenance infra layer. |
| 115 | LLM surrogate evaluation | Eval-harness infra. |
| 119 | expert-curation metadata | Non-spec metadata plus curation infra. |

**Conversation-scratch (13)** — philosophy/style items from specific conversations, or overlapping an implemented/rejected pattern:

| # | Title (short) | Reason |
|---|---|---|
| 33 | progressive disclosure for MCP-heavy skills | Repo already implements spec progressive disclosure; no MCP-heavy skills. |
| 34 | declarative directives over ALL-CAPS | Style preference; no concrete artifact. |
| 38 | tiered review + circuit-breaker | Overlaps T6 risk-calibrated depth (#87); auto-merge infra out of scope. |
| 42 | credential-vault / session-as-context | Vault/infra (June #11 class). |
| 43 | task-driven architecture rule | Covered by AGENTS.md end-state guidance. |
| 45 | untrusted-LLM-output / assume-breach | Infra posture (June #11 class). |
| 47 | anti-rationalization tables | Prompt-trick; spec and end-state guidance preferred. |
| 48 | six-level autonomy taxonomy | Overlaps T5 earned-autonomy (#66). |
| 49 | skills-as-code lifecycle | Overlaps T7 #109; CI/CD governance out of scope here. |
| 51 | agent-aware DX / auto-merge | Hermes DX infra. |
| 52 | curation quality metrics | Overlaps rejected #119. |
| 53 | intent-capture for PRs | Overlaps T6 #100. |
| 57 | testing-as-prerequisite | Already covered: T2 push gate plus AGENTS.md validation loops. |

**Duplicates (10):**

| # | Title (short) | Duplicate of |
|---|---|---|
| 32 | eval assertions test quality | T2 #18 noise-reduced verification. |
| 35 | contract-re-read pattern | T2 reviewer-overreach guard. |
| 36 | flake attribution protocol | pr-review-cycle verify-against-code (T2 #14). |
| 40 | prototype-as-spec eval template | T1: upstream skill-creator eval territory. |
| 44 | minimal-output grepable harness | T2 #18. |
| 46 | six named orchestration patterns | dev-team already implements them; overlaps #48. |
| 55 | two-stage classifier/permissions | T5 #66. |
| 56 | AI-resistant eval design | T1 upstream eval territory. |
| 58 | reconsolidation-upon-retrieval | Memory-aware skills don't exist here. |
| 61 | CI/CD-gated promotion | T7 #109; CI out of scope. |

**Out-of-scope (27)** — target missing skills or infrastructure, or propose non-spec frontmatter (same classes as June's table):

| # | Title (short) | Reason |
|---|---|---|
| 30 | blog-scraper DeepMind selectors | `blog-scraper` doesn't exist here (June #20/#24 class). |
| 59 | prospective indexing at write time | Memory-capture infra (insight-linker/memex). |
| 60 | procedural memory poisoning defences | Memory infra. |
| 69 | semantic hallucination prevention | Data-assistant domain; no data skills here. |
| 73 | break-glass Boundary + Vault | Infrastructure. |
| 74 | env-var isolation for profiles | Hermes runtime recipe, not repo content. |
| 77 | comprehension-debt auditing | Org process, not skill content. |
| 81 | production-trace self-improvement | Eval infrastructure. |
| 82 | conformal action certificates | Infrastructure. |
| 83 | privacy-budget ledgers | Infrastructure. |
| 84 | type-conditioned staleness metadata | Memory infra plus non-spec metadata. |
| 85 | golden-principles GC lints | No agent-enforced lint mechanism here. |
| 86 | zero-trust identity propagation | Infrastructure. |
| 89 | per-tool approval metadata | Non-spec frontmatter. |
| 96 | egress allowlist-as-capability | Infrastructure. |
| 97 | deferred config-loading | Agent-runtime behaviour, not repo content. |
| 101 | programmatic tool calling | Hermes tool-calling layer. |
| 102 | direct-API-first | No integration skills in this repo. |
| 116 | just-in-time context retrieval | Already covered by AGENTS.md progressive-disclosure conventions. |
| 121 | prerequisites/no-go frontmatter | Non-spec frontmatter; prose already in AGENTS.md. |
| 123 | trust-tiered skill taxonomy | Non-spec metadata taxonomy. |
| 124 | execution-provenance ledger | Infrastructure. |
| 126 | selective context persistence | Hermes session infrastructure. |
| 127 | boundary-aware metadata (BASM) | Non-spec frontmatter. |
| 129 | enforced model routing | Hermes routing-layer concern. |
| 130 | cost-equation management | No scheduled workflows in this repo. |
| 133 | retrieval-drift monitoring | No vector-search skills here. |
