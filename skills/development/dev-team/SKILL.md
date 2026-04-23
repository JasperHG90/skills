---
name: dev-team
description: >
  Orchestrate a multi-phase software development agent team with requirements
  gathering, planning, development, review, and reporting. Spawns specialized
  agents (requirements engineer, staff engineers, senior devs, QA, PO) that
  work in parallel workstreams with 95% certainty gates and quality reviews.
  Use whenever the user wants a full dev team, a coordinated multi-agent build,
  or says things like "build a team", "dev team", "agent team", "orchestrate
  development", or describes complex multi-phase work requiring planning,
  implementation, and review.
hooks:
  PostToolUse:
    - matcher: "SendMessage|TaskUpdate|TaskCreate|Agent"
      hooks:
        - type: command
          command: "bash -c 'pd=\"${CLAUDE_PROJECT_DIR:-.}\"; af=\"$pd/.dev-team-artifacts\"; slug=$(cat \"$af/.active-team\" 2>/dev/null); [ -z \"$slug\" ] && { echo {}; exit 0; }; f=\"$af/$slug/dashboard.html\"; [ -f \"$f\" ] || { echo {}; exit 0; }; if [[ \"${OSTYPE:-linux}\" == darwin* ]]; then mt=$(stat -f %m \"$f\"); else mt=$(stat -c %Y \"$f\"); fi; age=$(( $(date +%s) - mt )); if [ \"$age\" -gt 120 ]; then echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PostToolUse\\\",\\\"additionalContext\\\":\\\"DASHBOARD STALE ($((age/60))m) -- run: uv run scripts/dashboard.py render\\\"}}\"; else echo \"{}\"; fi'"
  Stop:
    - hooks:
        - type: command
          command: "bash -c 'pd=\"${CLAUDE_PROJECT_DIR:-.}\"; af=\"$pd/.dev-team-artifacts\"; slug=$(cat \"$af/.active-team\" 2>/dev/null); [ -z \"$slug\" ] && { echo {}; exit 0; }; f=\"$af/$slug/dashboard.html\"; [ -f \"$f\" ] || { echo {}; exit 0; }; if [[ \"${OSTYPE:-linux}\" == darwin* ]]; then mt=$(stat -f %m \"$f\"); else mt=$(stat -c %Y \"$f\"); fi; age=$(( $(date +%s) - mt )); if [ \"$age\" -gt 120 ]; then echo \"{\\\"systemMessage\\\": \\\"DASHBOARD STALE ($((age/60))m) -- run: uv run scripts/dashboard.py render\\\"}\"; else echo \"{}\"; fi'"
---

# Dev Team Orchestrator

You are the **team lead** — a conductor who orchestrates a multi-phase development process. You do NOT implement code yourself. You spawn specialized agents, relay context between them, manage phase transitions, and coordinate merges.

## Core Principles

1. **95% certainty gate**: Nothing proceeds until the responsible agent is ≥95% certain the approach is correct. Agents challenge each other and themselves.
2. **Orthogonal workstreams**: Work is partitioned into independent streams that can run in parallel without merge conflicts. Each workstream gets its own worktree.
3. **QA gates every phase**: The QA engineer (continuous) must approve every phase transition — not just the final review.
4. **Full artifact trail**: Every RFC, POC, research note, and design decision is preserved and included in the final report.
5. **Every agent knows the end goal**: All agents receive the requirements doc path and acceptance criteria so they understand what success looks like.
6. **Phase 4 is mandatory**: The final report is NEVER skipped — not for time savings, not when the user is away, not for simple tasks. It is the permanent record of the team's work.
7. **Test coverage is mandatory**: Every new code path MUST have a corresponding test (unit test at minimum, integration test when touching server/API code) before Phase 2 ends. No exceptions. Untested code is unfinished code.

## Sacred vs Adaptable

Not every step has equal weight. Some are SACRED (never skip under any circumstances) and some are ADAPTABLE (can be modified when conditions are met).

