---
name: github-branch-protection
description: Set up or update branch protection on a GitHub repository with a repository ruleset, through the gh CLI and the rulesets API. Blocks deletion and force-push on the default branch, requires pull requests with a chosen number of approvals, and optionally requires CI status checks, linear history and admin bypass. Re-running updates the same ruleset instead of stacking a second one. Use whenever the user says "protect main", "branch protection", "require PRs", "require reviews", "require CI to pass before merge", "block force pushes", "set up rulesets", or is hardening a new or existing GitHub repo. NOT for organization-wide rulesets, tag protection, GitLab or Bitbucket, or for changing GitHub Actions workflows themselves.
compatibility: gh CLI authenticated with admin rights on the target repository; Python 3.10+ (stdlib only). Private repositories on personal accounts need GitHub Pro.
metadata:
  author: Jasper Ginn
  version: 1.0.0
---

# GitHub Branch Protection

Protect a repository's default branch with a **repository ruleset**. Rulesets replace
the legacy branch-protection API (`repos/{repo}/branches/{branch}/protection`): several
can stack, they are readable by anyone with read access, and they can target the default
branch by alias (`~DEFAULT_BRANCH`) so a branch rename does not leave the repo unprotected.

`scripts/apply_ruleset.py` builds the request body, creates or updates the ruleset by
name, refuses required checks GitHub has never reported, keeps bypass actors and rules
it does not manage when updating, and fails if the read-back is missing a rule. Do not
hand-write the JSON or call `gh api .../rulesets` yourself; your job is choosing the
inputs.

**Do NOT use this skill** to manage organization-level rulesets
(`orgs/{org}/rulesets`), protect tags, edit legacy branch protection that someone
deliberately keeps, or fix CI workflows. If the repo already has legacy branch
protection, say so and ask before adding a ruleset on top; both apply, and the stricter
rule wins.

## End state

A ruleset (default name `default-branch-protection`) is active on the default branch,
the user has seen and approved its settings before it was applied, and the script's
read-back lists the expected rule types. Nothing else in the repository changed.

## Workflow

- [ ] 1. Identify the repo and check the current state
- [ ] 2. Choose the settings with the user
- [ ] 3. Dry run, show the plan, get a yes
- [ ] 4. Apply and report

### 1. Identify the repo and check the current state

Resolve `OWNER/NAME` from the user's message, or from the current checkout
(`gh repo view --json nameWithOwner -q .nameWithOwner`). Then look at what exists:

```bash
gh api "repos/OWNER/NAME/rulesets?includes_parents=true" \
  --jq '.[] | {id, name, source_type, enforcement}'
gh api repos/OWNER/NAME/branches/DEFAULT_BRANCH/protection 2>/dev/null | head -c 300
```

A ruleset with `source_type: Organization` comes from the org; leave it alone and tell
the user it already applies. A 404 on the second call means no legacy protection.

### 2. Choose the settings with the user

Propose these defaults and ask only about what the defaults do not settle:

| Setting | Flag | Default | Change it when |
|---|---|---|---|
| Required approvals | `--approvals N` | `1` | solo maintainer → `0`; regulated code → `2` |
| Required checks | `--check NAME` (repeat) | none | the repo has CI that runs on pull requests |
| Up to date before merge | `--strict` | off | merge queues are absent and main breaks from stale merges |
| Merge methods | `--merge-methods ...` | all three | the team has a convention (look at recent merge commits) |
| Linear history | `--linear-history` | off | the team squashes or rebases only |
| Admin bypass | `--admin-bypass` | `none` | solo maintainer who wants review rules but must still merge |
| App bypass | `--bypass-app APP_ID` | none | a release bot pushes version bumps to the default branch |
| Stale approval dismissal | `--dismiss-stale` | off | approvals should not survive new pushes |
| Code owner review | `--code-owners` | off | the repo has a `CODEOWNERS` file that is maintained |

**Finding check names.** A required check must match, character for character, a name
GitHub has reported. For Actions that is the job's `name:`, not its id, so a job
`pre-commit:` named `Run pre-commit checks` reports as `Run pre-commit checks`. Never
guess from workflow files; list what GitHub has actually seen on recent pull requests
and the default branch:

```bash
python3 scripts/apply_ruleset.py --repo OWNER/NAME --list-checks
```

From that list, require only checks that run on **every** pull request. A check that is
path-filtered, skipped, or only runs on `push` will never report on some pull requests,
and those pull requests can then never merge; when in doubt, read the workflow's `on:`
and `paths:` triggers. If every chosen check shows app `15368` (GitHub Actions), add
`--actions-only` so another app cannot satisfy a check by reusing its name. The script
refuses a `--check` it has never seen; pass `--allow-unseen-check` only when the
workflow that produces it is being added in the same change, and tell the user pull
requests are blocked until it reports.

### 3. Dry run, show the plan, get a yes

```bash
python3 scripts/apply_ruleset.py --repo OWNER/NAME --approvals 1 \
  --check "Run pre-commit checks" --check "Run tests (3.12)" --dry-run
```

The dry run prints whether it will create or update, any warnings, the body, and on an
update which existing bypass actors and rules it keeps or removes. Show the user the
settings in plain words (not the JSON), every warning and every removal, and wait for
approval. Applying a ruleset changes how everyone with push access works, so do not
skip this even when the request sounded explicit.

### 4. Apply and report

Run the same command without `--dry-run`. Report the ruleset id, its URL, and the
enforced rule types the script printed. The script exits 1 when GitHub does not enforce
a rule it just set; report that as a failure with the script's message.

## Gotchas

- **Solo maintainers lock themselves out.** With `--approvals 1` and no bypass, nobody
  can approve the only maintainer's pull requests (GitHub forbids approving your own).
  The script warns when it sees a single collaborator; offer `--approvals 0` (pull
  requests still required) or `--admin-bypass pull_request`.
- **Empty repositories.** Apply after the first commit exists on the default branch.
  Once the pull-request rule is active, a direct push of an initial commit is refused.
- **Matrix job names.** Actions reports matrix jobs with their matrix values, e.g.
  `Run tests (3.12)`, not `Run tests`. `--list-checks` shows the real form.
- **Plan limits.** Rulesets on private repos need GitHub Pro (personal) or Team/
  Enterprise (orgs). On Free, GitHub refuses with a 403 that asks you to upgrade or make
  the repository public. Report that; do not fall back to the legacy API, which has the
  same limit.
- **Updates keep what the script does not manage.** Bypass actors other than the admin
  role, and rule types other than the five the script writes (for example
  `required_signatures` added in the UI), survive a re-run. The admin bypass and the five
  managed rules follow the flags, so re-running without `--admin-bypass` removes an
  existing admin bypass; the dry run says so.
- **Unknown parameter errors.** GitHub adds and renames ruleset parameters. If the API
  rejects a key as invalid, report the exact message to the user rather than editing
  the request by hand; the script needs fixing.
- **`evaluate` mode** only exists on GitHub Enterprise. Elsewhere it is rejected.
- **Bots and deploy keys.** Release automation that pushes to the default branch (version
  bumps, changelog commits) is blocked by the pull-request rule. Ask whether such a
  workflow exists (`grep -rl "git push" .github/workflows`) before applying. If it pushes
  as a GitHub App, add `--bypass-app APP_ID` (`gh api /apps/<app-slug> --jq .id`). If it
  pushes with `GITHUB_TOKEN` or a personal token, the app route does not cover it; tell
  the user and let them choose between a deploy key bypass in the UI or a PR-based
  release flow.
