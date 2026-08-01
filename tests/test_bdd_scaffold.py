"""Characterization/acceptance tests for TASK-079 / REQUIREMENTS_BDD.md
BDD-001, BDD-002, BDD-003, BDD-016.

Exercises the real `generate-pyproject` and `generate-bdd-scaffold` Makefile
targets against a fixture consumer project vendoring this repo's Makefile
and `scaffold/` directory under `.butler/`.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
SCAFFOLD = REPO_ROOT / "scaffold"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"{cmd} in {cwd} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _build_consumer(path: Path) -> Path:
    """A consumer project vendoring this repo's Makefile + scaffold/ under .butler/."""
    path.mkdir(parents=True)
    (path / "Makefile").write_text("include .butler/Makefile\n")
    butler = path / ".butler"
    butler.mkdir()
    shutil.copy(MAKEFILE, butler / "Makefile")
    shutil.copytree(SCAFFOLD, butler / "scaffold")
    return path


class TestPyprojectScaffoldIncludesBdd:
    """Scenario: pytest-bdd is a dev dependency / testpaths includes tests/bdd/."""

    def test_pytest_bdd_is_a_dev_dependency(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        _run(["make", "generate-pyproject"], cwd=consumer)
        data = tomllib.loads((consumer / "pyproject.toml").read_text())
        assert "pytest-bdd" in data["project"]["optional-dependencies"]["dev"]

    def test_testpaths_includes_tests_bdd(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        _run(["make", "generate-pyproject"], cwd=consumer)
        data = tomllib.loads((consumer / "pyproject.toml").read_text())
        assert "tests/bdd/" in data["tool"]["pytest"]["ini_options"]["testpaths"]


class TestBddDirectorySkeleton:
    """Scenario: BDD directory skeleton exists, with example feature/step files."""

    def test_generate_bdd_scaffold_creates_directories_and_examples(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        _run(["make", "generate-bdd-scaffold"], cwd=consumer)

        features_dir = consumer / "tests" / "bdd" / "features"
        steps_dir = consumer / "tests" / "bdd" / "steps"
        assert features_dir.is_dir()
        assert steps_dir.is_dir()

        feature_files = list(features_dir.glob("*.feature"))
        assert feature_files, "expected at least one example .feature file"
        feature_text = feature_files[0].read_text()
        assert "example" in feature_files[0].name.lower() or "EXAMPLE" in feature_text
        assert "Given" in feature_text
        assert "When" in feature_text
        assert "Then" in feature_text

        step_files = list(steps_dir.glob("*.py"))
        assert step_files, "expected at least one example step definition file"
        step_text = step_files[0].read_text()
        assert "example" in step_files[0].name.lower() or "EXAMPLE" in step_text


class TestGeneratorsEmitBddAdditions:
    """Scenario: generator support so both entry points emit the BDD additions."""

    def test_init_project_calls_generate_bdd_scaffold(self) -> None:
        makefile_text = MAKEFILE.read_text()
        init_target = makefile_text.split("\ninit-project:")[1].split("\n\n")[0]
        assert "generate-bdd-scaffold" in init_target

    def test_generate_governance_files_calls_generate_bdd_scaffold(self) -> None:
        makefile_text = MAKEFILE.read_text()
        gov_target = makefile_text.split("\ngenerate-governance-files:")[1].split("\n\n")[0]
        assert "generate-bdd-scaffold" in gov_target
