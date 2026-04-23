# Document Templates

Templates for all artifacts produced during the dev-team workflow. Agents read the relevant section when creating a document.

---

## Requirements Document

Write to: `.dev-team-artifacts/{team-name}/requirements/requirements.md`

```markdown
# Requirements: {Project Title}

## Context

{Why this work is needed. What problem it solves. What prompted it.}

## Scope

### In Scope
{What will be built/changed}

### Out of Scope
{What is explicitly excluded — prevents scope creep}

## User Stories / Use Cases

### US-001: {Title}
As a {role}, I want to {action} so that {benefit}.

### US-002: {Title}
...

## Acceptance Criteria

| ID | Criterion | Verification Method | Status |
|----|-----------|-------------------|--------|
| AC-001 | {Specific, testable statement} | {How an agent proves this — e.g., "pytest test_auth.py passes"} | Pending |
| AC-002 | ... | ... | Pending |

Every criterion must be:
- **Specific**: no ambiguity about what "done" means
- **Testable**: an agent can programmatically verify it
- **Independent**: can be verified without relying on other criteria

## Verification Strategy

{Overall approach for proving the solution works}

- **Unit tests**: {what framework, what coverage expectations}
- **Integration tests**: {what services need to run, how — e.g., testcontainers, Docker Compose}
- **E2E tests**: {if applicable — e.g., playwright, browser automation}
- **Parity tests**: {if migration — compare old vs new behavior}
- **Manual verification**: {if any steps require human judgment}

## Interfaces and Contracts

{APIs, protocols, data formats that must be respected}

### Input
{What the system receives}

### Output
{What the system produces}

### Dependencies
{External systems, services, or libraries}

## Non-Functional Requirements

- **Performance**: {latency, throughput, resource constraints}
- **Security**: {authentication, authorization, data protection}
- **Compatibility**: {Python version, OS, browser support}
- **Other**: {any additional constraints}

## Open Questions

{Anything unresolved — these must be answered before Phase 1}

1. {Question} — {who can answer it}
2. ...
```

---

## RFC

Write to: `.dev-team-artifacts/{team-name}/rfcs/{number}-{topic}.md`

Number RFCs sequentially: 001, 002, 003...

```markdown
# RFC-{number}: {Title}

| Field | Value |
|-------|-------|
| **Status** | Draft / In Review / Approved / Superseded |
| **Author** | {agent name} |
| **Reviewers** | {agent names} |
| **Created** | {date} |
| **Updated** | {date} |

## Problem Statement

{What problem does this RFC address? Why can't we just write a ticket and go?}

## Proposed Solution

{Detailed technical approach}

### Design

{Architecture, data flow, key components}

### Implementation Steps

1. {Step 1}
2. {Step 2}
3. ...

## Alternatives Considered

### Alternative A: {Name}
{Description, pros, cons, why rejected}

### Alternative B: {Name}
{Description, pros, cons, why rejected}

## Risk Assessment

| Risk | Certainty Impact | Mitigation |
|------|-----------------|------------|
| {What could go wrong} | {How it affects certainty %} | {What we do about it} |

**Current certainty**: {N}%
**What would raise it**: {specific action — POC, research, consultation}
**Residual risks after mitigation**: {what remains uncertain}

## Required Tests

Every code path in this RFC MUST have a corresponding test. List them here. QA verifies this section during Phase 1 review.

| Code Path | Test Type | Test Description | Status |
|-----------|-----------|-----------------|--------|
| {function/method/path} | Unit / Integration | {What the test verifies} | Pending |

**Unit tests**: Required for all new functions, helpers, and logic branches.
**Integration tests**: Required when changes touch server endpoints, database operations, or cross-service communication.

## POC Results

{If a POC was conducted, summarize results here}

- **Question the POC answered**: {what was uncertain}
- **Approach**: {what was built/tested}
- **Result**: {what was learned}
- **Conclusion**: {does this validate or invalidate the approach?}
- **Code/artifacts**: {link to `.dev-team-artifacts/{team-name}/pocs/{number}-{topic}/`}

## Decision

{Final decision and rationale. Updated after review is complete.}

## Review Comments

### {Reviewer name} — {date}
{Feedback, certainty assessment, approval/rejection with rationale}
```

---

## Task / Ticket

Created via TaskCreate. Use this format for the subject and description fields.

**Subject format**: `[{workstream-name}] {imperative verb} {what}`

Examples:
- `[auth] Implement JWT token validation middleware`
- `[data-pipeline] Add retry logic to S3 upload`
- `[shared] Update pyproject.toml with new dependencies`

**Description format**:
```
Context: {Brief context — what this ticket is part of and why it matters}

Acceptance Criteria:
- {Specific, testable criterion 1}
- {Specific, testable criterion 2}

Dependencies:
- Blocked by: {ticket IDs or descriptions, if any}
- Blocks: {ticket IDs or descriptions, if any}

Definition of Ready:
- [ ] Dependencies resolved (all "Blocked by" tasks completed)
- [ ] RFC approved at ≥95% certainty (if applicable; write "N/A" if no RFC)
- [ ] Acceptance criteria are specific and testable

(Dev MUST NOT claim this task until all boxes are checked)

Definition of Done:
- [ ] Code complete — all acceptance criteria addressed
- [ ] Tests written and passing for every new code path
- [ ] Peer review completed (reviewer at ≥95% certainty)
- [ ] Testing specialist signed off on test quality
- [ ] QA confirmed GO

(Team lead verifies ALL boxes before marking task completed)

Related RFC: {RFC number, if this ticket emerged from an RFC}

Certainty: {N}% — {what's uncertain, if anything}

Workstream: {workstream-name}
```

---

## ADR

Write to: `.dev-team-artifacts/{team-name}/adrs/{number}-{topic}.md`

