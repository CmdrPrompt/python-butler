"""Acceptance tests for TASK-094 / REQUIREMENTS_AGENT_SKILLS.md Requirement 2.

`make lint-quiet`, `make test-quiet`, `make bdd-quiet` and the combined
`make verify` must run the same underlying checks as `make lint`, `make
test` and `make bdd` but print only what a failure needs. The verbose
targets must keep their exact current output.

`test-quiet`/`bdd-quiet`/`verify` are never invoked here against this
repo's own suite: `test-quiet` and `verify` both run `pytest tests/`, and
this file lives under `tests/` — shelling out to them from inside a test
collected by that very run would recurse without bound (see
`test_no_make_recursion.py` for the sibling concern with the `butler`
CLI). The pytest-flag behavior they rely on is instead proven directly,
via a synthetic scratch project pytest is invoked against outside `make`.
`lint-quiet` does not run pytest, so it is exercised directly against this
repo.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# The verbosity knobs `test-quiet`/`lint-quiet`/`bdd-quiet` set via `$(MAKE)
# ... VAR=value` command-line overrides, which Make auto-exports to the
# environment of everything that recipe spawns -- including, when this test
# module runs nested inside `make test-quiet` (e.g. via `make verify`), this
# very subprocess. Stripped before every dry run below so the comparison is
# hermetic regardless of how this test file itself was invoked.
_VERBOSITY_ENV_VARS = (
    "PYTEST_COV_REPORT",
    "PYTEST_EXTRA_FLAGS",
    "RUFF_QUIET",
    "MYPY_QUIET",
    "BANDIT_QUIET",
    "COMPLEXIPY_QUIET",
    "BDD_QUIET",
    # Make re-derives command-line variable overrides from MAKEFLAGS/MFLAGS in
    # every nested `make` invocation, independently of the plain environment
    # variables above -- both must be stripped for the same reason.
    "MAKEFLAGS",
    "MFLAGS",
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MAKEFILE = _REPO_ROOT / "Makefile"
_BUNDLED_MAKEFILE = _REPO_ROOT / "src" / "butler_core" / "data" / "Makefile"
_IMPL_WORKER_CLAUDE = _REPO_ROOT / ".claude" / "agents" / "implementation-worker.agent.md"
_IMPL_WORKER_SHARED = _REPO_ROOT / "claude-agents" / "implementation-worker.agent.md"


def _target_recipe(makefile_text: str, target: str) -> list[str]:
    """Return the recipe lines (tab-indented lines) belonging to `target:`,
    up to the next unindented line. Matches the convention established by
    test_bdd_makefile_targets.py."""
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


def _normalize(line: str) -> str:
    """Collapse runs of whitespace so an empty-variable expansion (e.g.
    `$(RUFF_QUIET)` -> "") doesn't register as a command-line diff."""
    return re.sub(r"\s+", " ", line).strip()


class TestTestQuietPytestFlags:
    """Scenario 1: the quiet test target keeps the coverage total but drops
    fully-covered files and individual passing test names. Scenario 4: a
    failing check is still identifiable in quiet output.

    Exercised against a synthetic scratch project with `uv run python -m
    pytest` directly (not `make test-quiet`), so this never touches the
    real `tests/` collection — see the module docstring."""

    def _scratch_project(self, tmp_path: Path) -> Path:
        project = tmp_path / "scratch"
        pkg = project / "src" / "pkg"
        tests = project / "tests"
        pkg.mkdir(parents=True)
        tests.mkdir(parents=True)
        (pkg / "__init__.py").write_text(
            "def partially_covered():\n    return 1\n\n\ndef never_called():\n    return 2\n"
        )
        (pkg / "full.py").write_text("def always():\n    return 42\n")
        (tests / "test_x.py").write_text(
            "from pkg import partially_covered\n"
            "from pkg.full import always\n\n\n"
            "def test_partially_covered():\n"
            "    assert partially_covered() == 1\n\n\n"
            "def test_full():\n"
            "    assert always() == 42\n"
        )
        return project

    def _run_quiet(self, project: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=src/pkg",
                "--cov-report=term:skip-covered",
                "-q",
                "--no-header",
                "--tb=short",
            ],
            cwd=project,
            env={"PYTHONPATH": "src", "PATH": __import__("os").environ["PATH"]},
            capture_output=True,
            text=True,
        )

    def test_keeps_total_row_drops_full_file_and_passing_test_names(self, tmp_path: Path) -> None:
        project = self._scratch_project(tmp_path)

        result = self._run_quiet(project)

        assert result.returncode == 0, result.stdout + result.stderr
        assert "TOTAL" in result.stdout
        assert "full.py" not in result.stdout, (
            "a 100%-covered file must be omitted by --cov-report=term:skip-covered"
        )
        assert "test_partially_covered" not in result.stdout, (
            "-q must suppress individual passing test names"
        )
        assert "test_full" not in result.stdout

    def test_failing_test_is_still_named_in_quiet_output(self, tmp_path: Path) -> None:
        project = self._scratch_project(tmp_path)
        (project / "tests" / "test_fail.py").write_text(
            "def test_will_fail():\n    assert 1 == 2\n"
        )

        result = self._run_quiet(project)

        assert result.returncode != 0
        assert "test_fail.py" in result.stdout
        assert "test_will_fail" in result.stdout


