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
name, and reads back the rules GitHub enforces. Do not hand-write the JSON or call
`gh api .../rulesets` yourself; your job is choosing the inputs.

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
| Stale approval dismissal | `--dismiss-stale` | off | approvals should not survive new pushes |
| Code owner review | `--code-owners` | off | the repo has a `CODEOWNERS` file that is maintained |

**Finding check names.** A required check must match a check run name GitHub has
already seen, character for character. Read them from a recent pull request or the
default branch head; never guess them from workflow file names:

```bash
SHA=$(gh api repos/OWNER/NAME/commits/DEFAULT_BRANCH --jq .sha)
gh api "repos/OWNER/NAME/commits/$SHA/check-runs?per_page=100" --jq '.check_runs[].name' | sort -u
```

Require only checks that run on **every** pull request. A check that is path-filtered,
skipped, or only runs on `push` will never report on some pull requests, and those pull
requests can then never merge. If all checks come from GitHub Actions, add
`--actions-only` so another app cannot satisfy a check by reusing its name.

### 3. Dry run, show the plan, get a yes

```bash
python3 scripts/apply_ruleset.py --repo OWNER/NAME --approvals 1 \
  --check "pre-commit" --check "test (3.12)" --dry-run
```

The dry run prints whether it will create or update, any warnings, and the body. Show
the user the settings in plain words (not the JSON) plus every warning, and wait for
approval. Applying a ruleset changes how everyone with push access works, so do not
skip this even when the request sounded explicit.

### 4. Apply and report

Run the same command without `--dry-run`. Report the ruleset id, its URL, and the
enforced rule types the script printed. If the read-back is missing a rule you set, say
so; do not report success.

## Gotchas

- **Solo maintainers lock themselves out.** With `--approvals 1` and no bypass, nobody
  can approve the only maintainer's pull requests (GitHub forbids approving your own).
  The script warns when it sees a single collaborator; offer `--approvals 0` (pull
  requests still required) or `--admin-bypass pull_request`.
- **Empty repositories.** Apply after the first commit exists on the default branch.
  Once the pull-request rule is active, a direct push of an initial commit is refused.
- **Matrix job names.** Actions reports matrix jobs as `test (3.12)`, not `test`.
  Requiring `test` waits forever.
- **Plan limits.** Rulesets on private repos need GitHub Pro (personal) or Team/
  Enterprise (orgs). On Free, GitHub answers 403 "Upgrade to GitHub Pro or make this
  repository public". Report that; do not fall back to the legacy API, which has the
  same limit.
- **Unknown parameter errors.** GitHub adds and renames ruleset parameters. If the API
  rejects a key as invalid, report the exact message to the user rather than editing
  the request by hand; the script needs fixing.
- **`evaluate` mode** only exists on GitHub Enterprise. Elsewhere it is rejected.
- **Bots and deploy keys.** Release automation that pushes to the default branch (version
  bumps, changelog commits) is blocked by the pull-request rule. Ask whether such a
  workflow exists (`grep -rl "git push" .github/workflows`) before applying, and if so
  tell the user it needs a bypass actor added in the repository settings.
