---
name: release-claude-code-plugin
description: Release a Claude Code plugin distributed via git — bumps the version in its .claude-plugin/plugin.json, keeps any marketplace.json entry in sync, commits, and pushes. Use whenever the user says "release the plugin", "bump the plugin version", "publish the Claude Code plugin", "ship the plugin", "cut a plugin release", or otherwise wants to version a plugin whose plugin.json holds the version. NOT for tag-and-CI release flows where a pushed v* tag builds artifacts — use the `release` skill for those.
---

# Release a Claude Code Plugin

Bumps the version of a Claude Code plugin and publishes it over git.

Claude Code plugins are usually distributed straight from a repository: users add the marketplace and install the plugin from a branch or ref, so there is no build to run and no CI to wait on. The version lives in the plugin's manifest, and "releasing" means bumping that version, committing, and pushing so installs pick it up. This skill is the lightweight, git-only counterpart to the `release` skill — reach for `release` instead when pushing a `v*` tag is what triggers a build and a GitHub release.

## How a plugin's version is stored

A plugin's version can live in **up to two places that must agree**:

1. **`plugin.json`** — every plugin has one at `<plugin-dir>/.claude-plugin/plugin.json`, with a `"version"` field. This is the source of truth.
2. **`marketplace.json`** — a marketplace repo has one at its root, `.claude-plugin/marketplace.json`, listing plugins under `"plugins"`. Each entry has a `"name"` and a `"source"` (relative path to the plugin dir), and **often duplicates `"version"`**. When it does, that copy has to be bumped in lockstep or installs read a stale number.

A repo may be a single plugin, a marketplace of several plugins in one repo (each under its own `source` path), or a plugin with no marketplace at all. Discover which before bumping.

## Step 1 — Locate the plugin(s) and read the current version

Run from the repo root. Find the real manifests, excluding vendored or installed copies (`.claude/plugins/` holds *installed* plugins, worktrees and `.temp`/`node_modules`/`.venv` hold duplicates — none of those are the source you edit):

```bash
find . \( -path '*/.claude/plugins/*' -o -path '*/.venv/*' -o -path '*/node_modules/*' \
  -o -path '*/.temp/*' -o -path '*/worktrees/*' \) -prune -o \
  -name plugin.json -path '*/.claude-plugin/*' -print -o \
  -name marketplace.json -path '*/.claude-plugin/*' -print
```

Read the `"version"` from each `plugin.json`. If more than one plugin turns up, ask the user which to release (or whether to bump several). If a `marketplace.json` exists, read its `plugins[]` and note, for the plugin being bumped, whether an entry carries a `"version"`. Match the entry to the plugin **by `"name"` first**, falling back to comparing the `"source"` path against the plugin's directory — normalize both before comparing (strip a leading `./` and any trailing `/`, or just compare basenames), since `source` is written various ways (`./packages/foo`, `packages/foo/`). Flag it now if the manifest and marketplace versions already disagree, since that changes what "in sync" should become.

## Step 2 — Determine the new version

Read the current version and follow the scheme it already uses rather than imposing one. Two conventions show up in practice:

- **SemVer** (`1.4.2`), optionally with a pre-release (`1.5.0-rc1`, `1.5.0-rc.2`, `1.5.0-beta.1` — dotted or undotted; match whatever's there).
- **A trailing pre-GA letter** (`0.3.0b`) — some plugins append a bare letter to mark every release as not-yet-stable. Preserve that suffix verbatim on numeric bumps; only drop it when the user explicitly stabilizes.

Default to a **patch bump that preserves whatever suffix is present**, unless the user asks for something else:

| Current | Action | New |
|---|---|---|
| `1.4.2` | patch (default) | `1.4.3` |
| `1.4.2` | minor | `1.5.0` |
| `1.4.2` | major | `2.0.0` |
| `1.5.0-rc1` | advance the pre-release series | `1.5.0-rc2` |
| `1.5.0-rc2` | promote to stable | `1.5.0` |
| `0.3.0b` | patch, keep suffix (default) | `0.3.1b` |
| `0.3.1b` | stabilize (drop the suffix) | `0.3.1` |

Two things are easy to get wrong, so hold them straight:

- **Promotion never re-bumps the numbers.** Dropping a `-rcN` or a trailing letter ships the *same* `MAJOR.MINOR.PATCH` (`1.5.0-rc2` → `1.5.0`; `0.3.1b` → `0.3.1`). If the user wants both a stable release *and* a higher number, that's two decisions — confirm which they mean.
- **To iterate within a pre-release**, advance the counter rather than the version core (`1.5.0-rc1` → `1.5.0-rc2`), not `1.5.1-rc1`.

To inform the bump type, look at what changed since the last version bump:

```bash
git log --oneline -- <plugin-dir>
```

Confirm the target version with the user before editing anything.

## Step 3 — Bump the manifest(s)

Edit the `"version"` field in `<plugin-dir>/.claude-plugin/plugin.json`.

If the marketplace entry for this plugin also carries a `"version"` (from Step 1), update it to the same value so the two never drift. If it does not carry one, leave `marketplace.json` alone — don't add a field the maintainer chose not to track.

Change only the version field(s). Leave surrounding formatting untouched so the diff is a clean one- or two-line change.

## Step 4 — Commit

Commit only the manifest files you changed, by pathspec, so nothing the user happened to already stage gets swept into the release commit:

```bash
git commit -- <plugin-dir>/.claude-plugin/plugin.json [<root>/.claude-plugin/marketplace.json]
```

(A bare `git commit` records the whole index; the pathspec form commits exactly those files regardless of what else is staged.) Glance at `git status` first — if the version files show up as *already staged* alongside unrelated changes, sort that out before committing.

Use a message that names the plugin and the new version. Match the repo's existing convention for the scope — check `git log --oneline` for prior bump commits, since some repos scope by the package/directory name rather than the plugin's `name`:

```
chore(<plugin-or-package-name>): bump version to <version>
```

## Step 5 — Push

A push is what publishes the release: most marketplaces install a plugin from a branch (commonly the default), so once the bumped commit lands on that branch, installs pick it up — no tag required.

That only holds if you push the branch installs actually read. Resolve the current branch and its upstream rather than assuming `origin`:

```bash
git rev-parse --abbrev-ref HEAD          # current branch
git rev-parse --abbrev-ref @{u}          # its configured upstream (remote/branch), if any
```

If the current branch isn't the one the marketplace installs from (usually the default branch), say so and confirm — pushing a feature branch commits the bump but publishes nothing. With the user's go-ahead, push to the resolved upstream (or `git push -u <remote> <branch>` if none is set yet). If the push is rejected as non-fast-forward, the remote moved: integrate it (`git pull --rebase`) and retry — don't force-push a shared release branch.

If this repo instead marks plugin releases with git tags or a CI pipeline, that's the `release` skill's territory; hand off rather than half-doing both.

## Step 6 — Confirm

Print a short summary:

- Plugin: `<plugin-name>`
- Previous version → new version
- Files bumped: `plugin.json` (and `marketplace.json` if synced)
- Commit: short SHA
- Pushed to: `<remote>/<branch>`
