"""Tests for the `make worktree-clean` target (TASK-074, Requirement 12):
removes an isolated subagent worktree and its temporary branch after its
changes have been squash-merged and committed.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


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


def _run_recipe_as_shell_script(
    recipe: list[str], branch: str, cwd: Path
) -> subprocess.CompletedProcess[str]:
    """Execute the real Makefile recipe lines for `worktree-clean` as a
    shell script against `cwd`, substituting `$(b)` with `branch` the way
    `make` would. Runs the actual recipe text (not a reimplementation), so
    a change to the Makefile is exercised by this test without needing a
    real `make` invocation wired to a throwaway Makefile."""
    script = "\n".join(line.lstrip("\t").lstrip("@") for line in recipe).replace("$(b)", branch)
    # `make` collapses `$$` to a literal `$` before handing the recipe to the
    # shell; do the same here so this hermetic harness matches what `make
    # worktree-clean` would actually run.
    script = script.replace("$$", "$")
    return subprocess.run(
        ["sh", "-c", script], cwd=cwd, capture_output=True, text=True, check=False
    )


def _init_repo_with_worktree(tmp_path: Path, branch: str) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)

    worktree_path = tmp_path / "worktree"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path)],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo, worktree_path


class TestWorktreeCleanTarget:
    def test_removes_the_worktree_and_deletes_its_branch(self, tmp_path: Path) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "worktree-clean")
        branch = "worktree-agent-test"
        repo, worktree_path = _init_repo_with_worktree(tmp_path, branch)

        result = _run_recipe_as_shell_script(recipe, branch, cwd=repo)

        assert result.returncode == 0, (
            f"expected worktree-clean recipe to succeed, got rc={result.returncode}, "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"
        )
        assert not worktree_path.exists(), "expected the worktree directory to be removed"
        worktree_list = subprocess.run(
            ["git", "worktree", "list"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout
        assert str(worktree_path) not in worktree_list, (
            "expected git worktree list to no longer show the removed worktree"
        )
        branch_list = subprocess.run(
            ["git", "branch", "--list", branch],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert branch_list.strip() == "", f"expected branch {branch!r} to be deleted"

    def test_usage_message_requires_b_argument(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        target_line = next(
            line for line in makefile_text.splitlines() if re.match(r"^worktree-clean\s*:", line)
        )
        recipe = _target_recipe(makefile_text, "worktree-clean")

        assert "worktree-clean" in makefile_text.split(".PHONY:", 1)[1].split("\n\n", 1)[0], (
            "expected worktree-clean to be declared .PHONY"
        )
        assert target_line.strip() == "worktree-clean:"
        usage_lines = [line for line in recipe if "Usage: make worktree-clean" in line]
        assert usage_lines, f"expected a usage message guarding b=, got recipe: {recipe}"


class TestCommitWorkflowSkillDocumentsCleanup:
    def test_worktree_clean_documented_as_a_step_after_commit_current_task(self) -> None:
        skill_text = (_REPO_ROOT / ".claude/skills/commit-workflow/SKILL.md").read_text()
        section = skill_text.split("## Merging a worktree branch", 1)[1]
        section = section.split("\n## ", 1)[0]

        assert "worktree-clean" in section, (
            "expected the 'Merging a worktree branch' section to mention worktree-clean"
        )
        commit_index = section.index("commit-current-task")
        clean_index = section.index("worktree-clean")
        assert commit_index < clean_index, (
            "expected worktree-clean to be documented as a step after commit-current-task"
        )

    def test_worktree_clean_not_folded_into_merge_worktree_step(self) -> None:
        skill_text = (_REPO_ROOT / ".claude/skills/commit-workflow/SKILL.md").read_text()
        section = skill_text.split("## Merging a worktree branch", 1)[1]
        section = section.split("\n## ", 1)[0]
        merge_worktree_line = next(
            line for line in section.splitlines() if line.strip().startswith("1.")
        )

        assert "worktree-clean" not in merge_worktree_line, (
            "expected worktree-clean to be a separate step, not folded into the "
            f"merge-worktree step: {merge_worktree_line!r}"
        )
