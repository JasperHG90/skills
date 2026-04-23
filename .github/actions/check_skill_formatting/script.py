import asyncio
from typing import Annotated
import pathlib as plb

import aiofiles
import typer
import rich
from jsonschema import validate


schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://agentskills.io/schemas/skill-frontmatter.json",
    "title": "Agent Skill Frontmatter",
    "description": "Schema for the YAML frontmatter of an agentskills.io SKILL.md file",
    "type": "object",
    "required": ["name", "description"],
    "properties": {
        "name": {
            "type": "string",
            "description": "The unique identifier for the skill. Must match the directory name.",
            "minLength": 1,
            "maxLength": 64,
            "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
            "examples": ["python-testing", "api-design", "data-analysis"],
        },
        "description": {
            "type": "string",
            "description": "A detailed description of what the skill does and when the agent should use it.",
            "minLength": 1,
            "maxLength": 1024,
        },
        "license": {
            "type": "string",
            "description": "The license for the skill (e.g., 'MIT', 'Apache-2.0') or a reference to a bundled LICENSE file.",
        },
        "compatibility": {
            "type": "string",
            "description": "Environment requirements such as OS, specific binaries, or network access.",
            "maxLength": 500,
        },
        "metadata": {
            "type": "object",
            "description": "Arbitrary key-value pairs for additional metadata (e.g., author, version).",
            "additionalProperties": True,
        },
        "allowed-tools": {
            "type": "array",
            "description": "A list of pre-approved tools that this skill is permitted to use (for security-conscious environments).",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": True,
}


console = rich.get_console()


app = typer.Typer(name="check_skill", help="Checks Skill frontmatter formatting")


class SkillFormattingError(Exception): ...


class SkillFrontMatterValidationError(Exception): ...


class SkillValidationError(Exception): ...


def _check_skill_dir_has_skill_md(dir: plb.Path) -> plb.Path:
    if not (dir / "SKILL.md").exists():
        raise FileNotFoundError(
            f"Skill directory '{str(dir)}' does not contain mandatory SKILL.md file. See <https://agentskills.io/specification>."
        )
    return dir / "SKILL.md"


async def _get_skill_content(skill_md_file: plb.Path) -> str:
    async with aiofiles.open(file=skill_md_file) as file:
        content = await file.read()
    return content


def _parse_frontmatter_simple(skill_md_content: str) -> dict[str, str]:
    if not skill_md_content.startswith("---"):
        raise ValueError(
            "SKILL.md file must start with YAML frontmatter metadata. See <https://agentskills.io/specification>."
        )
    fm_parsed = {}
    content_split = skill_md_content.split("---", 2)[1]
    frontmatter_raw = content_split.strip().split("\n")
    for field_and_value in frontmatter_raw:
        if field_and_value == "":
            continue
        try:
            key, value = field_and_value.strip().split(":", 1)
            fm_parsed[key.strip()] = value.strip()
        except ValueError as e:
            raise SkillFormattingError(
                "Skill frontmatter is not formatted correctly. "
                "Expecting format 'key: value' (e.g. 'name: myskill'), "
                f"got '{field_and_value.strip()}'"
            ) from e
    return fm_parsed


def _check_name_matches_skill_folder_name(skill_name: str, folder_name: str):
    if skill_name != folder_name:
        raise ValueError(
            f"'name' property in SKILL.md frontmatter must match skill folder name. "
            f"Got: 'folder_name={folder_name}' and 'skill_name={skill_name}'. See <https://agentskills.io/specification>."
        )


def _check_schema(fm: dict[str, str]) -> None:
    try:
        validate(fm, schema=schema)
    except Exception as e:
        raise SkillFrontMatterValidationError(
            "Skill frontmatter not valid. See the agent skill specification at <https://agentskills.io/specification>."
        ) from e


async def process_skill_directory(directory: plb.Path):
    resolved_skill_md_path = _check_skill_dir_has_skill_md(directory)
    frontmatter = _parse_frontmatter_simple(
        skill_md_content=(await _get_skill_content(resolved_skill_md_path))
    )
    _check_name_matches_skill_folder_name(
        frontmatter.get("name", ""), folder_name=directory.name
    )
    await asyncio.to_thread(_check_schema, frontmatter)


async def main(skill_directories: list[plb.Path]):
    for directory in skill_directories:
        try:
            await process_skill_directory(directory=directory)
        except Exception as e:
            raise SkillValidationError(f"Failed to validate '{str(directory)}'") from e


@app.command("check", help="Runs checks on (a list of) skill directories.")
def check_skill(
    skill_directories: Annotated[
        list[plb.Path],
        typer.Argument(
            ...,
            file_okay=False,
            dir_okay=True,
            exists=True,
            readable=True,
            resolve_path=True,
            help="List of file paths to skill folders that need to be validated.",
        ),
    ],
):
    try:
        asyncio.run(main(skill_directories=skill_directories))
    except Exception as e:
        console.print("Skill validation failed ...")
        raise e


if __name__ == "__main__":
    app()
