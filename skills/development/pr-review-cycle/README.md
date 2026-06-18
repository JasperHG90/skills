# /pr-review-cycle

A Claude Code skill that closes the loop on a PR reviewed by an automated reviewer (Hermes Code Review, Gemini, CodeQL, Snyk, Dependabot, or any GitHub Actions bot that posts severity-tagged findings). It fetches the review, parses the findings, triages with you, generates fixes, commits in logical chunks with conventional messages, pushes, and verifies the re-run CI.

## Usage

```
/pr-review-cycle
```

Triggers on "address the PR review", "patch the findings", "respond to the CI review", "update PR X based on the review", etc. **Not** for human review comments (resolve those in-thread), opening the PR itself, or non-PR local review.

## The six phases

Each phase is a checkpoint where the skill confirms before advancing:

1. **Identify the PR and fetch the review** — pulls review data as JSON via `gh`, filters to automated reviewers.
2. **Parse the findings** — robustly handles each vendor's free-form markdown; presents a severity/file/issue triage table.
3. **Triage with you** — patch everything / HIGHs only / pick specifically / defer; captures rejection rationale for design decisions.
4. **Generate fixes** — grouped into logical conventional commits (per severity tier, per finding, or per file).
5. **Test and push** — runs the project's tests and lint gate, then confirms before pushing (push notifies reviewers).
6. **Verify re-review** — polls CI for the re-queued review; loops back if new findings appear (2–3 iterations is normal); posts PR comments explaining rejected findings.

## Safety rules

The PR branch is shared state. The skill never force-pushes, closes/reopens/merges the PR, modifies the PR body/title, skips tests, or commits secrets — unless you explicitly ask. Default rework-cycle limit is 3, then it escalates to you.