Number ADRs sequentially: 001, 002, 003...

```markdown
# ADR-{number}: {Title}

| Field | Value |
|-------|-------|
| **Status** | Accepted / Superseded by ADR-{N} |
| **Date** | {date} |
| **Deciders** | {agent names who made or influenced the decision} |

## Context

{What is the issue that motivated this decision? What forces are at play — technical constraints, requirements, trade-offs, risks?}

## Decision

{What was decided. State it as a declarative sentence: "We will use X" / "The system will Y".}

## Consequences

### Positive
- {benefit 1}
- {benefit 2}

### Negative
- {trade-off 1}
- {trade-off 2}

### Risks
- {residual risk, if any}

## Alternatives Considered

### {Alternative A}
{Description. Why it was rejected — what made the chosen approach better.}

### {Alternative B}
{Description. Why it was rejected.}

## Source Artifacts
- {RFC-001, POC-002, research note, etc. — what artifacts informed this decision}
```

---

## Final Report HTML

Write to: `.dev-team-artifacts/{team-name}/reports/final-report.html`

The report must be **self-contained** — inline CSS, no external dependencies, no CDN links. It should render correctly when opened directly in a browser.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dev Team Report: {Project Title}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 960px; margin: 0 auto; padding: 2rem; }
  h1 { font-size: 2rem; margin-bottom: 0.5rem; border-bottom: 3px solid #2563eb; padding-bottom: 0.5rem; }
  h2 { font-size: 1.5rem; margin-top: 2.5rem; margin-bottom: 1rem; color: #1e40af; }
  h3 { font-size: 1.2rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }
  p, li { margin-bottom: 0.5rem; }
  table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
  th, td { padding: 0.5rem 0.75rem; border: 1px solid #d1d5db; text-align: left; }
  th { background: #f3f4f6; font-weight: 600; }
  tr:nth-child(even) { background: #f9fafb; }
  code { background: #f3f4f6; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.9em; }
  pre { background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 6px; overflow-x: auto; margin: 1rem 0; }
  pre code { background: none; color: inherit; padding: 0; }
  .status-met { color: #16a34a; font-weight: 600; }
  .status-unmet { color: #dc2626; font-weight: 600; }
  .status-partial { color: #d97706; font-weight: 600; }
  .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }
  .card h3 { margin-top: 0; }
  .summary-box { background: #eff6ff; border-left: 4px solid #2563eb; padding: 1rem 1.5rem; margin: 1.5rem 0; }
  details { margin: 0.5rem 0; }
  summary { cursor: pointer; font-weight: 600; padding: 0.5rem; background: #f3f4f6; border-radius: 4px; }
  details[open] summary { margin-bottom: 0.5rem; }
  .artifact-content { padding: 1rem; border: 1px solid #e5e7eb; border-radius: 4px; margin-top: 0.5rem; }
</style>
</head>
<body>

<h1>Dev Team Report: {Project Title}</h1>
<p><em>Generated: {date}</em></p>

<div class="summary-box">
<h3>Executive Summary</h3>
<p>{What was built, why, key outcomes, acceptance criteria status (X/Y met)}</p>
</div>

<h2>Requirements Status</h2>
<!-- Table of acceptance criteria with met/unmet status -->
<table>
<thead><tr><th>ID</th><th>Criterion</th><th>Verification</th><th>Status</th></tr></thead>
<tbody>
<tr><td>AC-001</td><td>{criterion}</td><td>{method}</td><td class="status-met">Met</td></tr>
<!-- ... -->
</tbody>
</table>

<h2>Workstream: {name}</h2>
<!-- Repeat for each workstream -->
<div class="card">
<h3>{Workstream Name}</h3>
<p>{Summary of what was implemented}</p>
<h4>Tickets Completed</h4>
<ul>
<li>{ticket subject} — {brief outcome}</li>
</ul>
<h4>Key Decisions</h4>
<p>{Notable design choices made in this workstream}</p>
</div>

<h2>RFCs</h2>
<!-- Embed full text of each RFC -->
<details>
<summary>RFC-001: {Title} — {Status}</summary>
<div class="artifact-content">
{Full RFC content rendered as HTML}
</div>
</details>

<h2>Proofs of Concept</h2>
<!-- Embed POC results -->
<details>
<summary>POC-001: {Title}</summary>
<div class="artifact-content">
<p><strong>Question</strong>: {what the POC answered}</p>
<p><strong>Result</strong>: {outcome}</p>
<pre><code>{key code snippets}</code></pre>
</div>
</details>

<h2>Research</h2>
<!-- Embed research notes -->
<details>
<summary>{Research Topic}</summary>
<div class="artifact-content">
{Full research content}
</div>
</details>

<h2>Architecture Decision Records</h2>
<!-- Embed full text of each ADR -->
<details>
<summary>ADR-001: {Title} — {Status}</summary>
<div class="artifact-content">
{Full ADR content rendered as HTML}
</div>
</details>

<h2>Design Decisions</h2>
<!-- Key decisions with rationale (for decisions not covered by ADRs) -->
<div class="card">
<h3>{Decision}</h3>
<p><strong>Context</strong>: {why this decision was needed}</p>
<p><strong>Decision</strong>: {what was decided}</p>
<p><strong>Alternatives</strong>: {what was considered and rejected}</p>
<p><strong>Rationale</strong>: {why this option won}</p>
</div>

<h2>Test Results</h2>
<p>{Summary of test coverage, pass rates, notable findings}</p>

</body>
</html>
```

Adapt this skeleton as needed — add sections, repeat cards, embed figures as inline SVG or base64 `<img>` tags. The key requirement is that ALL artifacts are included in the report, either as embedded content or within collapsible `<details>` sections.

