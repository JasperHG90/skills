# Pre-commit

**Description:** Template for running pre-commit checks.
**Inputs:**
- `python_version`: Python version to use (default: "3.11").
- `pre_commit_version`: Pre-commit version to use (default: "4.2.0").
- `directory`: Path to directory on which to run pre-commit (default: ".").

**Example Usage:**
```yaml
- uses: our-organization/data-platform-gha-templates/actions/pre_commit@main # or use a specific release e.g. @0.0.1
  with:
    python_version: "3.9"
    directory: "."
```
