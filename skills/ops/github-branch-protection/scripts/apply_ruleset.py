#!/usr/bin/env python3
"""apply_ruleset.py — create or update a branch-protection ruleset on a GitHub repo.

Self-contained, pure stdlib. Shells out to the `gh` CLI for every API call, so it
uses whatever account `gh auth status` reports and needs admin rights on the repo.

The script owns the invariants:

- the request body;
- create-vs-update by ruleset name, so a re-run never stacks a second ruleset;
- on update, keeping the bypass actors and rule types it does not manage, so a
  re-run never silently drops what someone added in the GitHub UI;
- refusing required checks GitHub has never reported, which would block every
  pull request forever;
- reading back the rules GitHub enforces and failing when one is missing.

The agent owns the judgment: which checks to require, how many approvals, and
who may bypass.

Exit codes: 0 applied (or dry run / listing printed), 1 GitHub or gh refused or
the read-back is missing a rule, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

# RepositoryRole actor id of the built-in "admin" repository role.
ADMIN_ROLE_ID = 5
# App id of GitHub Actions; pins a required check to checks reported by Actions.
GITHUB_ACTIONS_APP_ID = 15368
MERGE_METHODS = ("merge", "squash", "rebase")
# Rule types this script writes. Any other type on an existing ruleset is kept.
MANAGED_RULES = frozenset(
    {
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_linear_history",
        "required_status_checks",
    }
)
# How many recent pull requests to scan for check names.
RECENT_PRS = 10


class GhError(Exception):
    """A `gh` invocation failed; the message is gh's own stderr."""


def gh_api(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    """Call `gh api` and return the decoded JSON response (None when empty)."""
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
    """Return OWNER/NAME of the GitHub repo checked out in the working directory."""
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


def seen_checks(repo: str, default_branch: str) -> dict[str, set[int | None]]:
    """Map every check name GitHub reported recently to the app ids that sent it.

    Scans the heads of the last RECENT_PRS pull requests (where pull_request-only
    workflows report) and the default branch head. Covers both check runs and
    legacy commit statuses from external CI; statuses carry no app id (None).
    """
    shas: list[str] = []
    pulls = gh_api(f"repos/{repo}/pulls?state=all&per_page={RECENT_PRS}") or []
    shas += [p["head"]["sha"] for p in pulls]
    try:
        shas.append(gh_api(f"repos/{repo}/commits/{default_branch}")["sha"])
    except GhError:
        pass  # empty repository: no default branch head yet
    names: dict[str, set[int | None]] = {}
    for sha in dict.fromkeys(shas):
        runs = gh_api(f"repos/{repo}/commits/{sha}/check-runs?per_page=100") or {}
        for run in runs.get("check_runs", []):
            app = (run.get("app") or {}).get("id")
            names.setdefault(run["name"], set()).add(app)
        status = gh_api(f"repos/{repo}/commits/{sha}/status?per_page=100") or {}
        for st in status.get("statuses", []):
            names.setdefault(st["context"], set()).add(None)
    return names


def build_body(args: argparse.Namespace) -> dict[str, Any]:
    """Build the ruleset request body from the parsed flags alone."""
    rules: list[dict[str, Any]] = [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": args.approvals,
                "dismiss_stale_reviews_on_push": args.dismiss_stale,
                "require_code_owner_review": args.code_owners,
                "require_last_push_approval": False,
                "required_review_thread_resolution": args.resolve_threads,
                "allowed_merge_methods": args.merge_methods,
            },
        },
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
    bypass: list[dict[str, Any]] = []
    if args.admin_bypass != "none":
        bypass.append(
            {
                "actor_id": ADMIN_ROLE_ID,
                "actor_type": "RepositoryRole",
                "bypass_mode": args.admin_bypass,
            }
        )
    for app_id in args.bypass_app or []:
        bypass.append(
            {"actor_id": app_id, "actor_type": "Integration", "bypass_mode": "always"}
        )
    return {
        "name": args.name,
        "target": "branch",
        "enforcement": args.enforcement,
        "conditions": {"ref_name": {"include": [args.branch], "exclude": []}},
        "bypass_actors": bypass,
        "rules": rules,
    }


def _actor_key(actor: dict[str, Any]) -> tuple[Any, Any]:
    return (actor.get("actor_type"), actor.get("actor_id"))