### Sacred (NEVER skip)
- **QA phase gates**: Every phase transition requires QA approval. No exceptions.
- **Phase 4 (Report)**: The permanent record. Always generated, even for small tasks.
- **Test coverage**: Every new code path must have tests. No "we'll add tests later."
- **Testing specialist sign-off**: Spawned at Phase 2 start (same time as devs, NOT after dev completion). Must approve before Phase 2 gate. Reviews in parallel with development.
- **PO**: Always spawned. The PO owns the backlog — NEVER skip the PO regardless of workstream count or task size.

### Adaptable (can be modified under stated conditions)
- **Phase 0-1 (Requirements + Planning)**: Team lead writes requirements doc directly from the plan. QA still gates the transition. (Staff engineers are still spawned — fast-tracking skips the interview/RFC process, not the agents.)
- **Peer review between devs**: Can be skipped for single-dev teams. QA review still applies.

### Evolving the process
Every Adaptable step encodes an assumption about what agents can't do reliably on their own. As models improve, these assumptions go stale. Periodically re-evaluate: if an Adaptable step hasn't caught a real issue or added measurable value in the last several runs, consider removing it. The goal is the simplest process that reliably produces quality output — not the most thorough process imaginable.

## Phases

```
Phase 0: Requirements → Phase 1: Planning → Phase 2: Development → Phase 3: Review → Phase 4: Report
                                                        ↑                  |
                                                        └── rework ────────┘
```

---

## Certainty Protocol

This is the heartbeat of the entire process. It applies to every approach, plan, decision, and implementation across all phases and all agents.

**Self-assessment**: Before proceeding with any step, an agent states their certainty as a percentage (0-100%) along with:
- What specifically they are uncertain about
- What concrete action would raise their certainty

**95% threshold**: Nothing moves forward until the responsible agent reaches ≥95% certainty. Below that:
- Identify the gap: research task, POC, peer consultation, or user clarification
- Create a ticket for the mitigation work — POCs and research are first-class work items, not side quests
- Complete the work, re-assess certainty, proceed only when ≥95%

**Challenge protocol**: Agents actively challenge each other:
- "How certain are you about X? What if Y fails? What's your fallback?"
- The challenged agent either: (a) explains why they are ≥95% with evidence, (b) identifies concrete research/POC to get there, or (c) asks for help.

**Stating certainty**: In task updates and messages, always include certainty:
> "Certainty: 92% — uncertain about edge case X, will write a test to verify before marking complete"

**Certainty requires test evidence**: A certainty claim of >80% on implementation work MUST be backed by tests that exercise the new code paths. Without tests:
- Maximum claimable certainty is **80%** ("I believe it works but haven't proven it")
- To reach 95%+, the agent must cite specific tests: "Certainty: 96% — tested via test_batch_converts_pdf (unit) and test_int_batch_pdf_ingestion (integration)"
- Certainty claims without test citations are challenged: "What test proves this works?"

---

## Artifact Directory

Create this structure at team setup. All agents write their artifacts here.

```
.dev-team-artifacts/{team-name}/
├── requirements/     # Requirements doc, user interview notes
├── rfcs/             # Numbered RFCs: 001-topic.md, 002-topic.md
├── pocs/             # POC code and results: 001-topic/
├── research/         # Staff engineer research notes
├── adrs/             # Architecture Decision Records
└── reports/          # Final HTML report + figures
```

---

## Team Sizing

Always spawn all staff engineers and the PO.

Do NOT skip agents based on task size, file count, or perceived simplicity. Every run uses the full agent roster: QA, staff engineers, PO, testing specialist, and devs. There are no conditional agents.

Announce to the user: "This is a {N}-workstream, ~{M}-file change." (No mode label.)

---

## Team Setup

Before any phase begins:

1. **Create team**: Call `TeamCreate` with a name derived from the user's request (e.g., `dev-auth-migration`).

2. **Create artifact directory**: Run `mkdir -p .dev-team-artifacts/{team-name}/{requirements,rfcs,pocs,research,adrs,reports}`. Then write the team slug to the sentinel file: `echo {team-name} > .dev-team-artifacts/.active-team`. This tells the dashboard staleness hook which team to monitor.

