"""Tests for the pure parts of apply_ruleset.py: body building and merging.

Run from the skill root: `uv run --with pytest pytest tests/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import apply_ruleset as ar  # noqa: E402


def body_for(*flags: str) -> dict:
    return ar.build_body(ar.parse_args(list(flags)))


def rule(body: dict, rule_type: str) -> dict | None:
    return next((r for r in body["rules"] if r["type"] == rule_type), None)


def test_defaults_protect_default_branch_with_one_approval() -> None:
    body = body_for()
    assert body["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]
    assert {r["type"] for r in body["rules"]} == {
        "deletion",
        "non_fast_forward",
        "pull_request",
    }
    pr = rule(body, "pull_request")
    assert pr is not None
    assert pr["parameters"]["required_approving_review_count"] == 1
    assert pr["parameters"]["required_review_thread_resolution"] is True
    assert body["bypass_actors"] == []


def test_checks_pin_to_actions_only_when_asked() -> None:
    plain = rule(body_for("--check", "Run tests"), "required_status_checks")
    pinned = rule(
        body_for("--check", "Run tests", "--actions-only", "--strict"),
        "required_status_checks",
    )
    assert plain is not None and pinned is not None
    assert plain["parameters"]["required_status_checks"] == [{"context": "Run tests"}]
    assert pinned["parameters"]["required_status_checks"] == [
        {"context": "Run tests", "integration_id": ar.GITHUB_ACTIONS_APP_ID}
    ]
    assert pinned["parameters"]["strict_required_status_checks_policy"] is True


def test_bypass_actors_for_admin_and_apps() -> None:
    body = body_for("--admin-bypass", "pull_request", "--bypass-app", "42")
    assert body["bypass_actors"] == [
        {
            "actor_id": ar.ADMIN_ROLE_ID,
            "actor_type": "RepositoryRole",
            "bypass_mode": "pull_request",
        },
        {"actor_id": 42, "actor_type": "Integration", "bypass_mode": "always"},
    ]


@pytest.mark.parametrize(
    "flags",
    [
        ["--linear-history"],  # merge commits still allowed by default
        ["--strict"],  # strict without any check
        ["--approvals", "11"],
    ],
)
def test_impossible_combinations_are_refused(flags: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        ar.parse_args(flags)
    assert exc.value.code == 2


def test_update_keeps_unmanaged_actors_and_rules() -> None:
    existing = {
        "bypass_actors": [
            {"actor_id": 7, "actor_type": "Integration", "bypass_mode": "always"},
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"},
        ],
        "rules": [
            {"type": "required_signatures"},
            {"type": "required_linear_history"},
        ],
    }
    merged, notes = ar.merge_existing(body_for(), existing)
    assert merged["bypass_actors"] == [
        {"actor_id": 7, "actor_type": "Integration", "bypass_mode": "always"}
    ]
    types = [r["type"] for r in merged["rules"]]
    assert "required_signatures" in types
    assert "required_linear_history" not in types
    assert any("removing the existing admin bypass" in n for n in notes)
    assert any("removing rule required_linear_history" in n for n in notes)


def test_update_does_not_duplicate_an_actor_we_also_set() -> None:
    existing = {
        "bypass_actors": [
            {"actor_id": 42, "actor_type": "Integration", "bypass_mode": "always"}
        ],
        "rules": [],
    }
    merged, _ = ar.merge_existing(body_for("--bypass-app", "42"), existing)
    assert len(merged["bypass_actors"]) == 1


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("~DEFAULT_BRANCH", "main"),
        ("refs/heads/release", "release"),
        ("refs/heads/release/*", None),
    ],
)
def test_readback_branch(pattern: str, expected: str | None) -> None:
    assert ar.readback_branch(pattern, "main") == expected
