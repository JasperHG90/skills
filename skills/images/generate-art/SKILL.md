---
name: generate-art
description: |
  Generate static artwork/illustrations for this repo with Nano Banana Pro (aka
  "nano banana", Gemini 3 Pro Image) via tools/generate_art.py — craft a detailed
  prompt, run the script, view the result, iterate. Use this whenever the user
  wants to create, generate, or regenerate a visual asset for the project: a
  board/architecture diagram, engineer portrait, event-card art, icon, splash, or
  any image that lands as a PNG in the repo — even if they don't name the tool or
  just say "make me an image / a picture of X". Do NOT trigger for in-game runtime
  image needs (there are none) or for editing source code rather than producing an
  image file.
---

# Generate art

Build-time asset tooling. The engine is `scripts/generate_art.py`, bundled in
this skill; the skill body is the prompt-craft + iterate loop around it.

This skill is a **general** art generator — it knows *how* to generate, apply a
style, and cast a character, but ships with no project-specific art. A project's
house styles live in the *project* (`docs/styles/`, see "Style presets"), and the
cast pool is just whatever portraits a project points `--cast-dir` at. Same skill,
any repo.

The engine is bundled on purpose so packaging it as a `.skill` keeps it runnable
elsewhere. Trade-off to know: `.claude/` is gitignored in this repo, so the
bundled engine is not in git — its home of record is this skill directory. Don't
expect to `git log` it. (Project styles in `docs/styles/` *are* tracked.)

## Boundary — why Gemini is allowed here

This is build-time tooling, **not game runtime** — that distinction is what keeps
it legal. The game's only LLM is Nous Hermes via `LLMClient` (see `.claude/rules`),
and that contract governs the round loop. This script just produces static PNGs
checked into the repo; it never runs in the game. So the rule of thumb is: the
Gemini SDK and `GEMINI_API_KEY` stay out of `backend/src/game/`. Keep that line
clean and there's no conflict.

## Prerequisites

- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) set in the environment. The script
  reads it; do not hardcode keys.
- `uv` available. The script is a self-contained PEP 723 script — `uv run`
  installs `google-genai` + `pillow` into an ephemeral env. No backend deps.

## Run

Run from the repo root:

```
uv run .claude/skills/generate-art/scripts/generate_art.py --prompt "<prompt>" --out <path.png> [--banana pro] [--aspect 16:9] [--size 2K] [--ref existing.png]
```

- `--prompt` / `--prompt-file` — one is required. For long prompts, write to a
  temp file and use `--prompt-file` to avoid shell-quoting pain.
- `--out` — required. Save to a **tracked** dir (`/*.png` and `.claude` are
  gitignored). See output conventions below.
- `--banana` — `pro` (Gemini 3 Pro Image, default) or `flash` (Gemini 2.5 Flash
  Image — cheaper/faster, lower fidelity). Use `flash` for quick drafts/icons,
  `pro` for hero/board art and anything text-heavy or detail-critical.
- `--model` — explicit model id; overrides `--banana` if a new variant ships.
- `--aspect` — `1:1 3:2 2:3 3:4 4:3 4:5 5:4 9:16 16:9 21:9` (default `16:9`).
- `--size` — `1K | 2K | 4K` (default `2K`). Pro only; ignored for `flash`.
- `--style` — named style preset from `--styles-dir` (e.g. `engineers`). Appends
  the distilled house-style block to the prompt. Prefer this over `--ref` for
  style matching — see "Style presets" below.
- `--styles-dir` — where project style presets live (default `docs/styles`).
- `--style-file` — ad-hoc style preset file; overrides `--style`.
- `--cast` — opt-in: feature a real engineer's likeness in the art. `random`
  picks one; or pass an engineer name (file stem in `--cast-dir`). Off by
  default. Great for people/process cards where it's nice that the moment happens
  to a real teammate. Combine with `--style engineers`.
- `--cast-dir` — portrait dir for `--cast` (default `frontend/public/engineers`).
- `--ref` — reference image(s) for style/edit continuity; repeatable. Use to
  edit an existing image, or to anchor on a specific asset when text alone isn't
  enough. Note: passing a *character* portrait as `--ref` reproduces that person
  — for generic art prefer `--style`; for *intentional* engineer reuse prefer
  `--cast`.

## Style presets

Style presets are **project content, not part of this skill.** The skill is a
general art generator; each project keeps its own house styles and points
`--styles-dir` at them (default `docs/styles/`). A preset is a markdown file of
distilled style guidance that `--style <name>` appends to the prompt, so a house
look stays consistent across calls — without passing a character image as `--ref`
(which tends to clone that specific person).

This project ships one: `docs/styles/engineers.md` — the warm cartoon house style,
distilled from `frontend/public/engineers/`.

**Use a preset:** add `--style engineers` to any call (resolves to
`docs/styles/engineers.md`). The per-asset prompt still carries the *scene* and
composition negatives (no text, no frame, aspect); the preset carries only the
*look*.

**Distil a new style** (the reusable "capture the look once" step):
1. Look at 2-3 real reference images with the Read tool — the actual rendered art
   you want to match, not a written spec (specs drift from reality; see how
   `card-prompts.md` diverged from the real engineer style).
2. Write what you observe: medium/rendering, linework, shading & light, palette,
   background treatment, mood. Describe the *look*, not any scene or subject.
   Keep composition/negatives out — those are per-asset.
3. Save it to the project's styles dir as `docs/styles/<name>.md` with an
   `# Style: <name>` heading. (It lives in the project, not the skill.)
4. Validate: generate one asset with `--style <name>` and no character `--ref`,
   then Read the output and check it matches the references.

Keep presets look-only and subject-agnostic so they compose with any prompt.

**Generic vs. casting a real engineer.** Two deliberate paths, both opt-in:
- **Generic in-style** (default/standard) — `--style engineers`, no character ref.
  The art matches the house look but depicts nobody in particular.
- **Cast a real engineer** (option) — add `--cast random` (or `--cast <name>`) to
  feature an actual roster portrait. Nice for people/process cards where it lands
  that the moment happens to a real teammate. The script logs which engineer it
  cast. This is an option, not the default — only reach for it when reuse is
  wanted.

## Output conventions

- **Engineer portraits** → `frontend/public/engineers/<name>.png`, `--aspect 3:4`.
  Match the existing roster's style (pass an existing portrait via `--ref`).
- **Board / architecture visuals** → `docs/assets/`, `--aspect 16:9`.
- **Event / card / icon art** → ask where it should live; default `docs/assets/`.

## Workflow

1. **Clarify the asset** — what it depicts, where it lands, aspect, and whether
   it must match an existing style (if so, use `--style`; distil a new preset
   first if none fits).
2. **Craft the prompt yourself.** Ground it in the design doc and rules — e.g.
   the board is a 3-tier dependency stack (foundation → infra DAG → use-case
   pipeline; `DESIGN_DOCUMENT.md`, `game/world.md`). Be specific about subject,
   layout, labels, palette, and style; end with negatives (no logos, no
   paragraphs of text). Long prompts → temp file + `--prompt-file`.
3. **Run** the script.
4. **View the result** with the Read tool on the output PNG and judge it
   against what was asked — do not claim success without looking.
5. **Iterate** on the prompt (or add `--ref`) until it's right. Show the user
   the image and the final path.

## Notes

- Output is non-deterministic; same prompt varies run to run.
- If the response has no image (safety filter / refusal), the script exits with
  an error — adjust the prompt and retry.
