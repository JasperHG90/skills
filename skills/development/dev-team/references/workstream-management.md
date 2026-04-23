# Workstream Management

How to partition work into orthogonal workstreams and coordinate merges across worktrees.

---

## What is a Workstream?

A workstream is a logically grouped set of tickets that can be worked on independently and in parallel. Each workstream gets its own developer and its own worktree (isolated git branch).

The goal is **maximum parallelism with minimum conflict** — workstreams should be as orthogonal as possible so that merging is straightforward.

---

## Partitioning Principles

### 1. File-Level Orthogonality

The strongest form of independence: workstreams touch **different files and directories**.

Good partitioning:
- Workstream A: `packages/auth/` (new auth module)
- Workstream B: `packages/api/endpoints/` (new API endpoints)
- Workstream C: `tests/e2e/` (E2E test infrastructure)

Bad partitioning:
- Both workstreams A and B modify `packages/core/models.py` — merge conflict guaranteed

### 2. Interface-Level Orthogonality

When workstreams must interact, define **contracts** (interfaces, protocols, type definitions) upfront. Each workstream codes to the contract without needing the other's implementation.

Example:
- Define `AuthProvider` protocol in a shared file before development starts
- Workstream A implements the protocol
- Workstream B consumes it via the protocol type, not the concrete class

### 3. Independent Testability

Each workstream must be testable in isolation within its own worktree. If workstream B's tests require workstream A's code, the partitioning is wrong — either merge them or define a mock/stub.

---

## How to Identify Workstreams

During Phase 1, staff engineers partition the backlog:

1. **Group by domain**: Tickets that touch the same area of the codebase belong together
2. **Identify shared files**: List files that multiple groups need to modify — these are conflict hotspots
3. **Resolve conflicts**:
   - Move shared-file changes into a single "primary" workstream
   - Or define interfaces upfront so each workstream has its own files
4. **Validate independence**: For each workstream, ask: "Can a dev work on this without knowing what the other workstreams are doing?" If no, refine the boundaries.
5. **Check size**: Each workstream should be roughly balanced in effort. One massive workstream + one tiny one defeats the purpose of parallelism.

---

## Primary Workstream

One workstream is designated as **primary**. This workstream owns all shared files that multiple workstreams might otherwise conflict on:

- `pyproject.toml`, `package.json` (dependency changes)
- Configuration files (`.env`, `config.yaml`)
- CI/CD files (`.github/workflows/`)
- Shared type definitions or interfaces
- `__init__.py` re-exports

Other workstreams **must not modify primary workstream files**. If they need a change in a shared file, they create a ticket assigned to the primary workstream.

The primary workstream typically handles:
- Dependency additions
- Shared infrastructure (base classes, protocols)
- Configuration changes
- Any "glue" code that connects workstreams

---

## Tagging Convention

Every task in the backlog is prefixed with its workstream name in the subject:

```
[auth] Implement JWT token validation
[api] Add /users endpoint with pagination
[shared] Add pydantic models for auth types      ← primary workstream
```

This makes it easy to filter tasks by workstream in TaskList.

---

## Cross-Workstream Dependencies

Minimize these. When unavoidable:

1. Use TaskUpdate with `addBlockedBy`/`addBlocks` to express the dependency
2. PO monitors blocked tasks and prioritizes the blocking work
3. The blocking workstream completes and merges its relevant piece first
4. The blocked workstream pulls the merged changes and continues

Example:
- `[api] Add user endpoints` is blocked by `[shared] Define User schema`
- PO ensures `[shared]` ticket is prioritized and completed first
- After `[shared]` merges, `[api]` dev pulls the schema into their worktree

---

## Merge Strategy

After Phase 2 development completes, the team lead coordinates merging all worktree branches back into main.

### Merge Order

1. **Determine dependencies**: Which workstreams depend on others? Merge dependencies first.
2. **Primary workstream goes last**: It owns shared files, so merging it last avoids conflicts from other workstreams modifying files they shouldn't.
3. **Independent workstreams**: Merge in any order, but sequentially (not all at once).

### Merge Process

For each workstream, in order:

1. **Merge the worktree branch into main**:
   ```bash
   git merge {worktree-branch}
   ```

2. **Run the full test suite** immediately after merge:
   ```bash
   # Use the project's test command
   just test  # or uv run pytest, npm test, etc.
   ```

3. **If tests fail**: The dev who owns the failing workstream investigates and fixes. Do NOT proceed to the next merge until tests pass.

4. **If merge conflicts**: The dev who owns the conflicting workstream resolves them. They understand their changes best.

5. **After all merges**: One final comprehensive test run to confirm full integration.

### Handling Shared File Conflicts

If a non-primary workstream accidentally modified a shared file:
- The primary workstream's version takes precedence
- The non-primary dev adapts their changes to work with the primary version
- This is why the rule "only primary modifies shared files" exists — it prevents this scenario

### Post-Merge Verification

After all worktrees are merged:
- Full test suite passes
- All acceptance criteria from the requirements doc are still verifiable
- No regressions introduced by the integration
- QA can now proceed with Phase 3 review on the integrated codebase
