# /release-claude-code-plugin

A Claude Code skill that releases a Claude Code **plugin** distributed straight over git — the kind users install from a marketplace branch rather than a built artifact. It bumps the version in the plugin's `.claude-plugin/plugin.json`, keeps any `marketplace.json` entry in sync, commits, and pushes. It's the lightweight, git-only counterpart to the [`release`](../release/README.md) skill, which handles tag-and-CI release flows.

## What it does

1. **Locate the plugin(s)** — finds the real `plugin.json` / `marketplace.json` manifests, skipping installed and vendored copies (`.claude/plugins/`, worktrees, `node_modules`, etc.). Asks which plugin if a repo holds several.
2. **Determine the new version** — reads the current version, follows the scheme it already uses (SemVer, or a trailing pre-GA suffix), and proposes the next one. Defaults to a patch bump; confirms before editing.
3. **Bump the manifest(s)** — edits `plugin.json`, and the matching `marketplace.json` entry too when it duplicates the version, so the two never drift.
4. **Commit** — commits only the manifest files, by pathspec, so nothing else in the index sneaks into the release commit.
5. **Push** — resolves the current branch and its upstream, warns if you're not on the branch installs actually read, then publishes.
6. **Summarize** — plugin, version before → after, files bumped, commit SHA, where it pushed.

## Where a plugin's version lives

| File | Path | Role |
|---|---|---|
| `plugin.json` | `<plugin-dir>/.claude-plugin/plugin.json` | Source of truth — every plugin has one, with a `version` field. |
| `marketplace.json` | `<repo-root>/.claude-plugin/marketplace.json` | A marketplace lists its plugins here; each entry **often duplicates `version`**, which must be bumped in lockstep. |

Not every repo has a `marketplace.json`, and not every marketplace entry carries a `version` — the skill only touches the second file when there's a version there to keep in sync.

## When to use this vs `release`

| Situation | Skill |
|---|---|
| Plugin versioned in `plugin.json`, installed from a git branch, no build to run | **`release-claude-code-plugin`** (this one) |
| Pushing a `v*` tag triggers CI that builds artifacts and cuts a GitHub release | [`release`](../release/README.md) |

## Usage

```
/release-claude-code-plugin
```

Then follow the prompts. The skill confirms the target version before editing and confirms again before pushing.

## Safety

- Commits by pathspec, so a pre-populated index doesn't contaminate the release commit.
- Warns before publishing from a non-default branch (a push there bumps the commit but publishes nothing).
- On a rejected non-fast-forward push, integrates the remote (`git pull --rebase`) and retries rather than force-pushing a shared branch.