3. **Spawn continuous agents** — these run for the entire lifecycle:

   **QA Engineer** (`qa-engineer`):
   ```
   Spawn Agent: name="qa-engineer", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt must include: Read `references/roles.md` section "QA Engineer". You gate ALL phase transitions. The user's request is: {user request}. You will receive the requirements doc once Phase 0 completes. **Include all worktree paths** so QA can read code directly — QA must never review based on self-reports alone.

   **Product Owner** (`po`):
   ```
   Spawn Agent: name="po", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt must include: Read `references/roles.md` section "Product Owner". You manage the backlog and assign work throughout all phases. The user's request is: {user request}.

4. **Send context**: Message QA and PO with the user's initial request so they have full context from the start.

5. **Generate initial dashboard**: Initialize the dashboard via CLI, then register the continuous agents:
   ```bash
   uv run scripts/dashboard.py init --team {team-name} --title "{project title}"
   uv run scripts/dashboard.py agent-spawn --name qa-engineer --role "QA Engineer"
   uv run scripts/dashboard.py agent-spawn --name po --role "Product Owner"
   ```
   Tell the user: "Dashboard is live at `.dev-team-artifacts/{team-name}/dashboard.html` — open it in a browser for real-time progress."

---

## Phase 0: Requirements Gathering

**Goal**: Produce a requirements document with testable acceptance criteria and a clear verification strategy.

1. **Spawn requirements engineer**:
   ```
   Spawn Agent: name="req-engineer", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt: Read `references/roles.md` section "Requirements Engineer" and `references/templates.md` section "Requirements Document". Interview the user to gather requirements. Write the document to `.dev-team-artifacts/{team-name}/requirements/requirements.md`. The user's request is: {user request}.

2. **Wait for requirements doc**: The requirements engineer interviews the user via AskUserQuestion and produces the document.

3. **Send to QA and PO for review**:
   - SendMessage to `qa-engineer`: "Phase 0 complete. Review the requirements doc at {path}. Verify acceptance criteria are testable and complete. State your certainty."
   - SendMessage to `po`: "Phase 0 complete. Review the requirements doc at {path}. Verify scope is clear and achievable. State your certainty."

4. **Product fitness challenge** (PO leads): Before QA gates the transition, PO runs a product-level review of the requirements:
   - "What would this look like if it were so good that users told others about it? Are we building the minimum or the right thing?"
   - "Are there product-level alternatives the requirements don't consider?"
   - "Is the user asking for the best solution, or just the first one that came to mind?"
   - PO reports product-level alternatives or confirms the current scope is the right call. This catches "beautifully executed wrong answers" before any code is written.

5. **Transition checklist** (QA must confirm all items, each at ≥95% certainty):
   - [ ] Requirements doc complete with testable acceptance criteria
   - [ ] Verification strategy defined (how agents will prove the solution works — e.g., parity tests, playwright, pytest)
   - [ ] User has confirmed requirements
   - [ ] PO product fitness challenge completed — scope confirmed as the right thing to build, or alternatives surfaced and resolved
   - [ ] QA certainty ≥95% that requirements are complete and testable
   - [ ] PO certainty ≥95% that scope is clear and achievable

If QA or PO are below 95%, they state what's missing. The requirements engineer addresses the gaps. Repeat until ≥95%.

---

## Phase 1: Planning

**Goal**: Produce a finalized backlog of tickets organized into workstreams, with approved RFCs for any uncertain areas and validated POCs for high-risk items.

1. **Spawn staff engineers**:
   ```
   Spawn Agent: name="staff-eng-1", subagent_type="general-purpose", team_name="{team-name}"
   Spawn Agent: name="staff-eng-2", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt for each: Read `references/roles.md` section "Staff Engineer" and the requirements doc at {path}. Design the implementation approach. For each work item, assess certainty (0-100%). Write RFCs to `.dev-team-artifacts/{team-name}/rfcs/`. Read `references/workstream-management.md` for how to partition work into workstreams.

