# /github-branch-protection

A skill that protects a GitHub repository's default branch with a repository ruleset:
no deletion, no force-push, pull requests required, and optionally required approvals,
CI status checks, linear history and admin bypass. It works on any repository you
administer and is safe to re-run: the ruleset is updated in place by name.

## What it does

1. **Inspects the repo** for existing rulesets (repo and org level) and legacy branch
   protection.
2. **Agrees the settings with you**, starting from sensible defaults (1 approval,
   resolved review threads, no bypass) and reading real check names from recent CI runs.
3. **Dry-runs** the change and shows you the plan and any warnings: an empty repo, a solo
   maintainer who would be locked out, a private repo on a Free plan.
4. **Applies** the ruleset and reads back the rules GitHub now enforces on the default
   branch.

## Prerequisites

- [`gh`](https://cli.github.com) authenticated (`gh auth status`) as a user with admin
  rights on the target repository.
- Python 3.10+ (the script uses only the standard library).
- Public repository, or a private one on GitHub Pro / Team / Enterprise.

## Usage

```
/github-branch-protection
```

or ask in plain words: "protect main on octo-org/api and require the test job to pass".

The script can also run on its own:

```bash
# See what would happen
python3 scripts/apply_ruleset.py --repo octo-org/api --check "test (3.12)" --dry-run

# Solo maintainer: require PRs, no review
python3 scripts/apply_ruleset.py --repo me/tool --approvals 0

# Squash-only team with strict, Actions-reported checks
python3 scripts/apply_ruleset.py --repo octo-org/api --approvals 2 \
  --check lint --check "test (3.12)" --actions-only --strict \
  --merge-methods squash --linear-history
```

Run `python3 scripts/apply_ruleset.py --help` for every flag.

## Testing

`evals/evals.json` holds test prompts. Run them against a throwaway repository you own;
each eval applies a real ruleset. Remove it afterwards in the repository's
**Settings → Rules → Rulesets**, or with
`gh api -X DELETE repos/OWNER/NAME/rulesets/ID`.
