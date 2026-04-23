# Contributing to Xebia Data Agent Skills

This document provides guidelines for contributing new skills and maintaining the repository.

## Prerequisites

To contribute to this repository, you need:

- **Python 3.12+** - Required for running development tools
- **uv** - Fast Python package manager for dependency management
- **make** - For running development commands
- **Git** - For version control

## Quick Setup

Set up your development environment with a single command:

```bash
make setup
```

This command will:
1. Create a Python virtual environment using `uv`
2. Install development dependencies (`prek`, `pytest`)
3. Install pre-commit hooks

## Available Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make venv` | Set up a virtual environment |
| `make install` | Install Python dependencies |
| `make pre_commit_setup` | Install pre-commit hooks |
| `make setup` | Run venv, install, and pre_commit_setup |
| `make pre_commit` | Run pre-commit checks manually |

## Skill Requirements

### Directory Structure

Every skill must be placed in a directory under `skills/` with the following structure:

```
skills/
  your-skill-name/
    SKILL.md          # Required: Skill definition with frontmatter
    scripts/script.py # Optional: Supporting scripts
    assets/           # Optional: Bundled resources
    references/       # Optional: Additional documentation/skill abillities
```

### Required Files

**Every skill directory must contain a `SKILL.md` file.**

### SKILL.md Frontmatter Requirements

The `SKILL.md` file must start with YAML frontmatter metadata:

```yaml
---
name: your-skill-name       # Required, matches directory name
description: Description    # Required, describes skill purpose
---
```

#### Required Fields

| Field | Description | Constraints |
|-------|-------------|-------------|
| `name` | The unique identifier for the skill | Must match directory name, 1-64 chars, kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`) |
| `description` | A detailed description of what the skill does | 1-1024 characters |

#### Optional Fields

| Field | Description | Constraints |
|-------|-------------|-------------|
| `license` | License for the skill (e.g., `MIT`, `Apache-2.0`) or reference to bundled LICENSE file | - |
| `compatibility` | Environment requirements (OS, binaries, network access) | Max 500 characters |
| `metadata` | Arbitrary key-value pairs for additional metadata (author, version, etc.) | Object |
| `allowed-tools` | List of pre-approved tools the skill can use | Array of strings |

### Naming Convention

- Directory names must use **kebab-case**: lowercase letters, numbers, and hyphens only
- Pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`
- The `name` field in frontmatter must **exactly match** the directory name

### Example SKILL.md

```yaml
---
name: python-testing
description: A comprehensive skill for writing and running Python tests with pytest and managing test coverage.
license: MIT
compatibility: Python 3.12+, pytest 8.0+
metadata:
  author: Your Name
  version: 1.0.0
allowed-tools:
  - Bash
  - Edit
  - Write
---

# Python Testing Skill

[Your skill content here...]
```

## Code Quality Checks

All code in this repository must pass the following automated checks. These run both locally via pre-commit hooks and in CI/CD pipelines.

### Linting & Formatting

| Tool          | Purpose | Description |
|---------------|---------|-------------|
| `ruff`        | Python linting | Fast Python linter with auto-fix |
| `ruff-format` | Python formatting | Code formatting (auto-formats on run) |
| `mypy`        | Static type checking | Type hints validation |

### Validation Checks

| Check | Purpose |
|-------|---------|
| `check-yaml` | YAML syntax validation |
| `check-json` | JSON syntax validation |
| `check-added-large-files` | Prevents large files from being committed |
| `check-merge-conflict` | Detects merge conflict markers |
| `detect-private-key` | Detects private keys in code |
| `debug-statements` | Detects debug statements (e.g., `print()`, `pdb`) |
| `end-of-file-fixer` | Ensures files end with newline |

### Skill-Specific Checks

When you add or modify a skill, additional validation runs:

1. **SKILL.md presence** - Every skill directory must contain `SKILL.md`
2. **Frontmatter validation** - Frontmatter must match the [agentskills.io schema](https://agentskills.io/specification)
3. **Name matching** - The `name` field must match the directory name exactly

## Common-Sense Guidelines

Before contributing, please follow these best practices:

### 1. Check for Duplicates

Search existing skills to ensure you're not adding a skill with similar functionality to one that already exists. If you find an existing skill that's close to what you need:

- Consider improving the existing skill instead
- Or create a new skill if the functionality is sufficiently distinct

### 2. Review Existing Skills

Look at existing skills for examples of good patterns:

### 3. Follow the agentskills.io Specification

Skills follow the [agentskills.io](https://agentskills.io) specification. Ensure your `SKILL.md` complies with this specification.

### 4. Write Clear Documentation

- Follow [Claude's best practices guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) for writing effective skills
- Include clear instructions on when and how to use the skill
- Provide examples where appropriate
- Document any prerequisites or dependencies

### 5. Test Locally

Before pushing changes, always run the pre-commit checks:

```bash
make pre_commit
```

This will run all linting, formatting, and validation checks.

## Submission Process

Follow these steps to contribute a new skill:

### 1. Create a Feature Branch

```bash
git checkout -b feat/your-skill-name
```

### 2. Add Your Skill

Create your skill directory under `skills/`:

```bash
mkdir -p skills/your-skill-name
```

Add your `SKILL.md` and any supporting files.

### 3. Run Pre-Commit Checks

```bash
make pre_commit
```

Fix any issues that are reported.

### 4. Stage and Commit Changes

```bash
git add .
git commit -m "feat: add your-skill-name skill"
```

### 5. Push and Create Pull Request

```bash
git push -u origin feat/your-skill-name
```

Then create a pull request via GitHub.

### 6. CI/CD Validation

When you create a pull request, the following CI checks will automatically run:

1. **Pre-commit checks** - All linting, formatting, and validation
2. **Skill formatting checks** - Validates SKILL.md frontmatter and structure

Both checks must pass for the PR to be mergeable.

## Getting Help

If you have questions or need help contributing:

- Review existing skills for examples
- Check the [agentskills.io specification](https://agentskills.io/specification)