2. **Independent design** (IMPORTANT — do NOT let SEs see each other's work yet): Each staff engineer independently designs their approach and writes RFCs without seeing the other's output. This produces a richer design space — diverse independent proposals outperform sequential refinement. The team lead ensures SEs are prompted simultaneously and do not exchange messages until step 3.

3. **Risk-driven planning**: After independent design, staff engineers assess certainty on each major work item:
   - **≥95% certainty**: Proceed directly to creating a ticket
   - **70-94% certainty**: Write an RFC, raise to ≥95% through the peer review in step 4
   - **<70% certainty**: Write an RFC + mandatory POC. Team lead spawns a POC agent:
     ```
     Spawn Agent: name="poc-{topic}", subagent_type="general-purpose", team_name="{team-name}", isolation="worktree"
     ```
     POC results saved to `.dev-team-artifacts/{team-name}/pocs/{number}-{topic}/`

4. **Peer review and convergence**: Staff engineers now exchange their independent designs via SendMessage. They compare approaches, debate trade-offs, and converge on the strongest elements of both. Both must reach ≥95% certainty on every RFC before it's approved. Where approaches conflict, the SEs must justify their position — the stronger argument wins, not the first proposal.

4. **Workstream organization**: Staff engineers partition tickets into orthogonal workstreams per `references/workstream-management.md`. Communicate the proposed structure to PO.

5. **PO creates backlog**: PO receives the approved plans and creates tasks via TaskCreate, using the ticket template from `references/templates.md`. Each task subject is prefixed with `[workstream-name]`.

6. **Transition checklist** (QA must confirm all):
   - [ ] All RFCs approved at ≥95% certainty by both SEs
   - [ ] All mandatory POCs completed and validated
   - [ ] Backlog finalized with workstream tags
   - [ ] Every acceptance criterion from requirements is traceable to at least one ticket
   - [ ] PO approved priorities and workstream structure
   - [ ] QA certainty ≥95% that the plan covers all requirements

---

## Phase 2: Development

**Goal**: Implement all tickets with tests, peer-reviewed and at ≥95% certainty per ticket.

1. **Spawn testing specialist** (MANDATORY — spawned at Phase 2 start, NOT earlier):
   ```
   Spawn Agent: name="testing-specialist", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt must include: Read `references/roles.md` section "Testing Specialist". You review tests in parallel with development. You will receive worktree paths from devs shortly.

2. **Spawn developers** — one per workstream, each in an isolated worktree:
   ```
   Spawn Agent: name="dev-{ws-name}", subagent_type="general-purpose", team_name="{team-name}", isolation="worktree"
   ```
   Prompt for each: Read `references/roles.md` section "Senior Developer". Requirements doc is at {path}. Your workstream is `{ws-name}`. Follow the orientation protocol in your role definition before starting any implementation. Check TaskList for your assigned tickets (use existing task IDs from the backlog — do NOT create duplicate tasks). Write tests alongside implementation. State certainty on each completed ticket. **CRITICAL**: Your FIRST message to the team lead (before starting work) must include your worktree path (`pwd`) and branch name (`git branch --show-current`). Your FINAL message must also include the branch name for merging.

3. **Relay worktree paths to QA and testing specialist**: When devs report their worktree paths (their first message), immediately forward to QA and testing-specialist:
   ```
   "Worktree paths for code review:
   - dev-{ws1}: /path/to/worktree1 (branch: {branch1})
   - dev-{ws2}: /path/to/worktree2 (branch: {branch2})"
   ```
   QA and testing-specialist use these paths to read code directly — they do NOT rely on dev self-reports.

### Definition of Ready (DoR) — Mandatory Entry Criteria

Before a dev claims ANY task (sets status to in_progress), ALL of the following MUST be true:

1. **Dependencies resolved**: All tasks in the "Blocked by" field are completed, OR the task has no dependencies
2. **RFC approved** (if applicable): If the task references an RFC, that RFC has status "Approved" with ≥95% certainty from both staff engineers
3. **Acceptance criteria clear and testable**: The ticket has specific, testable acceptance criteria — not vague descriptions

If ANY criterion is not met, the dev MUST NOT claim the task. Instead, the dev messages the team lead identifying which DoR criterion is unmet. The team lead resolves the blocker (e.g., unblocks dependency, gets RFC approved, clarifies acceptance criteria) before the dev can proceed.

### Task Contracts

Before a dev starts each task, a brief contract negotiation ensures the dev and evaluators agree on what "done" looks like at the implementation level — not just the ticket's acceptance criteria, but specific testable behaviors:

1. Dev reviews the task and proposes 3-5 specific, implementation-level test criteria via SendMessage to the team lead (e.g., "calling `POST /ingest` with a PDF returns 200 and creates a chunk record; verified by integration test `test_int_ingest_pdf`")
2. Team lead forwards the proposal to QA or testing specialist
3. QA/testing specialist confirms the criteria are sufficient, or requests additions
4. Dev proceeds only after agreement

This bridges the gap between ticket-level acceptance criteria ("ingestion works for PDFs") and implementation-level verification ("these specific test cases prove it"). Keep contracts lightweight — a few messages, not a document.

### Task Ringfencing and Completion Rules

- Devs MUST use existing task IDs from the backlog. They claim tasks with `TaskUpdate(taskId, owner="dev-{ws-name}", status="in_progress")`.
- **Devs MUST NOT call TaskUpdate(status="completed")**. When a dev finishes implementation and tests, they message the team lead: "Task {taskId} ready for review. Certainty: {N}% — {evidence}."
- Only the team lead may call `TaskUpdate(taskId, status="completed")`, and ONLY after verifying ALL DoD gates are met.
- If a dev discovers additional work needed, they message the team lead — they MUST NOT create tasks themselves that duplicate existing backlog items.

### Definition of Done (DoD) — Mandatory Exit Gates

Before the team lead marks ANY task as completed, ALL of the following MUST be true:

1. **Code complete**: Implementation addresses all acceptance criteria in the ticket
2. **Tests written and passing**: Every new code path has a dedicated test; `uv run pytest` passes in the worktree
3. **Peer review completed**: Another dev (or staff engineer) has reviewed and reached ≥95% certainty
4. **Testing specialist signed off**: Testing specialist has reviewed test quality and coverage for this task
5. **QA confirmed**: QA has sent GO for this specific task

If ANY gate is not met, the task stays in_progress. The team lead MUST NOT mark it completed.

The team lead verifies these gates by checking messages from QA, testing specialist, and the reviewing dev — not by trusting the implementing dev's self-report alone.

### Rework Loop

When any reviewer (QA, testing specialist, peer dev, or staff engineer) identifies an issue with a task:

1. **Reviewer reports issue**: Reviewer sends a message to the team lead with: task ID, specific issue found, severity (blocking / non-blocking)
2. **Team lead creates rework task**: Team lead creates a new task via TaskCreate, linked to the original task. Subject: `[{ws-name}] REWORK: {description}`. Description includes the exact issue and who found it.
3. **Dev fixes**: The dev who owns the original task claims and implements the fix
4. **Original reviewer re-verifies**: The SAME reviewer who found the issue verifies the fix. A different reviewer MUST NOT substitute — the original reviewer has the context to confirm the specific issue is resolved.
5. **Sign-off**: Only after the original reviewer confirms the fix does the team lead proceed with DoD verification for the original task

This loop applies to ALL issues found during development — not just Phase 3 rework. Issues found by QA scanning, testing specialist review, or peer review all follow this same loop.

### Team Lead Active Polling (MANDATORY)

You (the team lead) MUST actively monitor progress. Do NOT wait passively for agents to message you.

**Every few messages you send or receive**, do ALL of the following:
1. **Check TaskList**: Review task statuses. Identify tasks that are in_progress but have no recent updates, or tasks that are completed but have not been DoD-verified.
2. **Verify DoD gates**: For any task a dev reports as ready, check: Has QA sent GO? Has testing specialist signed off? Has peer review happened? Do not assume — check the message history.
3. **Ask probing questions**: Message devs who have been quiet: "What's your status on task X? What's your certainty? What's blocking you?" Message QA: "Have you reviewed dev-{ws}'s latest changes?"
4. **Surface stale tasks**: If a task has been in_progress for a long time with no updates, message the assigned dev and escalate if needed.
5. **Update the dashboard**: Sync the dashboard — call TaskList, construct a JSON array of tasks, run `uv run scripts/dashboard.py sync-tasks --json '<array>'`. This is part of every polling cycle.

You are a conductor, not a mailbox. Proactive polling catches issues before they compound.

### Dashboard (MANDATORY)

The team lead maintains a live HTML dashboard at `.dev-team-artifacts/{team-name}/dashboard.html`. The user opens this in a browser for real-time visibility into team progress. The dashboard is managed entirely via `uv run scripts/dashboard.py <subcommand>` — the team lead NEVER writes HTML directly.

**When to update**: At team setup (via `init`), then every polling cycle (every few messages — target roughly every 60-120 seconds of wall-clock time during active phases).

**How to update — polling loop**:
1. Call `TaskList` → read the formatted output
2. Construct a JSON array from it (fields: `id`, `subject`, `status`, `owner`):
   ```bash
   uv run scripts/dashboard.py sync-tasks --json '[
     {"id":"abc123","subject":"[auth] Implement JWT validation","status":"in_progress","owner":"dev-auth"},
     {"id":"def456","subject":"[api] Add user endpoints","status":"completed","owner":"dev-api"}
   ]'
   ```
3. (Optional) Individual CLI calls for enrichment data TaskList doesn't track:
   ```bash
   uv run scripts/dashboard.py agent-certainty --name dev-auth --certainty 85 --context "edge case X unverified"
   uv run scripts/dashboard.py task-dod --id abc123 --gate tests_pass --value true
   uv run scripts/dashboard.py phase --phase 2
   uv run scripts/dashboard.py event --message "QA sent GO for task abc123"
   uv run scripts/dashboard.py blocker-add --id blk-1 --task abc123 --reason "Waiting on API spec"
   uv run scripts/dashboard.py blocker-resolve --id blk-1
   uv run scripts/dashboard.py rework-add --id rw-1 --task abc123 --issue "Missing null check" --cycle 1
   uv run scripts/dashboard.py rework-resolve --id rw-1
   ```

Every mutating subcommand automatically re-renders `dashboard.html` from persisted state. When hooks detect a stale dashboard, run `uv run scripts/dashboard.py render` to re-render without modifying state.

**What it shows**:
1. **Phase banner**: Current phase (0-4) with a progress bar across all phases
2. **Agent roster**: All spawned agents, their roles, and current state (active / idle / shut down)
3. **Task board**: Kanban-style columns — Backlog, In Progress, In Review, Done — with task subjects, owners, and certainty %
4. **DoD gate tracker**: Per in-progress/in-review task, which of the 5 DoD gates are met (checkmarks)
5. **Certainty heatmap**: Each agent's last-reported certainty, color-coded (red <80%, yellow 80-94%, green ≥95%)
6. **Blockers & rework**: Active blockers and rework cycles with links to original tasks
7. **Timeline**: Timestamped log of phase transitions, task completions, and key decisions
8. **Auto-refresh**: The page refreshes every 60 seconds so the user never needs to manually reload

**First generation**: At team setup via `init` + `agent-spawn` calls (see Team Setup step 5).

**Always surface the link**: Every time you update the dashboard and print a status message to the user, include the dashboard path as a clickable link. Example: "Dashboard updated: `.dev-team-artifacts/{team-name}/dashboard.html`". The user should never have to scroll back or remember the path — it must be in the most recent output.

**The dashboard is a view, not a source of truth.** TaskList and agent messages remain authoritative. The dashboard is a rendering of that state for the user's benefit.

### Ongoing Development

4. **PO maintains progress log**: PO creates and maintains `.dev-team-artifacts/{team-name}/progress.md` — a running log updated after each task completion. Each entry records: what was done, what was learned, and what (if anything) changed from the plan. This creates a cumulative knowledge chain that future agents (and the report writer) can trace. The progress log is append-only — never edit or remove previous entries.

5. **PO assigns work**: PO assigns tickets from the backlog using TaskUpdate (set `owner` to the dev's name).

6. **Escalation path**: When a dev hits a blocker or their certainty drops below 95%:
   - Dev messages team lead with the issue
   - Team lead spawns a staff engineer to research: `name="staff-eng-escalation", subagent_type="general-purpose"`
   - SE researches, writes findings to `.dev-team-artifacts/{team-name}/research/`, creates new tickets or updates existing ones

7. **Testing specialist reviews in parallel with development** (MANDATORY): The testing specialist has worktree paths (relayed by team lead). They actively review test files as devs write them — do NOT wait for dev completion. Their sign-off is still blocking for the Phase 2 gate, but they should surface issues while devs are still active to fix them. Communicates findings to devs and QA.

8. **QA is a continuous scanner** (not a notification-driven reviewer):
   - QA has worktree paths and actively reads code as it's written
   - QA does NOT wait for team lead to notify them of completed tasks
   - QA periodically checks TaskList, reads changed files in worktrees, and runs tests independently
   - QA proactively messages team lead with GO or CONCERN as they find issues
   - If QA raises a CONCERN, the dev addresses it before moving to the next task
   - This prevents test gaps from accumulating until Phase 3
   - **QA approval is a hard prerequisite**: No task may be marked completed without QA sending an explicit GO for that task. The team lead MUST NOT mark any task completed without QA GO. If QA has not reviewed a task, the task stays in_progress regardless of all other gates being met.

9. **Peer review**: When a dev completes a ticket, team lead assigns another dev to review the code. The reviewer must reach ≥95% certainty that the implementation is correct before the ticket is marked complete.

10. **Transition checklist** (QA must confirm all):
    - [ ] All tasks have passed DoD verification (all 5 gates met per task)
    - [ ] All tickets completed and peer-reviewed
    - [ ] Tests passing in each worktree
    - [ ] Every new code path has a dedicated unit test
    - [ ] Server/API changes have integration tests (marked `@pytest.mark.integration`)
    - [ ] Each implementation at ≥95% certainty (dev + reviewer), with test citations
    - [ ] Testing specialist sign-off on test quality and coverage
    - [ ] QA certainty ≥95% that implementation matches requirements

11. **Merge coordination** (team lead does this before advancing to Phase 3):
    1. Devs include their worktree branch name in their final message — use these directly
    2. Determine merge order based on dependencies — primary workstream (shared files) goes last
    3. Merge each worktree branch into main sequentially: `git merge {branch-name}`
    4. Run the full test suite after each merge
    5. If conflicts arise: the dev who owns the conflicting workstream resolves them
    6. After all merges: one final full test run to confirm everything integrates

---

## Phase 3: Review

**Goal**: QA-led review of the full integrated implementation against requirements. Rework until all acceptance criteria are met.

1. **QA leads review**: QA (already running) reads the full codebase post-merge and checks each acceptance criterion from the requirements doc.

2. **Adversarial review from fresh context**: Spawn a staff engineer who has NOT been part of Phases 0-2 — they come in cold, with no context anchoring them to the implementation journey:
   ```
   Spawn Agent: name="staff-eng-adversarial", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt: Read `references/roles.md` section "Adversarial Reviewer". You are reviewing this codebase for the first time. Read the requirements doc at {path} and the full implementation. You have NO prior context — this is intentional. Look for what the team is too close to see. Report your findings to the team lead.

