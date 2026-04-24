---
name: pr-review-cycle
description: Close the loop on a PR that has been reviewed by an automated reviewer (Hermes Code Review, Gemini, CodeQL, Snyk, Dependabot, or any GitHub Actions bot that posts PR review comments with severity-tagged findings). Fetches the review, parses the findings, asks which ones to patch, generates the fixes, commits in logical chunks with conventional commit messages, pushes to the PR branch, and verifies the re-run CI. Use whenever the user says "address the PR review", "patch the findings", "respond to the Hermes/Gemini/CI review", "update PR X based on the review", "run the PR review cycle", or anything about triaging and applying an automated code-review bot's feedback. Also trigger this if the user opens a PR and the next step is clearly "now deal with the review comments".
---

# PR Review Cycle

Triage and resolve automated code-review findings on an open PR, commit-by-commit, until the reviewer is satisfied.

## When this skill fires

Use it when:
- A PR is open and an automated reviewer (Hermes, Gemini, CodeQL, Snyk, SonarCloud, etc.) has posted severity-tagged findings.
- The user wants you to patch those findings (all of them, or a subset by severity) and update the PR.
- The user says any trigger phrase in the description, or describes the workflow without naming it.

Do NOT fire this skill for:
- Human code-review comments on a PR — those are conversational; resolve them in-thread.
- Opening the PR itself — use `gh pr create` directly.
- Non-PR code review (e.g. local `just prek` output) — just fix inline.

## Why this exists

Automated review bots post a lot of signal in a frustratingly ad-hoc format: free-form markdown, different severity conventions per vendor, mixing real bugs with style nits with "did you consider…" suggestions. Humans skim these in a slack window. Claude can parse them rigorously, triage against the user's priorities, apply fixes atomically, and close the loop. That's what this skill does.

The guiding principle: **the PR branch is shared state.** Pushing updates changes what reviewers see. So this skill is careful about confirmation, atomic commits, and never rewriting history unless the user explicitly asks.

## Workflow

The cycle has six phases. Each one is a checkpoint where you confirm before advancing.

### Phase 1: Identify the PR and fetch the review

Ask (or infer) the PR number. Then fetch the review data as JSON — don't scrape the web UI:

```bash
gh pr view <PR> --json reviews,comments,statusCheckRollup,latestReviews --repo <owner/repo>
```

The `--repo` flag is belt-and-suspenders — `gh` usually infers it from the local repo, but if the user's session is in a worktree on a different remote, inference can mislead. Pass it explicitly if uncertain.

