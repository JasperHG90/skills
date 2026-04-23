import sys
import os

# Ensure script can be imported
sys.path.append(os.path.dirname(__file__))

import script

import pytest


@pytest.fixture
def valid_frontmatter():
    return """---
name: test-skill
description: A valid test skill description
---
"""


@pytest.fixture
def valid_skill_dir(tmp_path):
    d = tmp_path / "test-skill"
    d.mkdir()
    return d


def test_check_skill_dir_has_skill_md_exists(valid_skill_dir):
    (valid_skill_dir / "SKILL.md").touch()
    result = script._check_skill_dir_has_skill_md(valid_skill_dir)
    assert result == valid_skill_dir / "SKILL.md"


def test_check_skill_dir_has_skill_md_missing(valid_skill_dir):
    with pytest.raises(FileNotFoundError, match="does not contain mandatory SKILL.md"):
        script._check_skill_dir_has_skill_md(valid_skill_dir)


@pytest.mark.asyncio
async def test_get_skill_content(tmp_path):
    f = tmp_path / "test.md"
    content = "some content"
    f.write_text(content)
    result = await script._get_skill_content(f)
    assert result == content


def test_parse_frontmatter_simple_valid(valid_frontmatter):
    result = script._parse_frontmatter_simple(valid_frontmatter)
    assert result["name"] == "test-skill"
    assert result["description"] == "A valid test skill description"


def test_parse_frontmatter_simple_no_frontmatter():
    with pytest.raises(ValueError, match="must start with YAML frontmatter"):
        script._parse_frontmatter_simple("Just some text")


def test_parse_frontmatter_simple_malformed():
    content = """---
name
---"""
    with pytest.raises(
        script.SkillFormattingError, match="Expecting format 'key: value'"
    ):
        script._parse_frontmatter_simple(content)


def test_check_name_matches_skill_folder_name_match():
    # Should not raise
    script._check_name_matches_skill_folder_name("my-skill", "my-skill")


def test_check_name_matches_skill_folder_name_mismatch():
    with pytest.raises(ValueError, match="must match skill folder name"):
        script._check_name_matches_skill_folder_name("my-skill", "other-folder")


def test_check_schema_valid():
    data = {"name": "valid-skill", "description": "Valid description"}
    script._check_schema(data)


def test_check_schema_invalid_missing_field():
    data = {
        "name": "valid-skill"
        # missing description
    }
    with pytest.raises(
        script.SkillFrontMatterValidationError, match="Skill frontmatter not valid"
    ):
        script._check_schema(data)


def test_check_schema_invalid_pattern():
    data = {"name": "Invalid Name", "description": "Valid description"}
    with pytest.raises(script.SkillFrontMatterValidationError):
        script._check_schema(data)


@pytest.mark.asyncio
async def test_process_skill_directory_success(valid_skill_dir, valid_frontmatter):
    (valid_skill_dir / "SKILL.md").write_text(valid_frontmatter)

    # Should run without error
    await script.process_skill_directory(valid_skill_dir)


@pytest.mark.asyncio
async def test_process_skill_directory_failure(valid_skill_dir):
    # No SKILL.md
    with pytest.raises(FileNotFoundError):
        await script.process_skill_directory(valid_skill_dir)


@pytest.mark.asyncio
async def test_main_success(valid_skill_dir, valid_frontmatter):
    (valid_skill_dir / "SKILL.md").write_text(valid_frontmatter)

    # Should run without error
    await script.main([valid_skill_dir])


@pytest.mark.asyncio
async def test_main_failure(valid_skill_dir):
    # No SKILL.md
    with pytest.raises(script.SkillValidationError, match="Could not validate skill"):
        await script.main([valid_skill_dir])