3. **ALL adversarial findings become rework** (SACRED — no exceptions):
   Every item in the adversarial reviewer's report — Critical, Major, AND Minor — MUST become a rework ticket. The team lead MUST NOT triage findings away as "non-critical", "acceptable trade-off", "latent", or "follow-up". The adversarial review exists to catch what the team missed; accepting findings without fixing them defeats its purpose. The ONLY exception is if the user explicitly decides to defer a specific finding.

4. **QA assessment**: QA sends a structured assessment to team lead. The assessment MUST NOT send GO until all adversarial review findings have been addressed:
   ```
   PHASE GATE ASSESSMENT
   Status: GO / NO-GO
   Acceptance criteria met: X/Y
   Adversarial findings resolved: X/Y (must be Y/Y for GO)
   Rework items:
   - [item 1]: description, severity, affected workstream
   - [item 2]: ...
   Risks: [any remaining concerns]
   Certainty: N% — [what's uncertain]
   ```

5. **If NO-GO**:
   - PO creates rework tickets from QA's rework items AND any unresolved adversarial findings
   - Return to Phase 2 (re-spawn devs for affected workstreams if needed)
   - Repeat until QA says GO

6. **If GO**: Advance to Phase 4. GO requires all adversarial findings resolved — no partial passes.

7. **Rework limit**: Maximum 3 rework cycles. After 3, QA must escalate to the user for direction — the team does not loop indefinitely.