class TestLintQuietDropsPerFunctionComplexityListing:
    """Scenario 2: the quiet lint target drops the per-function complexity
    listing. Safe to run directly against this repo -- `lint` never invokes
    pytest, so there is no recursion risk."""

    def test_lint_quiet_passes_and_omits_function_score_lines(self) -> None:
        clean_env = {k: v for k, v in os.environ.items() if k not in _VERBOSITY_ENV_VARS}
        result = subprocess.run(
            ["make", "lint-quiet"], cwd=_REPO_ROOT, env=clean_env, capture_output=True, text=True
        )

        assert result.returncode == 0, result.stdout + result.stderr
        combined = result.stdout + result.stderr
        assert "No functions were found with complexity greater than 15." in combined
        # A verbose `make lint` run lists every analysed function with a
        # "<name> <score>  PASSED" row (see complexipy's `-s desc` output);
        # none of those rows may appear on success in the quiet variant.
        assert "PASSED" not in combined


class TestBddQuietRecipe:
    """Scenario 3: the quiet BDD target drops passing scenario names.

    Verified statically: `bdd-quiet` delegates to `bdd` with `BDD_QUIET=1`,
    and `bdd`'s own recipe switches from `-v` (prints every passing
    scenario) to `-q --no-header --tb=short` (suppresses them) based on
    that variable. Not run dynamically here: a real `tests/bdd/` run needs
    a scaffolded consumer project outside this repo's own venv, which the
    existing BDD Makefile tests (test_bdd_makefile_targets.py) already
    establish is impractical without a real `uv`-managed environment."""

    def test_bdd_quiet_delegates_with_bdd_quiet_flag(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "bdd-quiet")
        joined = " ".join(recipe)
        assert "$(MAKE) bdd" in joined
        assert "BDD_QUIET=1" in joined

    def test_bdd_recipe_switches_pytest_verbosity_on_bdd_quiet(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        recipe = _target_recipe(makefile_text, "bdd")
        pytest_lines = [line for line in recipe if "pytest" in line and "bdd" in line]
        assert pytest_lines, f"expected a pytest tests/bdd/ invocation, got: {recipe}"
        line = pytest_lines[0]
        assert "$(BDD_QUIET)" in line
        assert "-q --no-header --tb=short" in line
        assert "-v" in line


class TestVerifyRunsAllThreeChecks:
    """Scenario 5: one combined target runs every check."""

    def test_verify_depends_on_all_three_quiet_targets(self) -> None:
        makefile_text = _MAKEFILE.read_text()
        verify_line = next(
            line for line in makefile_text.splitlines() if line.startswith("verify:")
        )
        prerequisites = verify_line.split(":", 1)[1].split()
        assert set(prerequisites) == {"lint-quiet", "test-quiet", "bdd-quiet"}


class TestVerboseTargetsUnchanged:
    """Scenario 6: the verbose targets are unchanged -- `make -n lint`,
    `make -n test` and `make -n bdd` expand to the same command lines
    (ignoring incidental whitespace from now-empty verbosity variables) as
    before the quiet variants were introduced.

    Compared against `tests/fixtures/Makefile.baseline`, a checked-in copy
    of the Makefile from commit 64ae502 (the TASK-092 merge, parent of
    TASK-093/094) -- not fetched via `git show` against that commit, since
    CI checks out with `fetch-depth: 1` and the commit is unavailable in a
    shallow clone."""

    _BASELINE_MAKEFILE = _REPO_ROOT / "tests" / "fixtures" / "Makefile.baseline"

    def _dry_run(self, makefile: Path, target: str) -> list[str]:
        clean_env = {k: v for k, v in os.environ.items() if k not in _VERBOSITY_ENV_VARS}
        result = subprocess.run(
            ["make", "-n", "-f", str(makefile), target],
            cwd=_REPO_ROOT,
            env=clean_env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        return [_normalize(line) for line in result.stdout.splitlines() if line.strip()]

    def test_lint_test_bdd_dry_run_unchanged_from_baseline(self) -> None:
        for target in ("lint", "test", "bdd"):
            current = self._dry_run(_MAKEFILE, target)
            baseline = self._dry_run(self._BASELINE_MAKEFILE, target)
            assert current == baseline, f"`make -n {target}` drifted from baseline:\n{current}"


class TestVendoredMakefileDoesNotDrift:
    """Scenario 7: the vendored Makefile copy does not drift."""

    def test_bundled_makefile_matches_root_makefile(self) -> None:
        assert _BUNDLED_MAKEFILE.read_text() == _MAKEFILE.read_text(), (
            "src/butler_core/data/Makefile has drifted from the repo root Makefile -- "
            "re-copy the root Makefile into src/butler_core/data/Makefile"
        )


class TestImplementationWorkerUsesQuietTargets:
    """Scenario 8: the Implementation Worker uses the quiet targets."""

    def test_verify_named_as_completion_gate_and_test_quiet_in_tdd_loop(self) -> None:
        text = _IMPL_WORKER_CLAUDE.read_text()
        assert "make verify" in text
        assert "make test-quiet" in text
        assert "| tail" in text and "| head" in text and "| grep" in text, (
            "the rule forbidding shell pipes to shorten output must still be present"
        )

    def test_claude_agents_and_shared_copy_are_byte_identical(self) -> None:
        assert _IMPL_WORKER_CLAUDE.read_text() == _IMPL_WORKER_SHARED.read_text()