def merge_existing(
    body: dict[str, Any], existing: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Keep what the existing ruleset has that this script does not manage.

    Returns the merged body and human-readable notes on what was kept or dropped.
    The admin role is managed by --admin-bypass, so an existing admin bypass is
    replaced; every other bypass actor and every unmanaged rule type is kept.
    """
    notes: list[str] = []
    ours = {_actor_key(a) for a in body["bypass_actors"]}
    admin = ("RepositoryRole", ADMIN_ROLE_ID)
    for actor in existing.get("bypass_actors") or []:
        key = _actor_key(actor)
        if key in ours:
            continue
        if key == admin:
            notes.append("removing the existing admin bypass (no --admin-bypass given)")
            continue
        body["bypass_actors"].append(
            {
                "actor_id": actor.get("actor_id"),
                "actor_type": actor["actor_type"],
                "bypass_mode": actor.get("bypass_mode", "always"),
            }
        )
        notes.append(f"keeping bypass actor {key[0]} {key[1]}")
    ours_types = {r["type"] for r in body["rules"]}
    for rule in existing.get("rules") or []:
        if rule["type"] in MANAGED_RULES:
            if rule["type"] not in ours_types:
                notes.append(f"removing rule {rule['type']} (no flag asks for it)")
            continue
        body["rules"].append(rule)
        notes.append(f"keeping rule {rule['type']}")
    return body, notes


def find_ruleset(repo: str, name: str) -> int | None:
    """Return the id of this repo's own branch ruleset called `name`, if any."""
    page = 1
    while True:
        rulesets = (
            gh_api(
                f"repos/{repo}/rulesets?includes_parents=false&per_page=100&page={page}"
            )
            or []
        )
        for rs in rulesets:
            if rs.get("name") == name and rs.get("target", "branch") == "branch":
                return int(rs["id"])
        if len(rulesets) < 100:
            return None
        page += 1


def readback_branch(pattern: str, default_branch: str) -> str | None:
    """Name a concrete branch the ref pattern covers, or None if it is a glob."""
    if pattern in ("~DEFAULT_BRANCH", "~ALL"):
        return default_branch
    name = pattern.removeprefix("refs/heads/")
    return None if any(c in name for c in "*?[") else name


def warnings_for(
    repo: str, info: dict[str, Any], args: argparse.Namespace
) -> list[str]:
    """Collect conditions that make the planned ruleset likely to hurt."""
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
            "on the Free plan GitHub refuses with a 403"
        )
    return out


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse and cross-check the command line."""
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
        "--list-checks",
        action="store_true",
        help="Print the check names GitHub reported on the last "
        f"{RECENT_PRS} pull requests and the default branch head, then exit. "
        "Pick --check values from this list.",
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
        help="Required status check, exactly as --list-checks prints it (for "
        "Actions this is the job's display name, e.g. 'Run tests (3.12)', not "
        "its id). Repeat per check. A name GitHub never reported is refused. "
        "Default: none.",
    )
    p.add_argument(
        "--allow-unseen-check",
        action="store_true",
        help="Accept --check names GitHub has not reported yet, e.g. for a "
        "workflow that is being added in the same change. Pull requests stay "
        "blocked until that check reports.",
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
        "--bypass-app",
        action="append",
        type=int,
        metavar="APP_ID",
        help="Numeric id of a GitHub App (e.g. a release bot) that may push "
        "directly. Find it with `gh api /apps/<app-slug> --jq .id`. Repeatable.",
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
    """Run the CLI; see the module docstring for exit codes."""
    args = parse_args(argv)
    try:
        repo = args.repo or current_repo()
        info = gh_api(f"repos/{repo}")
        default_branch = info["default_branch"]
        seen: dict[str, set[int | None]] = {}
        if args.list_checks or args.check:
            seen = seen_checks(repo, default_branch)
        if args.list_checks:
            for name in sorted(seen):
                apps = ", ".join(sorted(str(a or "status") for a in seen[name]))
                print(f"{name}\t(app: {apps})")
            if not seen:
                print(
                    "no checks reported on recent pull requests or the default branch"
                )
            return 0
        if args.check and not args.allow_unseen_check:
            unseen = [c for c in args.check if c not in seen]
            if unseen:
                print(
                    f"error: GitHub never reported {unseen} on {repo}; requiring them "
                    "blocks every pull request. Known checks: "
                    f"{sorted(seen) or 'none'}. Run --list-checks, or pass "
                    "--allow-unseen-check if the check is new.",
                    file=sys.stderr,
                )
                return 2
            if args.actions_only:
                foreign = [
                    c for c in args.check if GITHUB_ACTIONS_APP_ID not in seen[c]
                ]
                if foreign:
                    print(
                        f"error: {foreign} are not reported by GitHub Actions, so "
                        "--actions-only would never accept them",
                        file=sys.stderr,
                    )
                    return 2
        if not info.get("permissions", {}).get("admin"):
            print(
                f"error: the gh account has no admin rights on {repo}; rulesets need admin",
                file=sys.stderr,
            )
            return 1
        body = build_body(args)
        existing_id = find_ruleset(repo, args.name)
        notes: list[str] = []
        if existing_id:
            existing = gh_api(f"repos/{repo}/rulesets/{existing_id}")
            body, notes = merge_existing(body, existing)
        action = f"update ruleset {existing_id}" if existing_id else "create ruleset"
        for w in warnings_for(repo, info, args):
            print(f"warning: {w}", file=sys.stderr)
        print(f"{repo}: {action} '{args.name}'")
        for n in notes:
            print(f"  {n}")
        if args.dry_run:
            print(json.dumps(body, indent=2))
            return 0
        if existing_id:
            result = gh_api(f"repos/{repo}/rulesets/{existing_id}", "PUT", body)
        else:
            result = gh_api(f"repos/{repo}/rulesets", "POST", body)
        branch = readback_branch(args.branch, default_branch)
        enforced = gh_api(f"repos/{repo}/rules/branches/{branch}") if branch else None
    except GhError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    fallback = f"https://github.com/{repo}/settings/rules/{result['id']}"
    print(f"ruleset id: {result['id']}")
    print(f"url: {result.get('_links', {}).get('html', {}).get('href') or fallback}")
    if branch is None:
        print(f"read-back skipped: '{args.branch}' is a pattern, not a branch")
        return 0
    types = {r["type"] for r in enforced or []}
    print(f"rules now enforced on '{branch}': {', '.join(sorted(types)) or 'none'}")
    if args.enforcement != "active":
        return 0
    missing = {r["type"] for r in body["rules"]} - types
    if missing:
        print(
            f"error: GitHub does not enforce {sorted(missing)} on '{branch}' "
            "after the update; check the ruleset in the repository settings",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
