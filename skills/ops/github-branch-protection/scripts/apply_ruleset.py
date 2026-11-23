#!/usr/bin/env python3
"""apply_ruleset.py — create or update a branch-protection ruleset on a GitHub repo.

Self-contained, pure stdlib. Shells out to the `gh` CLI for every API call, so it
uses whatever account `gh auth status` reports and needs admin rights on the repo.

The script owns the invariants: the request body, create-vs-update by ruleset
name (so a re-run never stacks a second ruleset), and the read-back of the rules
GitHub actually enforces on the default branch. The agent owns the judgment:
which status checks to require, how many approvals, and who may bypass.

Exit codes: 0 applied (or dry run printed), 1 GitHub or gh refused, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

# Repository role ids GitHub uses for bypass actors (RepositoryRole actor type).
ADMIN_ROLE_ID = 5
# App id of GitHub Actions; pins a required check to checks reported by Actions.
GITHUB_ACTIONS_APP_ID = 15368
MERGE_METHODS = ("merge", "squash", "rebase")


class GhError(Exception):
    """A `gh` invocation failed; the message is gh's own stderr."""


def gh_api(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    cmd = ["gh", "api", "-X", method, path]
    if body is not None:
        cmd += ["--input", "-"]
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(body) if body is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise GhError(
            "gh is not installed or not on PATH; install it from https://cli.github.com"
        ) from e
    if proc.returncode != 0:
        raise GhError((proc.stderr or proc.stdout).strip())
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def current_repo() -> str:
    try:
        proc = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise GhError("gh is not installed or not on PATH") from e
    if proc.returncode != 0 or not proc.stdout.strip():
        raise GhError(
            "no --repo given and the current directory is not a GitHub checkout; "
            "pass --repo OWNER/NAME"
        )
    return proc.stdout.strip()


def build_body(args: argparse.Namespace) -> dict[str, Any]:
    pull_request: dict[str, Any] = {
        "type": "pull_request",
        "parameters": {
            "required_approving_review_count": args.approvals,
            "dismiss_stale_reviews_on_push": args.dismiss_stale,
            "require_code_owner_review": args.code_owners,
            "require_last_push_approval": False,
            "required_review_thread_resolution": args.resolve_threads,
            "allowed_merge_methods": args.merge_methods,
        },
    }
    rules: list[dict[str, Any]] = [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        pull_request,
    ]
    if args.linear_history:
        rules.append({"type": "required_linear_history"})
    if args.check:
        checks = []
        for name in args.check:
            entry: dict[str, Any] = {"context": name}
            if args.actions_only:
                entry["integration_id"] = GITHUB_ACTIONS_APP_ID
            checks.append(entry)
        rules.append(
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": args.strict,
                    "do_not_enforce_on_create": False,
                    "required_status_checks": checks,
                },
            }
        )
    bypass = []
    if args.admin_bypass != "none":
        bypass.append(
            {
                "actor_id": ADMIN_ROLE_ID,
                "actor_type": "RepositoryRole",
                "bypass_mode": args.admin_bypass,
            }
        )
    return {
        "name": args.name,
        "target": "branch",
        "enforcement": args.enforcement,
        "conditions": {"ref_name": {"include": [args.branch], "exclude": []}},
        "bypass_actors": bypass,
        "rules": rules,
    }


def find_ruleset(repo: str, name: str) -> int | None:
    rulesets = gh_api(f"repos/{repo}/rulesets?includes_parents=false") or []
    for rs in rulesets:
        if rs.get("name") == name and rs.get("target", "branch") == "branch":
            return int(rs["id"])
    return None


