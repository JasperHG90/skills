---
name: blueprint
description: >
  Scan a repository and produce a comprehensive architectural blueprint document
  with tech stack, component maps, Mermaid diagrams, data flow, API surfaces,
  dependency graphs, and design patterns. Spawns parallel analysis agents for
  speed. Use whenever the user says "blueprint", "architecture overview",
  "architectural blueprint", "map this repo", "codebase analysis", "system
  design doc", "repo scan", "how is this repo structured", "document the
  architecture", or wants to understand, document, or map the architecture of
  a codebase. Also use when onboarding to a new codebase and wanting a
  high-level understanding, or when asked to create technical documentation
  for a project.
argument-hint: "[target-directory]"
---

# Architectural Blueprint Generator

You scan a repository and produce a comprehensive architectural blueprint. The output is a structured Markdown document with Mermaid diagrams, written to `BLUEPRINT.md` in the repo root.

The process has three phases: a quick scan to gather surface-level facts, parallel deep analysis by specialized agents, and synthesis into the final document.

## Input Handling

Parse the user's input for an optional target directory. If none is provided, use the current working directory. Validate that the directory exists and contains code (has files beyond just a README).

If the user provides a path as the argument (e.g., `/blueprint ./my-project`), use that as the target directory.

---

## Phase 1: Quick Scan

Before spawning agents, gather surface-level facts yourself. This context will be shared with all agents so they don't redundantly discover the same basics.

1. **List the root directory** — `ls -la` at the repo root to see the top-level layout.

2. **Detect languages and frameworks** — Check for indicator files:
   - Python: `pyproject.toml`, `setup.py`, `requirements.txt`, `Pipfile`
   - JavaScript/TypeScript: `package.json`, `tsconfig.json`
   - Rust: `Cargo.toml`
   - Go: `go.mod`
   - Java/Kotlin: `pom.xml`, `build.gradle`, `build.gradle.kts`
   - C/C++: `CMakeLists.txt`, `Makefile`, `meson.build`
   - Ruby: `Gemfile`
   - PHP: `composer.json`
   - .NET: `*.csproj`, `*.sln`
   - Docker: `Dockerfile`, `docker-compose.yml`
   - CI/CD: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`

3. **Read key docs** — Read `README.md` (first 100 lines) and `CLAUDE.md` / `AGENTS.md` if they exist. These often contain architecture summaries that bootstrap understanding.

4. **Count files by type** — Run a quick count of files by extension to understand the codebase size and composition:
   ```bash
   find <target> -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15
   ```

5. **Check for monorepo signals** — Look for workspace configurations, multiple package directories, or lerna/nx/turborepo configs.

6. **Compile quick scan summary** — Assemble your findings into a concise summary (~200 words) covering:
   - Primary language(s) and framework(s)
   - Package manager and build system
   - Monorepo vs single project
   - Approximate codebase size
   - Key documentation found

7. **Form an architecture hypothesis** — Based on the quick scan, form a preliminary hypothesis about the system's architecture (e.g., "This appears to be a layered monorepo with hexagonal core and plugin-based extensions" or "This looks like a microservices architecture with an API gateway"). Share this hypothesis with all analysts so they can validate, refine, or refute it. A hypothesis gives analysts a frame to work within, making their analysis more targeted than open-ended exploration.

---

## Phase 2: Parallel Deep Analysis

Spawn all 4 analysis agents in a **single turn** so they run concurrently. Each agent receives:
- The target directory path
- Your quick scan summary from Phase 1

Read each agent's instruction file before spawning it. The agents are:

| Agent | Instruction file | Focus |
|-------|-----------------|-------|
| Structure Analyst | `agents/structure-analyst.md` | Directory layout, modules, entry points |
| Dependency Analyst | `agents/dependency-analyst.md` | External + internal dependencies, infra |
| Pattern Analyst | `agents/pattern-analyst.md` | Architecture patterns, design decisions |
| API Analyst | `agents/api-analyst.md` | API surfaces, routes, CLI commands |

### Spawning pattern

For each agent, read its instruction file from the skill directory, then spawn it as a general-purpose agent:

```
Spawn Agent:
  name: "blueprint-{analyst-type}"
  subagent_type: "general-purpose"
  prompt: |
    {contents of the agent instruction file}

    ## Context
    Target directory: {target-path}
    Quick scan summary: {your Phase 1 summary}

    ## Output
    Return your findings as structured Markdown. Use the section headings
    specified in your instructions. Be thorough but concise — focus on
    architectural significance, not exhaustive file listings.
