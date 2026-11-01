"""Git/gh workflow operations extracted from Makefile targets, operating on Task objects."""

from __future__ import annotations

import subprocess  # nosec B404 -- used only to invoke fixed git/gh CLI commands
from pathlib import Path

from butler_core.tasks import DEFAULT_TASKS_DIR, Task, TaskNotFoundError

_EXCLUDED_DIR_PREFIXES = (".venv/", ".butler/.github/", "libs/", ".claude/")


class GitOpsError(RuntimeError):
    """Raised when a git/gh operation fails in a way the Makefile also treats as fatal."""


def _branch_exists(branch: str) -> bool:
    result = subprocess.run(  # nosec B603 B607 -- fixed git CLI invocation, no shell/user input
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
    )
    return result.returncode == 0


def branch_for(task: Task) -> None:
    """Create or switch to the task's branch, matching Makefile `branch-task`."""
    branch = task.branch_name
    if _branch_exists(branch):
        subprocess.run(["git", "checkout", branch], check=True)  # nosec B603 B607
    else:
        subprocess.run(["git", "fetch", "origin", "main"], check=True)  # nosec B603 B607
        subprocess.run(  # nosec B603 B607
            ["git", "checkout", "-b", branch, "origin/main"], check=True
        )


def _markdown_files(root: Path) -> list[str]:
    files = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in _EXCLUDED_DIR_PREFIXES):
            continue
        files.append(f"./{rel}")
    return files


def stage_for(task: Task, repo_root: Path | None = None) -> None:
    """Fix, format, and stage files for a task, matching Makefile `stage-task`."""
    root = repo_root or Path.cwd()
    subprocess.run(  # nosec B603 B607
        ["uv", "run", "ruff", "check", "--fix", "."], check=True, cwd=root
    )
    subprocess.run(["uv", "run", "ruff", "format", "."], check=True, cwd=root)  # nosec B603 B607
    md_files = _markdown_files(root)
    subprocess.run(  # nosec B603 B607
        [
            "uv",
            "run",
            "pymarkdown",
            "--config",
            ".pymarkdown",
            "--return-code-scheme",
            "minimal",
            "fix",
            *md_files,
        ],
        check=True,
        cwd=root,
    )
    subprocess.run(  # nosec B603 B607 -- fixed git CLI invocation; paths are data, never shell text
        ["git", "add", *task.stage_paths], check=True, cwd=root
    )
    subprocess.run(  # nosec B603 B607
        ["git", "update-index", "-q", "--refresh"], check=True, cwd=root
    )


def commit_for(task: Task) -> None:
    """Commit using the task's commit message, matching Makefile `commit-task`."""
    subprocess.run(  # nosec B603 B607
        ["git", "commit", "-m", task.commit_message], check=True
    )


def _find_task_file(task_id: str, tasks_dir: str) -> Path:
    matches = sorted(Path(tasks_dir).glob(f"{task_id}*.md"))
    if not matches:
        raise TaskNotFoundError(f"No task file found matching '{task_id}' in {tasks_dir}")
    return matches[0]


def _pr_body(text: str) -> str:
    lines = text.splitlines()
    body_lines: list[str] = []
    capturing = False
    for line in lines:
        if line.startswith("## Description"):
            capturing = True
        elif line.startswith("## Completion"):
            break
        if capturing:
            body_lines.append(line)
    return "\n".join(body_lines)


def open_pr_for(task: Task, tasks_dir: str = DEFAULT_TASKS_DIR) -> None:
    """Push the branch and open a PR, matching Makefile `pr-task`."""
    path = _find_task_file(task.id, tasks_dir)
    title = f"{task.id} {task.title}"
    body = _pr_body(path.read_text())
    subprocess.run(["git", "push", "-u", "origin", "HEAD"], check=True)  # nosec B603 B607
    subprocess.run(  # nosec B603 B607
        ["gh", "pr", "create", "--title", title, "--body", body, "--base", "main"],
        check=True,
    )


def _one_line(stderr: object) -> str:
    return " ".join(str(stderr or "").split()) or "no error output"


def _git_after_merge(*args: str, ok_codes: tuple[int, ...] = (0,)) -> int:
    """Run a git command after the merge; a failure becomes a one-line GitOpsError."""
    cmd = f"git {' '.join(args)}"
    try:
        result = subprocess.run(  # nosec B603 B607 -- fixed git CLI invocation
            ["git", *args], check=False, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as exc:
        raise GitOpsError(f"PR was merged, but '{cmd}' failed: {_one_line(exc.stderr)}") from exc
    if result.returncode not in ok_codes:
        raise GitOpsError(f"PR was merged, but '{cmd}' failed: {_one_line(result.stderr)}")
    return int(result.returncode)


def _update_local_main(head_sha: str) -> None:
    """Bring local main in line with origin/main after the squash merge (Requirement 19)."""
    _git_after_merge("checkout", "main")
    _git_after_merge("fetch", "origin", "main")
    # Exit 0: local main has no commits missing from origin/main; 1: it has local-only ones.
    if _git_after_merge("merge-base", "--is-ancestor", "main", "origin/main", ok_codes=(0, 1)) == 0:
        _git_after_merge("pull", "--ff-only")
        return
    # Local-only commits: safe to drop only when the merged PR already contains them all.
    if _git_after_merge("merge-base", "--is-ancestor", "main", head_sha, ok_codes=(0, 1)) == 1:
        raise GitOpsError(
            "PR was merged, but local main has unpushed commits that are not in the PR; "
            "local main was left unchanged. Review them with "
            "'git log origin/main..main', then run 'git rebase origin/main' to keep them "
            "or 'git reset --keep origin/main' to drop them"
        )
    _git_after_merge("reset", "--keep", "origin/main")


def merge_pr_for(task: Task) -> None:
    """Squash-merge the task's open PR and update main, matching Makefile `merge-pr`."""
    branch = task.branch_name
    list_result = subprocess.run(  # nosec B603 B607
        ["gh", "pr", "list", "--head", branch, "--json", "number", "--jq", ".[0].number"],
        check=True,
        capture_output=True,
        text=True,
    )
    pr = list_result.stdout.strip()
    if not pr:
        raise GitOpsError(f"No open PR for branch {branch}")

    view_result = subprocess.run(  # nosec B603 B607
        ["gh", "pr", "view", pr, "--json", "mergeable", "--jq", ".mergeable"],
        check=True,
        capture_output=True,
        text=True,
    )
    state = view_result.stdout.strip()
    if state != "MERGEABLE":
        raise GitOpsError(f"PR #{pr} not mergeable ({state})")

    # Captured before the merge: --delete-branch removes the branch the SHA is read from.
    head_result = subprocess.run(  # nosec B603 B607
        ["gh", "pr", "view", pr, "--json", "headRefOid", "--jq", ".headRefOid"],
        check=True,
        capture_output=True,
        text=True,
    )
    head_sha = head_result.stdout.strip()

    subprocess.run(  # nosec B603 B607
        ["gh", "pr", "merge", pr, "--squash", "--delete-branch"], check=True
    )
    _update_local_main(head_sha)
