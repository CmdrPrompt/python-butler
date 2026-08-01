"""Structural checks for the reusable .github/workflows/python-ci.yml.

These validate the workflow_call input contract and step ordering that
consumer repos (e.g. firefly-bank-importer) depend on, since the workflow
itself can only be exercised end-to-end by GitHub Actions.
"""

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "python-ci.yml"


def _load_workflow() -> dict:
    # PyYAML parses the bare `on:` key as boolean True; work around by
    # re-keying it back to the string "on" for lookups below.
    with WORKFLOW_PATH.open() as f:
        data = yaml.safe_load(f)
    if True in data:
        data["on"] = data.pop(True)
    return data


def test_workflow_is_triggered_by_workflow_call():
    workflow = _load_workflow()
    assert "workflow_call" in workflow["on"]


def test_workflow_declares_the_existing_consumer_input_contract():
    inputs = _load_workflow()["on"]["workflow_call"]["inputs"]

    required = {"python-version", "install-command", "lint-command", "test-command"}
    for name in required:
        assert inputs[name]["required"] is True

    assert inputs["audit-command"]["required"] is False


def test_job_runs_checkout_setup_install_lint_test_audit_as_separate_steps():
    jobs = _load_workflow()["jobs"]
    ((_, job),) = jobs.items()
    steps = job["steps"]

    uses = [step.get("uses", "") for step in steps]
    assert any(u.startswith("actions/checkout@") for u in uses)
    assert any(u.startswith("actions/setup-python@") for u in uses)

    names = [step.get("name") for step in steps]
    assert names.index("Install") < names.index("Lint") < names.index("Test")

    install_step = steps[names.index("Install")]
    lint_step = steps[names.index("Lint")]
    test_step = steps[names.index("Test")]

    assert install_step["run"] == "${{ inputs.install-command }}"
    assert lint_step["run"] == "${{ inputs.lint-command }}"
    assert test_step["run"] == "${{ inputs.test-command }}"

    for step in (install_step, lint_step, test_step):
        assert "||" not in step["run"]


def test_uv_is_set_up_before_install():
    jobs = _load_workflow()["jobs"]
    ((_, job),) = jobs.items()
    steps = job["steps"]

    uses = [step.get("uses", "") for step in steps]
    setup_uv_index = next(i for i, u in enumerate(uses) if u.startswith("astral-sh/setup-uv@"))

    names = [step.get("name") for step in steps]
    setup_python_index = names.index("Set up Python")
    install_index = names.index("Install")

    assert setup_python_index < setup_uv_index < install_index


def test_audit_step_is_conditional_and_does_not_swallow_failures():
    jobs = _load_workflow()["jobs"]
    ((_, job),) = jobs.items()
    steps = job["steps"]

    names = [step.get("name") for step in steps]
    audit_step = steps[names.index("Audit")]

    assert "if" in audit_step
    assert audit_step["run"] == "${{ inputs.audit-command }}"
    assert "||" not in audit_step["run"]