def warnings_for(
    repo: str, info: dict[str, Any], args: argparse.Namespace
) -> list[str]:
    out = []
    try:
        branches = gh_api(f"repos/{repo}/branches?per_page=1") or []
    except GhError:
        branches = []
    if not branches:
        out.append(
            "the repository has no branches yet; push a first commit before applying, "
            "or that first push is blocked by the pull-request rule"
        )
    if args.approvals >= 1 and args.admin_bypass == "none":
        try:
            collaborators = gh_api(f"repos/{repo}/collaborators?per_page=2") or []
        except GhError:
            collaborators = []
        if len(collaborators) == 1:
            out.append(
                f"only one collaborator can push here, and {args.approvals} approval(s) "
                "are required with no bypass: nobody can approve that person's pull "
                "requests. Use --approvals 0 or --admin-bypass pull_request"
            )
    if info.get("private") and info.get("owner", {}).get("type") == "User":
        out.append(
            "private repository on a personal account: rulesets need GitHub Pro; "
            "on the Free plan GitHub answers 403 'Upgrade to GitHub Pro'"
        )
    return out


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="apply_ruleset.py",
        description=(
            "Create or update a branch ruleset that blocks deletion and force-push "
            "and requires pull requests on the default branch. Re-running updates "
            "the ruleset with the same --name in place."
        ),
    )
    p.add_argument(
        "--repo",
        metavar="OWNER/NAME",
        help="Target repository, e.g. octo-org/api. Default: the repo of the "
        "current directory, as `gh repo view` reports it.",
    )
    p.add_argument(
        "--name",
        default="default-branch-protection",
        help="Ruleset name; an existing ruleset with this name is updated "
        "instead of a second one created. Default: %(default)s.",
    )
    p.add_argument(
        "--branch",
        default="~DEFAULT_BRANCH",
        help="Ref pattern to protect: ~DEFAULT_BRANCH, ~ALL, or a full ref like "
        "refs/heads/release/*. Default: %(default)s.",
    )
    p.add_argument(
        "--approvals",
        type=int,
        default=1,
        choices=range(11),
        metavar="N",
        help="Approving reviews needed to merge, 0-10. 0 still forces the pull "
        "request flow, just without review. Default: %(default)s.",
    )
    p.add_argument(
        "--check",
        action="append",
        metavar="NAME",
        help="Required status check, exactly as GitHub shows the check run name "
        "(for Actions, the job name, e.g. 'test (3.12)'). Repeat per check. "
        "Default: none.",
    )
    p.add_argument(
        "--actions-only",
        action="store_true",
        help="Accept the --check results only when GitHub Actions reported them, "
        "so another app cannot satisfy a check by reusing its name.",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Require the branch to be up to date with the base before merging "
        "(only applies with --check).",
    )
    p.add_argument(
        "--merge-methods",
        nargs="+",
        choices=MERGE_METHODS,
        default=list(MERGE_METHODS),
        metavar="METHOD",
        help="Merge methods allowed by the ruleset: merge, squash, rebase. "
        "Default: all three.",
    )
    p.add_argument(
        "--linear-history",
        action="store_true",
        help="Forbid merge commits on the branch. Pair with --merge-methods "
        "squash rebase, or merging becomes impossible.",
    )
    p.add_argument(
        "--dismiss-stale",
        action="store_true",
        help="Dismiss approvals when new commits are pushed to the pull request.",
    )
    p.add_argument(
        "--code-owners",
        action="store_true",
        help="Require review from a CODEOWNERS owner of the changed files.",
    )
    p.add_argument(
        "--no-resolve-threads",
        dest="resolve_threads",
        action="store_false",
        help="Allow merging with unresolved review threads (resolved is required "
        "by default).",
    )
    p.add_argument(
        "--admin-bypass",
        choices=("none", "pull_request", "always"),
        default="none",
        help="Let repository admins bypass: pull_request lets them merge their own "
        "pull requests past the rules, always also lets them push directly. "
        "Default: %(default)s.",
    )
    p.add_argument(
        "--enforcement",
        choices=("active", "evaluate", "disabled"),
        default="active",
        help="active enforces; evaluate only reports (GitHub Enterprise); "
        "disabled stores the ruleset unenforced. Default: %(default)s.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned action and request body; change nothing.",
    )
    args = p.parse_args(argv)
    if args.linear_history and "merge" in args.merge_methods:
        p.error(
            "--linear-history forbids merge commits but --merge-methods allows "
            "'merge'; pass --merge-methods squash rebase"
        )
    if args.strict and not args.check:
        p.error("--strict only applies with at least one --check NAME")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repo = args.repo or current_repo()
        info = gh_api(f"repos/{repo}")
        if not info.get("permissions", {}).get("admin"):
            print(
                f"error: the gh account has no admin rights on {repo}; rulesets need admin",
                file=sys.stderr,
            )
            return 1
        body = build_body(args)
        existing = find_ruleset(repo, args.name)
        action = f"update ruleset {existing}" if existing else "create ruleset"
        for w in warnings_for(repo, info, args):
            print(f"warning: {w}", file=sys.stderr)
        print(f"{repo}: {action} '{args.name}'")
        if args.dry_run:
            print(json.dumps(body, indent=2))
            return 0
        if existing:
            result = gh_api(f"repos/{repo}/rulesets/{existing}", "PUT", body)
        else:
            result = gh_api(f"repos/{repo}/rulesets", "POST", body)
        default_branch = info["default_branch"]
        enforced = gh_api(f"repos/{repo}/rules/branches/{default_branch}") or []
    except GhError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"ruleset id: {result['id']}")
    fallback = f"https://github.com/{repo}/settings/rules/{result['id']}"
    url = result.get("_links", {}).get("html", {}).get("href") or fallback
    print(f"url: {url}")
    types = sorted({r["type"] for r in enforced})
    print(f"rules now enforced on '{default_branch}': {', '.join(types) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
