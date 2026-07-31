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

import json
import os
import re
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


def _warning(task_id: str, reason: str, *, suggestion: str | None = None) -> SyncResult:
    message = f"Warning: could not sync {task_id} to GitHub Projects ({reason}) - continuing"
    if suggestion:
        message = f"{message}\n{suggestion}"
    return SyncResult(success=False, message=message)


def _parse_owner_repo_from_git_remote(url: str) -> tuple[str, str] | None:
    """Parse an owner/repo pair out of a `git remote get-url origin` URL,
    supporting both SSH (`git@github.com:owner/repo.git`) and HTTPS
    (`https://github.com/owner/repo.git`) forms."""
    match = re.search(r"[/:]([^/:]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    if not owner or not repo:
        return None
    return owner, repo


def _lookup_owner_repo(env: dict[str, str] | None) -> tuple[str, str] | None:
    """Best-effort lookup of the current repository's owner/name, used to
    build a copy-pasteable setup suggestion when no Project is configured.
    Never raises; returns None on any failure so callers can fall back to
    the generic warning."""
    try:
        gh_result = _run_gh(["repo", "view", "--json", "owner,name"], env)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        gh_result = None
    if gh_result is not None and gh_result.returncode == 0:
        try:
            data = json.loads(gh_result.stdout)
            owner = data["owner"]["login"]
            name = data["name"]
        except (ValueError, KeyError, TypeError):
            owner = name = None
        if owner and name:
            return owner, name

    try:
        git_result = subprocess.run(  # nosec B603 B607 -- fixed git CLI invocation, no shell/user input
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return None
    if git_result.returncode != 0:
        return None
    return _parse_owner_repo_from_git_remote(git_result.stdout)


def _classify_gh_failure(stderr: str) -> str:
    lowered = stderr.lower()
    if "auth" in lowered:
        return "gh: not authenticated"
    return stderr.strip() or "gh command failed"


def _resolve_project_node_id(project: str, owner: str, env: dict[str, str] | None) -> str | None:
    """Resolve the GraphQL node ID (e.g. `PVT_...`) `gh project item-edit
    --project-id` requires, from the human-facing project number."""
    result = _run_gh(["project", "view", project, "--owner", owner, "--format", "json"], env)
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return str(data["id"])
    except (ValueError, KeyError, TypeError):
        return None


def _resolve_status_done_field_ids(
    project: str, owner: str, env: dict[str, str] | None
) -> tuple[str, str] | None:
    """Resolve the "Status" field's node ID and its "Done" option's node ID
    that `gh project item-edit --field-id`/`--single-select-option-id`
    require, instead of the literal strings "Status"/"Done"."""
    result = _run_gh(["project", "field-list", project, "--owner", owner, "--format", "json"], env)
    if result.returncode != 0:
        return None
    try:
        fields = json.loads(result.stdout)["fields"]
    except (ValueError, KeyError, TypeError):
        return None
    for field in fields:
        if field.get("name") != "Status":
            continue
        for option in field.get("options", []):
            if option.get("name") == "Done":
                return field["id"], option["id"]
        return None
    return None


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


def _no_project_warning(task: Task, env: dict[str, str] | None) -> SyncResult:
    suggestion = None
    owner_repo = _lookup_owner_repo(env)
    if owner_repo is not None:
        owner, repo = owner_repo
        suggestion = (
            f"To configure one:\n"
            f"  gh project create --owner {owner} --title {repo}\n"
            f"  export BUTLER_GITHUB_PROJECT=<number from the command above>"
        )
    return _warning(task.id, "no project configured for this repo", suggestion=suggestion)


def _create_item(task: Task, project: str, owner: str, env: dict[str, str] | None) -> SyncResult:
    try:
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
    except FileNotFoundError:
        return _warning(task.id, "gh: not found")
    except subprocess.CalledProcessError as exc:
        return _warning(task.id, (exc.stderr or "").strip() or "gh command failed")
    except OSError as exc:
        return _warning(task.id, str(exc))

    if result.returncode != 0:
        return _warning(task.id, _classify_gh_failure(result.stderr))

    message = f"Synced {task.id} {task.title} to GitHub Project item (status: In Progress)"
    return SyncResult(success=True, message=message)


def _update_status_done(
    task: Task, project: str, owner: str, env: dict[str, str] | None
) -> SyncResult:
    try:
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

        project_node_id = _resolve_project_node_id(project, owner, env)
        status_done_ids = _resolve_status_done_field_ids(project, owner, env)
        if project_node_id is None or status_done_ids is None:
            return _warning(task.id, 'no "Status"/"Done" field on this Project')
        field_id, option_id = status_done_ids

        result = _run_gh(
            [
                "project",
                "item-edit",
                "--id",
                item_id,
                "--project-id",
                project_node_id,
                "--field-id",
                field_id,
                "--single-select-option-id",
                option_id,
            ],
            env,
        )
    except FileNotFoundError:
        return _warning(task.id, "gh: not found")
    except subprocess.CalledProcessError as exc:
        return _warning(task.id, (exc.stderr or "").strip() or "gh command failed")
    except OSError as exc:
        return _warning(task.id, str(exc))

    if result.returncode != 0:
        return _warning(task.id, _classify_gh_failure(result.stderr))

    return SyncResult(
        success=True, message=f"Updated GitHub Project item for {task.id} to status: Done"
    )


def _sync(task: Task, env: dict[str, str] | None, status: str | None) -> SyncResult:
    project = _project_number(env)
    if not project:
        return _no_project_warning(task, env)

    owner = _owner(env)
    if status is None:
        return _create_item(task, project, owner, env)
    return _update_status_done(task, project, owner, env)


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
