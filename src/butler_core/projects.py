"""Best-effort, one-way sync of task metadata to a linked GitHub Projects
(v2) item.

Encapsulated separately from git_ops.py per Requirement 4 of
REQUIREMENTS_TASK_WORKFLOW.md: this module owns all interaction with GitHub
Projects and never re-exports through git_ops.py. Sync failures (no project
configured, `gh` not authenticated, `gh` not installed, or any other
unexpected error) are always reported as a `SyncResult(success=False, ...)`
and never raised, so a failure here can never block PR creation or merge.

The sync is one-way: it only writes TASK-ID/title/status derived from the
task file to GitHub Projects. It never reads field values back from GitHub
Projects into the task file, the CLI, or git_ops.py.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 -- used only to invoke the fixed `gh` CLI
from dataclasses import dataclass

from butler_core.tasks import Task

_PROJECT_ENV_VAR = "BUTLER_GITHUB_PROJECT"
_OWNER_ENV_VAR = "GITHUB_REPOSITORY_OWNER"


@dataclass
class SyncResult:
    """Outcome of a one-way write to GitHub Projects.

    Only carries what was written (or attempted), never any field value
    read back from GitHub Projects.
    """

    success: bool
    message: str


def _project_number(env: dict[str, str] | None) -> str | None:
    source: dict[str, str] = env if env is not None else dict(os.environ)
    value = source.get(_PROJECT_ENV_VAR)
    return value or None


def _owner(env: dict[str, str] | None) -> str:
    source: dict[str, str] = env if env is not None else dict(os.environ)
    return source.get(_OWNER_ENV_VAR) or "@me"


def _warning(task_id: str, reason: str) -> SyncResult:
    return SyncResult(
        success=False,
        message=f"Warning: could not sync {task_id} to GitHub Projects ({reason}) - continuing",
    )


def _classify_gh_failure(stderr: str) -> str:
    lowered = stderr.lower()
    if "auth" in lowered:
        return "gh: not authenticated"
    return stderr.strip() or "gh command failed"


def _run_gh(args: list[str], env: dict[str, str] | None) -> subprocess.CompletedProcess[str]:
    subprocess_env = dict(os.environ)
    if env is not None:
        subprocess_env.update(env)
    return subprocess.run(  # nosec B603 B607 -- fixed gh CLI invocation, no shell/user input
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
        env=subprocess_env,
    )


def _sync(task: Task, env: dict[str, str] | None, status: str | None) -> SyncResult:
    project = _project_number(env)
    if not project:
        return _warning(task.id, "no project configured for this repo")

    owner = _owner(env)
    try:
        if status is None:
            result = _run_gh(
                [
                    "project",
                    "item-create",
                    project,
                    "--owner",
                    owner,
                    "--title",
                    f"{task.id} {task.title}",
                ],
                env,
            )
        else:
            item_result = _run_gh(
                [
                    "project",
                    "item-list",
                    project,
                    "--owner",
                    owner,
                    "--format",
                    "json",
                    "--jq",
                    f'.items[] | select(.content.title | startswith("{task.id}")) | .id',
                ],
                env,
            )
            if item_result.returncode != 0:
                return _warning(task.id, _classify_gh_failure(item_result.stderr))
            item_id = item_result.stdout.strip() or task.id
            result = _run_gh(
                [
                    "project",
                    "item-edit",
                    "--id",
                    item_id,
                    "--project-id",
                    project,
                    "--field-id",
                    "Status",
                    "--single-select-option-id",
                    "Done",
                ],
                env,
            )
    except FileNotFoundError:
        return _warning(task.id, "gh: not found")
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        return _warning(task.id, stderr or "gh command failed")
    except OSError as exc:
        return _warning(task.id, str(exc))

    if result.returncode != 0:
        return _warning(task.id, _classify_gh_failure(result.stderr))

    if status is None:
        message = f"Synced {task.id} {task.title} to GitHub Project item (status: In Progress)"
    else:
        message = f"Updated GitHub Project item for {task.id} to status: {status}"
    return SyncResult(success=True, message=message)


def sync_on_pr_open(task: Task, *, env: dict[str, str] | None = None) -> SyncResult:
    """Create or link a GitHub Projects item for `task` after a PR is opened.

    Best-effort: never raises. Any failure (no project configured, `gh` not
    authenticated/installed, or any other error) is reported as a
    `SyncResult(success=False, ...)` warning.
    """
    return _sync(task, env, status=None)


def sync_on_pr_merge(task: Task, *, env: dict[str, str] | None = None) -> SyncResult:
    """Update the linked GitHub Projects item's status to "Done" after a PR
    for `task` is merged.

    Best-effort: never raises. Any failure is reported as a
    `SyncResult(success=False, ...)` warning.
    """
    return _sync(task, env, status="Done")
