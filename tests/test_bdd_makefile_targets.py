"""Tests for TASK-080 / REQUIREMENTS_BDD.md BDD-010..013, BDD-050: the `bdd`
and `bdd-missing` Makefile targets, their `make help` listing, and graceful
degradation when a project has not adopted `tests/bdd/`.

Follows the text-parsing convention established by
test_makefile_cli_flag_drift.py for recipe assertions, and the consumer
fixture from test_projects_makefile_integration.py for the functional
degrade-gracefully checks (which don't require a BDD-capable venv).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MAKEFILE = _REPO_ROOT / "Makefile"
_SCAFFOLD = _REPO_ROOT / "scaffold"


def _target_recipe(makefile_text: str, target: str) -> list[str]:
    """Return the recipe lines (tab-indented lines) belonging to `target:`,
    up to the next unindented line."""
    lines = makefile_text.splitlines()
    recipe: list[str] = []
    capturing = False
    target_re = re.compile(rf"^{re.escape(target)}\s*:")
    for line in lines:
        if target_re.match(line):
            capturing = True
            continue
        if capturing:
            if line.startswith("\t"):
                recipe.append(line)
            elif line.strip() == "":
                continue
            else:
                break
    return recipe


def _build_consumer(path: Path, with_scaffold: bool = False) -> Path:
    """A consumer project vendoring this repo's Makefile under .butler/,
    without a tests/bdd/ directory."""
    path.mkdir(parents=True)
    (path / "Makefile").write_text("include .butler/Makefile\n")
    butler = path / ".butler"
    butler.mkdir()
    shutil.copy(_MAKEFILE, butler / "Makefile")
    if with_scaffold:
        shutil.copytree(_SCAFFOLD, butler / "scaffold")
    return path


class TestBddTargetRecipe:
    """Scenario: make bdd runs pytest tests/bdd/ verbosely."""

    def test_bdd_target_runs_pytest_against_bdd_dir_verbosely(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "bdd")
        pytest_lines = [line for line in recipe if "pytest" in line and "bdd" in line]
        assert pytest_lines, f"expected a pytest tests/bdd/ invocation in bdd recipe, got: {recipe}"
        assert "-v" in pytest_lines[0], (
            f"expected verbose pytest invocation, got: {pytest_lines[0]!r}"
        )

    def test_bdd_target_does_not_suppress_pytest_failures(self) -> None:
        """A failing scenario must cause `make bdd` to exit non-zero, so the
        pytest line must not be prefixed with '-' or followed by '|| true'."""
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "bdd")
        pytest_lines = [line for line in recipe if "pytest" in line and "bdd" in line]
        assert pytest_lines, f"expected a pytest tests/bdd/ invocation in bdd recipe, got: {recipe}"
        stripped = pytest_lines[0].strip().lstrip("@")
        assert not stripped.startswith("-"), f"pytest line must not suppress failures: {stripped!r}"
        assert "|| true" not in stripped, f"pytest line must not suppress failures: {stripped!r}"


class TestBddMissingTargetRecipe:
    """Scenario: make bdd-missing lists unbound scenarios and exits non-zero."""

    def test_bdd_missing_target_invokes_pytest_against_bdd_dir(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "bdd-missing")
        pytest_lines = [line for line in recipe if "pytest" in line and "bdd" in line]
        assert pytest_lines, (
            f"expected a pytest tests/bdd/ invocation in bdd-missing recipe, got: {recipe}"
        )

    def test_bdd_missing_target_exits_non_zero_when_steps_are_missing(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "bdd-missing")
        assert any("exit 1" in line for line in recipe), (
            f"expected bdd-missing to exit 1 when unbound scenarios are found, got: {recipe}"
        )


class TestHelpListsBddTargets:
    """Scenario: make help shows bdd and bdd-missing descriptions."""

    def test_help_lists_bdd_with_a_description(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "help")
        bdd_lines = [line for line in recipe if re.search(r"make bdd\b", line)]
        assert bdd_lines, f"expected 'make bdd' to be listed in help output, got: {recipe}"
        assert "--" in bdd_lines[0], f"expected a one-line description, got: {bdd_lines[0]!r}"

    def test_help_lists_bdd_missing_with_a_description(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "help")
        bdd_missing_lines = [line for line in recipe if "make bdd-missing" in line]
        assert bdd_missing_lines, (
            f"expected 'make bdd-missing' to be listed in help output, got: {recipe}"
        )
        assert "--" in bdd_missing_lines[0], (
            f"expected a one-line description, got: {bdd_missing_lines[0]!r}"
        )


class TestMakeTestIncludesBddScenarios:
    """Scenario: make test includes BDD scenarios (BDD-011) — tests/bdd/ is
    nested under $(TESTS_DIR), so the existing `test` target's pytest
    invocation already walks it; this pins that invariant."""

    def test_test_target_search_path_is_a_parent_of_the_bdd_scaffold_dir(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "test")
        pytest_lines = [line for line in recipe if "pytest" in line]
        assert pytest_lines, f"expected a pytest invocation in the test recipe, got: {recipe}"
        assert "$(TESTS_DIR)/" in pytest_lines[0], (
            f"expected test target to walk $(TESTS_DIR)/, got: {pytest_lines[0]!r}"
        )

    def test_bdd_scaffold_is_generated_under_tests_dir(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer", with_scaffold=True)
        result = subprocess.run(
            ["make", "generate-bdd-scaffold"], cwd=consumer, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        bdd_dir = consumer / "tests" / "bdd"
        assert bdd_dir.is_dir()


class TestBddDegradesGracefullyWithoutBddDir:
    """Scenario: make bdd degrades gracefully without tests/bdd/."""

    def test_bdd_prints_adoption_hint_and_exits_zero(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        result = subprocess.run(["make", "bdd"], cwd=consumer, capture_output=True, text=True)
        detail = f"got {result.returncode}:\n{result.stdout}{result.stderr}"
        assert result.returncode == 0, f"expected exit 0 without tests/bdd/, {detail}"
        assert (result.stdout + result.stderr).strip(), "expected an adoption hint message"

    def test_bdd_missing_prints_adoption_hint_and_exits_zero(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        result = subprocess.run(
            ["make", "bdd-missing"], cwd=consumer, capture_output=True, text=True
        )
        detail = f"got {result.returncode}:\n{result.stdout}{result.stderr}"
        assert result.returncode == 0, f"expected exit 0 without tests/bdd/, {detail}"
        assert (result.stdout + result.stderr).strip(), "expected an adoption hint message"