From the JSON:
- `reviews[]` — review submissions (state, author, body, submittedAt).
- `latestReviews[]` — the latest review per author, which is usually what you want.
- `comments[]` — inline or general PR comments.
- `statusCheckRollup[]` — CI status (look for the review workflow's success/failure).

**Filter to automated reviewers**: look for `author.login` values ending in `[bot]` or equal to `github-actions`, or whose `authorAssociation` is `NONE`. Human reviewers need different handling.

Surface to the user: who reviewed (bot name), submitted at what time, state (`COMMENTED` / `CHANGES_REQUESTED` / `APPROVED`), and whether the review workflow check passed.

### Phase 2: Parse the findings

Review bodies are free-form markdown. Vendors vary:

- **Hermes**: `**High — <file>::<function>**` headers followed by code blocks and a prose explanation. Summary table at the end.
- **Gemini**: similar but uses `### High`, `### Medium`, `### Low` section headers.
- **CodeQL**: usually a list with `**🔴 High**` / `**🟡 Medium**` inline markers.
- **Copilot review**: inline comment anchors; you get severity via the `state` field on the comment, not keywords.

Parse robustly — don't hardcode one format. Look for any of these markers in the body (case-insensitive):
- `**High`, `**Medium`, `**Low`, `**Critical`, `**Info`
- `### High`, `### Medium`, `### Low`
- `🔴`, `🟡`, `🟢` emoji
- HTML-ish `<severity>High</severity>` tags (rare but some tools use them)

For each finding extract: severity, file path (and line/function if present), a one-line issue summary. The bot's full explanation is your reference when generating the fix — but for the triage table, only the one-liner is user-facing.

Present to the user as a table:

```
| # | Sev | File:Location | Issue |
|---|-----|---------------|-------|
| 1 | HIGH | tools.py::handle_add_assets | Filename not sanitized (path-traversal risk) |
| 2 | HIGH | tools.py::handle_add_assets | Duplicate filenames silently overwrite |
| 3 | MED  | tools.py::handle_get_memory_units | N serial API calls, no batch try |
...
```

If the bot left no severity markers at all (e.g., a plain prose review), present the findings as a numbered list and flag that severity is not set; ask the user which ones they consider important.

### Phase 3: Triage with the user

Ask a focused question — use `AskUserQuestion` if available with up to 4 options:

1. **Patch everything** — address all findings.
2. **Patch HIGHs only** — ship critical fixes, defer the rest as follow-up issues.
3. **Pick specifically** — user names which numbers to fix.
4. **Defer everything** — add a PR comment noting the findings are tracked elsewhere; merge as-is.

For each finding the user accepts, also capture any rejection rationale: sometimes a finding reflects a design decision the user is comfortable with (e.g., "base64 input deliberately diverges from MCP — documented as such"). Record these as rejection-with-rationale entries and respond to them with a PR comment (Phase 6) rather than a code change.

### Phase 4: Generate fixes

For each accepted finding, produce a fix. Group logically — commits should reflect intent, not arbitrary batches. Good patterns:

- **One commit per severity tier**: `fix(scope): address HIGH-severity review findings` + `refactor(scope): address MEDIUM findings` + `chore(scope): address LOW findings`. Keeps the PR history readable.
- **One commit per finding when the fix is substantive** — e.g., a security patch that deserves its own blame-trail.
- **One commit per file when fixes touch many small spots in one file** — clusters easier to review.

Use conventional commits. Scope = the package/module most affected (e.g., `hermes-plugin`, `auth`, `api`).

**Docs-only resolutions**: sometimes a finding's fix is "the current behavior is intentional, document it". Accept that as a valid resolution type — add a code comment or docstring, commit with `docs(scope): document <behavior> (addresses review finding)`. Don't over-engineer if the underlying concern is already handled.

**Branch / worktree discipline**:
- If the PR branch is checked out in multiple worktrees, git will refuse a second checkout. Work in the worktree where the branch is already checked out, or create a fresh worktree for the purpose.
- Use `git -C /path/to/worktree ...` and absolute paths for file edits if your session's cwd is fixed to a different worktree. This avoids branch-collision errors and cross-worktree race conditions.
- Set up a dedicated venv in the worktree if the project uses `uv` or a similar tool whose shared cache can resolve imports from sibling worktrees. See `references/worktree-hygiene.md` if you hit weird import issues during tests.

### Phase 5: Test and push

Run the project's test command before committing. Minimum: the test file(s) relevant to the changed code. Better: the full test suite for the changed package.

If the project has a lint/format/type-check gate (`just prek`, `npm run lint`, `cargo fmt`, `pnpm check`), run it too. Many review bots flag style issues that the linter would have caught; running prek first avoids a pointless second round of findings.

Commit with the conventional message. Then confirm with the user before pushing — push updates the PR and notifies reviewers. Example confirmation:

> Ready to push 3 commits to `branch-name` on PR #38. This will update the PR and re-trigger the review workflow. Go?

On confirmation: `git -C <worktree> push origin <branch>`. Don't use `--force` or `--force-with-lease` unless the user explicitly asked.

### Phase 6: Verify re-review

After push, the CI reviewer usually re-queues automatically. Wait ~30-60 seconds then poll:

```bash
gh pr view <PR> --json statusCheckRollup,latestReviews --repo <owner/repo>
```

Look for:
- The review workflow (`Hermes Code Review`, `Gemini Review`, etc.) check status: `COMPLETED` / `SUCCESS`.
- A new review submission timestamped after your push.

If the new review is clean (no new High/Medium findings), report success. If new findings appear, loop back to Phase 2 — this is normal for deep codebases; 2-3 iterations is common.

For **rejected findings** (design decisions you deliberately didn't fix), post a PR comment explaining the rationale so the human reviewer sees it:

```bash
gh pr comment <PR> --body "<explanation>" --repo <owner/repo>
```

Exit the cycle when:
- The user says they're done.
- No High/Medium findings remain.
- A rework cycle limit is hit (default 3 — escalate to the user if still iterating at that point).

## Safety rules

These apply across the whole skill — do not break them:

- **Never force-push** (`--force`, `--force-with-lease`) unless the user has explicitly asked for it in this conversation. Force-pushing to a PR overwrites work that others may have pulled.
- **Never close or re-open the PR** without explicit user instruction.
- **Never merge the PR** from this skill — merges are always a separate, explicit user decision.
- **Never modify the PR body/title** unless the user asks. Your commits speak for themselves.
- **Never skip tests** to unblock the cycle. If tests fail, fix the cause or stop and report; don't `--no-verify` past a hook.
- **Never commit secrets** — the automated reviewer sometimes flags `.env` or credential-like patterns; if the fix involves adding a secret to the repo, stop and escalate.

## Useful `gh` recipes

Grouped in `references/gh-recipes.md` if you need them:
- Pagination on repos with lots of comments
- Reading inline review comments anchored to specific lines
- Posting PR comments that @mention the reviewer bot (useful for "I addressed this" acknowledgements)
- Querying the specific `check-run` for the review workflow to confirm its re-queue succeeded

## Scratch template

A starting-point mental checklist when the skill fires:

```
[ ] PR number identified: #___
[ ] Reviewer identified: _______
[ ] Review fetched (SHA of commit reviewed: _______)
[ ] Findings parsed (count: __ H, __ M, __ L)
[ ] User triaged — accepted: __, rejected: __, deferred: __
[ ] Fixes generated for accepted findings
[ ] Tests run green (suite: _______)
[ ] Lint/prek green
[ ] Commits created (count: ___, messages reviewed)
[ ] User confirmed push
[ ] Pushed to <branch>
[ ] Re-review triggered and passed (new review at _______)
[ ] PR comment(s) posted for rejected findings (count: ___)
[ ] Cycle complete / iteration count: ___
```

Keep the scratch note in-thread so the user can see where you are without asking.