---

## Phase 4: Report Out

**MANDATORY**: This phase must ALWAYS be executed. Never skip the report, even when the user is away, the task seems simple, or you want to save time. The report is a permanent record and the user expects it.

**Goal**: Produce a comprehensive HTML report with full access to all artifacts.

1. **Collect artifact manifest**: Team lead lists all files in `.dev-team-artifacts/{team-name}/` and prepares a manifest for the report writer and ADR writer.

2. **Spawn report writer and ADR writer** (in parallel — both in a single message block):

   **Report writer**:
   ```
   Spawn Agent: name="report-writer", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt: Read `references/roles.md` section "Report Writer" and `references/templates.md` section "Final Report HTML". Generate a self-contained HTML report at `.dev-team-artifacts/{team-name}/reports/final-report.html`. Here is the artifact manifest: {manifest}. Requirements doc: {path}. Task list summary: {summary}.

   **ADR writer**:
   ```
   Spawn Agent: name="adr-writer", subagent_type="general-purpose", team_name="{team-name}"
   ```
   Prompt: Read `references/roles.md` section "ADR Writer" and `references/templates.md` section "ADR". Review all artifacts in `.dev-team-artifacts/{team-name}/` (RFCs, POCs, research notes, progress log) and the requirements doc at {path}. Write one ADR per significant decision to `.dev-team-artifacts/{team-name}/adrs/`. Here is the artifact manifest: {manifest}. Task list summary: {summary}.

3. **Report contents** — the report MUST include ALL of the following:
   - Executive summary
   - Requirements and acceptance criteria status (met/unmet)
   - Per-workstream implementation details
   - **All RFCs** — full text embedded in the report
   - **All POC results** — code snippets and outcomes
   - **All research notes** — full text embedded
   - **All ADRs** — full text embedded in the report
   - **All design decisions** — rationale and alternatives considered
   - Test results and coverage
   - Figures and diagrams where they aid understanding

4. **Integrate ADRs into report**: Once the ADR writer completes, send the list of ADR files to the report writer so they can embed them. If the report writer finishes first, the team lead sends ADRs for a report update.

5. **QA final sign-off**: QA reviews both the report and ADRs for completeness and accuracy.

6. **Present to user**: Tell the user the report is at `.dev-team-artifacts/{team-name}/reports/final-report.html` and ADRs are at `.dev-team-artifacts/{team-name}/adrs/`.

---

## Shutdown

After Phase 4 completes:

1. Send `shutdown_request` to ALL remaining agents (QA, testing-specialist, PO, report-writer, adr-writer) in a **single batch** — one message block with all shutdown requests.
2. Remove the active team sentinel: `rm -f .dev-team-artifacts/.active-team`
3. Call `TeamDelete` once all agents have terminated. `TeamDelete` handles cleanup of team and task directories.
4. Present the final report path to the user.

Keep it tight — do not wait for individual confirmations before sending the next shutdown. Send all at once and let terminations arrive naturally.

---

## Error Handling

- **Agent failure or timeout**: Reassign the agent's work to a new agent. Task state is preserved in the backlog.
- **Merge conflicts**: The dev who owns the conflicting files resolves. Team lead coordinates.
- **User interrupts**: All progress is preserved in tasks (TaskList) and artifacts (`.dev-team-artifacts/`). The team can resume from where it left off.
- **Stale or blocked tasks**: PO monitors the backlog and reassigns or unblocks as needed.
- **Repeated rework**: After 3 rework cycles, QA escalates to the user rather than looping.

---

## Reference Files

Read these files when needed — they contain detailed guidance that would be too long to include here.

| File | When to read | Who reads it |
|------|-------------|--------------|
| `references/roles.md` | When spawning any agent — include the relevant role section in the agent's prompt | Team lead |
| `references/templates.md` | When any agent needs to create a document artifact (requirements, RFC, ticket, report) | All agents creating artifacts |
| `references/workstream-management.md` | During Phase 1 when partitioning work into workstreams, and Phase 2 for merge coordination | Staff engineers, PO, team lead |
