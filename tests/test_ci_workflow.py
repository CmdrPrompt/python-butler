"""Structural checks for .github/workflows/ci.yml, this repo's own PR gate."""

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def _load_workflow() -> dict:
    with WORKFLOW_PATH.open() as f:
        return yaml.safe_load(f)


def test_validate_agents_job_is_unchanged():
    jobs = _load_workflow()["jobs"]
    validate_agents = jobs["validate-agents"]

    assert validate_agents["runs-on"] == "ubuntu-latest"
    steps = validate_agents["steps"]
    assert any(step.get("uses", "").startswith("actions/checkout@") for step in steps)
    assert any(step.get("run") == "make validate-agents" for step in steps)


def test_ci_job_dogfoods_the_reusable_workflow_with_this_repos_commands():
    jobs = _load_workflow()["jobs"]
    ci_job = jobs["ci"]

    assert ci_job["uses"] == "./.github/workflows/python-ci.yml"
    with_block = ci_job["with"]
    assert with_block["install-command"] == "uv sync --extra dev"
    assert with_block["lint-command"] == "make lint"
    assert with_block["test-command"] == "make test"
    assert with_block["audit-command"] == "uv run pip-audit --progress-spinner=off"