```

All 4 agents in the same message so they run in parallel.

---

## Phase 3: Synthesis

Once all agents have returned their findings:

1. **Cross-validate agent findings** — Before writing anything, check for consistency across agents:
   - Does the pattern analyst's architecture description align with the structure analyst's directory layout?
   - Does the API analyst's route list match the dependency analyst's framework identification?
   - Do the dependency analyst's internal module dependencies match the structure analyst's module boundaries?
   - Does anyone's findings contradict the Phase 1 architecture hypothesis?
   - Where agents disagree, investigate — the contradiction often reveals something interesting about the architecture.

2. **Completeness check** — Verify you have sufficient input for every section of the template:
   - [ ] All template sections have agent input (or a clear "N/A" with rationale)
   - [ ] Enough data to generate all Mermaid diagrams (component map, data flow, dependency graph)
   - [ ] Component descriptions explain *why* things exist, not just *what* they are
   - [ ] Entry points identified with types and locations
   - If gaps exist, send targeted follow-up questions to the relevant agent before proceeding.

3. **Read the blueprint template** from `references/blueprint-template.md`. This defines the exact output structure.

4. **Assemble the blueprint** — Fill in each section of the template using agent findings:
   - Technology Stack: from quick scan + dependency analyst
   - System Overview: synthesize from all agents into 2-3 coherent paragraphs
   - Directory Structure: from structure analyst
   - Component Map: from structure analyst + pattern analyst, generate a Mermaid `graph TD` diagram
   - Data Flow: from pattern analyst + API analyst, generate a Mermaid `sequenceDiagram` or `flowchart`
   - API Surface: from API analyst
   - Dependency Graph: external from dependency analyst (table), internal as Mermaid `graph LR`
   - Architecture Patterns: from pattern analyst
   - Architecture Assessment: from pattern analyst (where the architecture fits well and where it may create friction)
   - Key Design Decisions: from pattern analyst + any CLAUDE.md/ADR content
   - Entry Points: from structure analyst + API analyst

5. **Generate Mermaid diagrams** — These are the most valuable part of the blueprint. Take care to:
   - Keep diagrams readable (max ~15 nodes per diagram, split if larger)
   - Use meaningful labels, not file paths
   - Show directional relationships (A depends on B, not just "A connects to B")
   - Use subgraphs to group related components

6. **Resolve contradictions** — If agents disagree (e.g., one calls something a "service" and another calls it a "handler"), use the pattern analyst's findings as the authoritative source for naming conventions.

7. **Write the blueprint** — Save as `BLUEPRINT.md` in the target directory root.

8. **Verify the blueprint** — Spawn a verification agent that reads the generated BLUEPRINT.md and spot-checks 3-5 specific claims against the actual codebase:
   ```
   Spawn Agent:
     name: "blueprint-verifier"
     subagent_type: "general-purpose"
     prompt: |
       Read BLUEPRINT.md at {target-path}/BLUEPRINT.md. Pick 3-5 specific factual
       claims (e.g., "X is the entry point", "A depends on B", "pattern Y is used
       in module Z") and verify each by checking the actual source code. Report:
       - Claim: [what the blueprint says]
       - Verified: [yes/no]
       - Evidence: [what you found]
       If any claims are wrong, report what the correct information should be.
   ```
   If the verifier finds inaccuracies, fix them in BLUEPRINT.md before presenting to the user.

9. **Present to the user** — Give a brief summary of what was found: primary architecture pattern, number of components identified, key technologies. Mention the verification results. Let them know the full blueprint is at `BLUEPRINT.md`.

---

## Quality Guidelines

**What makes a good blueprint:**
- Someone unfamiliar with the repo can read it and understand the system in 10 minutes
- Mermaid diagrams are accurate and render correctly
- Component descriptions explain *why* something exists, not just *what* it is
- Dependencies are categorized by purpose (not just listed)
- The document is self-contained — no broken references or "see X for details"

**Common pitfalls to avoid:**
- Don't list every file — focus on architecturally significant components
- Don't guess at design decisions — if you can't tell why something was done, say what it does and note the pattern
- Don't generate diagrams with 30+ nodes — split into multiple focused diagrams
- Don't include implementation details like function signatures — this is an architecture document
- Don't skip sections — if an area doesn't apply (e.g., no CLI), say "N/A" with a brief note

---

## Reference Files

| File | When to read | Purpose |
|------|-------------|---------|
| `agents/structure-analyst.md` | Phase 2 — before spawning | Instructions for structure analysis agent |
| `agents/dependency-analyst.md` | Phase 2 — before spawning | Instructions for dependency analysis agent |
| `agents/pattern-analyst.md` | Phase 2 — before spawning | Instructions for pattern analysis agent |
| `agents/api-analyst.md` | Phase 2 — before spawning | Instructions for API analysis agent |
| `references/blueprint-template.md` | Phase 3 — synthesis | Output document template |
