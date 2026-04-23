# AGENTS.md

Instructions for AI agents working in this repository.

## Repository purpose

This is an **Agent Skills repository**. Every directory at the top level (excluding dotfiles and this file) is a skill that conforms to the [Agent Skills specification](https://agentskills.io/specification).

## Skill structure

Each skill is a directory containing at minimum a `SKILL.md` and a `README.md`:

```
skill-name/
├── SKILL.md          # Required: metadata + agent instructions (spec-defined)
├── README.md         # Required: human-readable documentation
├── scripts/          # Optional: executable code
├── references/       # Optional: detailed reference material
├── assets/           # Optional: templates, resources, data files
└── ...
```

### `SKILL.md` (for agents)

Must contain YAML frontmatter followed by Markdown instructions.

**Required frontmatter fields:**

| Field         | Constraints                                                                                |
|---------------|--------------------------------------------------------------------------------------------|
| `name`        | 1-64 chars. Lowercase `a-z`, digits, hyphens only. No leading/trailing/consecutive hyphens. Must match the parent directory name. |
| `description` | 1-1024 chars. Describes what the skill does AND when to use it. Include keywords that help agents identify relevant tasks. |

**Optional frontmatter fields:**

| Field           | Purpose                                                        |
|-----------------|----------------------------------------------------------------|
| `license`       | License name or reference to bundled license file.             |
| `compatibility` | Environment requirements (max 500 chars). E.g. required tools, runtime, network access. |
| `metadata`      | Arbitrary key-value map for additional properties.             |
| `allowed-tools` | Space-separated string of pre-approved tools (experimental).   |

**Body content guidelines:**

- Keep `SKILL.md` under **500 lines / 5000 tokens**. Move detailed reference material to `references/`.
- Focus on what the agent *wouldn't know without the skill*: project conventions, domain procedures, non-obvious edge cases, specific tools/APIs.
- Favor procedures over declarations. Teach the agent *how to approach* a class of problems, not *what to produce* for a specific instance.
- Provide defaults, not menus. Pick one recommended approach; mention alternatives briefly.
- Include a gotchas section for environment-specific facts that defy reasonable assumptions.
- Use templates for output format requirements.
- Use checklists for multi-step workflows.
- Add validation loops where the agent should verify its own work.

### `README.md` (for humans)

Every skill must have a `README.md` that documents:

- What the skill does (in plain language)
- Prerequisites and dependencies
- Usage examples
- Configuration options (if any)
- How to test or validate the skill

This file is for human consumption. Do not duplicate the full `SKILL.md` instructions here.

## Creating a new skill

1. Create a directory with a valid skill name (lowercase, hyphens, no leading/trailing/consecutive hyphens).
2. Create `SKILL.md` with required frontmatter (`name`, `description`) and agent instructions.
3. Create `README.md` with human-readable documentation.
4. Add scripts to `scripts/`, references to `references/`, and static resources to `assets/` as needed.
5. Verify the directory name matches the `name` field in `SKILL.md` frontmatter exactly.

## Conventions

- **Naming**: Skill directory names and `name` fields use lowercase kebab-case (`my-skill`, not `MySkill` or `my_skill`).
- **File references**: Use relative paths from the skill root. Keep references one level deep from `SKILL.md`.
- **Progressive disclosure**: Agents load `name` + `description` at startup (~100 tokens), the full `SKILL.md` body on activation (<5000 tokens), and referenced files only when needed. Structure skills to take advantage of this.
- **Self-contained**: Each skill directory should be independently usable. Avoid cross-skill dependencies.
- **Scripts**: Should be self-contained or clearly document dependencies. Include helpful error messages and handle edge cases.

## Validation

Use the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) reference library to validate skills:

```bash
skills-ref validate ./skill-name
```
