"""TASK-098: binds TASK-098-upgrade-vulnerable-locked-dependencies.feature.

These scenarios call the network (pip-audit, pre-commit) and are slow.

@AC-3 deliberately does not shell out to `make test` or `make bdd`: that
would re-enter this very test run and recurse forever. Those two gates are
verified by the task gate itself (`make lint && make test && make bdd`
must pass for the task to complete). Here we check the parts that cannot
recurse: `make lint`, the pre-commit hooks and that `uv.lock` is consistent.

@AC-4 checks only what stays true after merge (the affected packages are at
or above their fixed versions). That nothing else changed is a one-off review
check against the pre-upgrade lockfile, recorded in the task's Completion.
"""

import json
import subprocess  # nosec B404 - test helper runs fixed local commands
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version
from pytest_bdd import given, scenarios, then, when

scenarios("../features/TASK-098-upgrade-vulnerable-locked-dependencies.feature")

REPO_ROOT = Path(__file__).resolve().parents[3]
AFFECTED = {"virtualenv", "filelock", "urllib3", "certifi", "msgpack"}
LOCAL_PACKAGE = "butler-core"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument lists, no shell
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )


def _lock_versions(text: str) -> dict[str, str]:
    data = tomllib.loads(text)
    return {p["name"]: p.get("version", "") for p in data["package"]}


@pytest.fixture(scope="module")
def audit_run() -> dict:
    proc = _run(["uv", "run", "pip-audit", "--progress-spinner=off", "-f", "json"])
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {"dependencies": [], "unparsed": proc.stdout + proc.stderr}
    return {"returncode": proc.returncode, "report": report, "stderr": proc.stderr}


@pytest.fixture
def audit_result(audit_run) -> dict:
    return audit_run


@given("the packages pinned in `uv.lock`")
def _locked_packages():
    assert (REPO_ROOT / "uv.lock").is_file()


@given("the packages pinned in `uv.lock`, including the local package `butler-core`")
def _locked_packages_with_local():
    assert LOCAL_PACKAGE in _lock_versions((REPO_ROOT / "uv.lock").read_text())


@given("the upgraded `uv.lock`")
def _upgraded_lock():
    assert (REPO_ROOT / "uv.lock").is_file()


@when("the dependency audit `uv run pip-audit --progress-spinner=off` runs")
def _audit_runs(audit_result):
    return audit_result


@when("the dependency audit runs")
def _audit_runs_short(audit_result):
    return audit_result


@then("no known vulnerabilities are reported")
def _no_vulns(audit_result):
    vulns = {
        f"{d['name']} {d['version']}: {v['id']}"
        for d in audit_result["report"]["dependencies"]
        for v in d.get("vulns", [])
    }
    assert not vulns, f"{len(vulns)} known vulnerabilities: {sorted(vulns)}"


@then("the audit exits 0")
def _audit_exit_zero(audit_result):
    assert audit_result["returncode"] == 0, audit_result["stderr"]


@then('`butler-core` is listed under "Skip" as not found on PyPI')
def _butler_core_skipped(audit_result):
    skipped = {d["name"] for d in audit_result["report"]["dependencies"] if "skip_reason" in d}
    assert LOCAL_PACKAGE in skipped


@then('no other package is listed under "Skip"')
def _only_local_skipped(audit_result):
    skipped = {d["name"] for d in audit_result["report"]["dependencies"] if "skip_reason" in d}
    assert skipped - {LOCAL_PACKAGE} == set()


_gate_results: dict[str, subprocess.CompletedProcess[str]] = {}


@when("`make lint`, `make test`, `make bdd` and the pre-commit hooks run")
def _gates_run():
    # `make test` and `make bdd` are intentionally not run here (would recurse
    # into this test run); the task gate verifies them.
    _gate_results["lint"] = _run(["make", "lint"])
    _gate_results["pre-commit"] = _run(["uv", "run", "pre-commit", "run", "--all-files"])
    _gate_results["lock"] = _run(["uv", "lock", "--check"])


@then("each of them passes")
def _gates_pass():
    failed = {k: (v.stdout + v.stderr)[-2000:] for k, v in _gate_results.items() if v.returncode}
    assert not failed, failed


@when("the locked versions of the affected packages are read", target_fixture="lock_versions")
def _current_lock():
    return _lock_versions((REPO_ROOT / "uv.lock").read_text())


@then("each affected package is locked at or above its first fixed version")
def _at_or_above_fixed(lock_versions, datatable):
    header, *rows = datatable
    assert header == ["package", "fixed version"]
    assert {name for name, _ in rows} == AFFECTED
    too_old = {
        name: lock_versions.get(name)
        for name, fixed in rows
        if Version(lock_versions.get(name, "0")) < Version(fixed)
    }
    assert not too_old, f"locked below the first fixed version: {too_old}"
