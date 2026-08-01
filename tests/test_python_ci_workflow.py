"""Structural checks for the reusable .github/workflows/python-ci.yml.

These validate the workflow_call input contract and job structure that
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


def _step(job: dict, name: str) -> dict:
    steps = job["steps"]
    names = [step.get("name") for step in steps]
    return steps[names.index(name)]


def _step_uses(job: dict, prefix: str) -> dict:
    return next(step for step in job["steps"] if step.get("uses", "").startswith(prefix))


def test_workflow_is_triggered_by_workflow_call():
    workflow = _load_workflow()
    assert "workflow_call" in workflow["on"]


def test_workflow_declares_the_existing_consumer_input_contract():
    inputs = _load_workflow()["on"]["workflow_call"]["inputs"]

    required = {"python-version", "install-command", "lint-command", "test-command"}
    for name in required:
        assert inputs[name]["required"] is True

    assert inputs["audit-command"]["required"] is False


def test_jobs_are_install_lint_test_audit_needs_chained():
    jobs = _load_workflow()["jobs"]

    assert set(jobs.keys()) == {"install", "lint", "test", "audit"}
    assert jobs["lint"]["needs"] == "install"
    assert jobs["test"]["needs"] == "lint"
    assert jobs["audit"]["needs"] == "test"


def test_each_job_checks_out_submodules_and_sets_up_cached_uv():
    jobs = _load_workflow()["jobs"]

    for job in jobs.values():
        checkout_step = _step_uses(job, "actions/checkout@")
        assert checkout_step["with"]["submodules"] is True

        setup_uv_step = _step_uses(job, "astral-sh/setup-uv@")
        assert setup_uv_step["with"]["enable-cache"] is True

        assert _step(job, "Install")["run"] == "${{ inputs.install-command }}"


def test_each_job_runs_its_own_command_after_install():
    jobs = _load_workflow()["jobs"]

    for job_name, command_step_name, input_name in [
        ("lint", "Lint", "lint-command"),
        ("test", "Test", "test-command"),
        ("audit", "Audit", "audit-command"),
    ]:
        job = jobs[job_name]
        names = [step.get("name") for step in job["steps"]]
        assert names.index("Install") < names.index(command_step_name)

        command_step = _step(job, command_step_name)
        assert command_step["run"] == "${{ inputs." + input_name + " }}"
        assert "||" not in command_step["run"]


def test_audit_job_is_conditional_and_does_not_swallow_failures():
    audit_job = _load_workflow()["jobs"]["audit"]
    audit_step = _step(audit_job, "Audit")

    assert "if" in audit_step
    assert audit_step["run"] == "${{ inputs.audit-command }}"
    assert "||" not in audit_step["run"]
