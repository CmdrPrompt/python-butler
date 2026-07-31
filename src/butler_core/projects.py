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
from datetime import date
from pathlib import Path
from typing import Any

from butler_core.tasks import Task

_PROJECT_ENV_VAR = "BUTLER_GITHUB_PROJECT"
_OWNER_ENV_VAR = "GITHUB_REPOSITORY_OWNER"
_PROJECT_CONFIG_FILENAME = ".butler-project"


@dataclass
class SyncResult:
    """Outcome of a one-way write to GitHub Projects.

    Only carries what was written (or attempted), never any field value
    read back from GitHub Projects.
    """

    success: bool
    message: str


def _repo_root(start: Path) -> Path:
    """Walk up from `start` looking for the target repo's root (marked by a
    `.git` directory or file), so `.butler-project` is only looked up within
    the repo that owns `start`, never an unrelated ancestor directory."""
    for directory in [start, *start.parents]:
        if (directory / ".git").exists():
            return directory
    return start


def _butler_project_file_value(tasks_dir: str | None) -> str | None:
    if not tasks_dir:
        return None
    repo_root = _repo_root(Path(tasks_dir).resolve())
    config_file = repo_root / _PROJECT_CONFIG_FILENAME
    if not config_file.is_file():
        return None
    return config_file.read_text().strip() or None


def _project_number(env: dict[str, str] | None, tasks_dir: str | None = None) -> str | None:
    from_file = _butler_project_file_value(tasks_dir)
    if from_file:
        return from_file
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


def _fetch_project_fields(
    project: str, owner: str, env: dict[str, str] | None
) -> list[dict[str, Any]] | None:
    """Resolve the raw `fields` array from `gh project field-list`, so
    callers needing more than one field (e.g. backfill's Status/Created/
    Closed) can share a single `gh` invocation."""
    result = _run_gh(["project", "field-list", project, "--owner", owner, "--format", "json"], env)
    if result.returncode != 0:
        return None
    try:
        fields: list[dict[str, Any]] = json.loads(result.stdout)["fields"]
        return fields
    except (ValueError, KeyError, TypeError):
        return None


def _find_field_by_name(fields: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for field in fields:
        if field.get("name") == name:
            return field
    return None


def _normalize_status_name(status_name: str) -> str:
    return status_name.replace("-", " ").strip().lower()


def _match_status_option(fields: list[dict[str, Any]], status_name: str) -> tuple[str, str] | None:
    """Match a single-select "Status" option by name, case-insensitively,
    treating `-` in `status_name` as a space (so a task file's `in-progress`
    matches a Project option literally named "In Progress")."""
    normalized = _normalize_status_name(status_name)
    for field in fields:
        if field.get("name") != "Status":
            continue
        for option in field.get("options", []):
            if _normalize_status_name(str(option.get("name", ""))) == normalized:
                return field["id"], option["id"]
        return None
    return None


def _resolve_status_option_field_ids(
    project: str, owner: str, env: dict[str, str] | None, status_name: str
) -> tuple[str, str] | None:
    """Resolve the "Status" field's node ID and the node ID of the option
    matching `status_name` that `gh project item-edit
    --field-id`/`--single-select-option-id` require."""
    fields = _fetch_project_fields(project, owner, env)
    if fields is None:
        return None
    return _match_status_option(fields, status_name)


def _resolve_status_done_field_ids(
    project: str, owner: str, env: dict[str, str] | None
) -> tuple[str, str] | None:
    """Resolve the "Status" field's node ID and its "Done" option's node ID
    that `gh project item-edit --field-id`/`--single-select-option-id`
    require, instead of the literal strings "Status"/"Done"."""
    return _resolve_status_option_field_ids(project, owner, env, "Done")


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
            f"  echo <number from the command above> > .butler-project\n"
            f"  (or) export BUTLER_GITHUB_PROJECT=<number from the command above>"
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


def _item_list_lookup(
    task: Task, project: str, owner: str, env: dict[str, str] | None
) -> subprocess.CompletedProcess[str]:
    """The `gh project item-list --jq` lookup for the Project item linked to
    `task`, shared by `_update_status_done` and `_backfill` so the `--jq`
    filter string is defined exactly once."""
    return _run_gh(
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


def _update_status_done(
    task: Task, project: str, owner: str, env: dict[str, str] | None
) -> SyncResult:
    try:
        item_result = _item_list_lookup(task, project, owner, env)
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


def _sync(
    task: Task,
    env: dict[str, str] | None,
    status: str | None,
    tasks_dir: str | None = None,
) -> SyncResult:
    project = _project_number(env, tasks_dir)
    if not project:
        return _no_project_warning(task, env)

    owner = _owner(env)
    if status is None:
        return _create_item(task, project, owner, env)
    return _update_status_done(task, project, owner, env)


def sync_on_pr_open(
    task: Task, *, env: dict[str, str] | None = None, tasks_dir: str | None = None
) -> SyncResult:
    """Create or link a GitHub Projects item for `task` after a PR is opened.

    Best-effort: never raises. Any failure (no project configured, `gh` not
    authenticated/installed, or any other error) is reported as a
    `SyncResult(success=False, ...)` warning. The target Project is resolved
    from a `.butler-project` file in `tasks_dir`'s repo, falling back to the
    `BUTLER_GITHUB_PROJECT` environment variable if the file is absent.
    """
    return _sync(task, env, status=None, tasks_dir=tasks_dir)


def sync_on_pr_draft(
    task: Task, *, env: dict[str, str] | None = None, tasks_dir: str | None = None
) -> SyncResult:
    """Create or link a GitHub Projects item for `task` as soon as its task
    file is drafted (before any PR exists). Behaves identically to
    `sync_on_pr_open`; kept as a separate name so callers (e.g. Workflow
    Guardian, right after merging Task Drafter's branch) can express intent.
    """
    return _sync(task, env, status=None, tasks_dir=tasks_dir)


def sync_on_pr_merge(
    task: Task, *, env: dict[str, str] | None = None, tasks_dir: str | None = None
) -> SyncResult:
    """Update the linked GitHub Projects item's status to "Done" after a PR
    for `task` is merged.

    Best-effort: never raises. Any failure is reported as a
    `SyncResult(success=False, ...)` warning. Project resolution follows the
    same `.butler-project` / `BUTLER_GITHUB_PROJECT` precedence as
    `sync_on_pr_open`.
    """
    return _sync(task, env, status="Done", tasks_dir=tasks_dir)


def _task_file_path(task: Task, tasks_dir: str | None) -> Path | None:
    """Locate `task`'s file on disk within `tasks_dir`, so backfill can read
    its git history. Mirrors `tasks.py`'s `_find_task_file` lookup but kept
    local to this module, which owns all of its own GitHub-Projects-adjacent
    logic. Returns None (rather than raising) if `tasks_dir` is unset or no
    file matches, since backfill's item-create/Status steps can still
    succeed without a Created/Closed date."""
    if not tasks_dir:
        return None
    matches = sorted(Path(tasks_dir).glob(f"{task.id}*.md"))
    return matches[0] if matches else None


def _git_log_dates(repo_root: Path, path: Path, log_args: list[str]) -> list[str]:
    """Run `git log <log_args> --format=%aI -- <path>` in `repo_root` and
    return its stdout lines. Never raises: any failure (non-zero exit,
    missing git, etc.) is treated as "no date available" by returning []."""
    try:
        result = subprocess.run(  # nosec B603 B607 -- fixed git CLI invocation, no shell/user input
            ["git", "log", *log_args, "--format=%aI", "--", str(path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _first_commit_date(repo_root: Path, path: Path) -> str | None:
    """The date-only (`YYYY-MM-DD`) prefix of the earliest commit that added
    `path`, per `git log --diff-filter=A --follow` (oldest commit last)."""
    lines = _git_log_dates(repo_root, path, ["--diff-filter=A", "--follow"])
    return lines[-1][:10] if lines else None


def _most_recent_commit_date(repo_root: Path, path: Path) -> str | None:
    """The date-only (`YYYY-MM-DD`) prefix of `path`'s most recent commit."""
    lines = _git_log_dates(repo_root, path, ["-1"])
    return lines[0][:10] if lines else None


def _closed_date(task: Task, repo_root: Path | None, file_path: Path | None) -> str | None:
    """The task's own Completion date when present and parseable as a date,
    otherwise the task file's most recent git commit date."""
    if task.completion is not None and task.completion.date.strip():
        try:
            date.fromisoformat(task.completion.date.strip())
            return task.completion.date.strip()
        except ValueError:
            pass
    if repo_root is None or file_path is None:
        return None
    return _most_recent_commit_date(repo_root, file_path)


def _display_status(status: str) -> str:
    """Human-readable form of a task's `## Status` value for the success
    message, matching the Project's own option-naming convention (e.g.
    "in-progress" -> "In Progress")."""
    return status.replace("-", " ").strip().title()


def _item_edit_date(
    item_id: str, project_node_id: str, field_id: str, value: str, env: dict[str, str] | None
) -> subprocess.CompletedProcess[str]:
    return _run_gh(
        [
            "project",
            "item-edit",
            "--id",
            item_id,
            "--project-id",
            project_node_id,
            "--field-id",
            field_id,
            "--date",
            value,
        ],
        env,
    )


def _backfill(
    task: Task,
    project: str,
    owner: str,
    env: dict[str, str] | None,
    tasks_dir: str | None,
) -> SyncResult:
    create_result = _create_item(task, project, owner, env)
    if not create_result.success:
        return create_result

    try:
        resolved = _backfill_resolve_and_set_status(task, project, owner, env)
        if isinstance(resolved, SyncResult):
            return resolved
        item_id, project_node_id, fields = resolved
        created_date, closed_date = _backfill_dates(
            task, item_id, project_node_id, fields, tasks_dir, env
        )
    except FileNotFoundError:
        return _warning(task.id, "gh: not found")
    except subprocess.CalledProcessError as exc:
        return _warning(task.id, (exc.stderr or "").strip() or "gh command failed")
    except OSError as exc:
        return _warning(task.id, str(exc))

    parts = [f"status: {_display_status(task.status)}"]
    if created_date:
        parts.append(f"created: {created_date}")
    if closed_date:
        parts.append(f"closed: {closed_date}")
    message = f"Synced {task.id} {task.title} to GitHub Project item ({', '.join(parts)})"
    return SyncResult(success=True, message=message)


def _backfill_resolve_and_set_status(
    task: Task, project: str, owner: str, env: dict[str, str] | None
) -> tuple[str, str, list[dict[str, Any]]] | SyncResult:
    """Look up the Project item linked to `task`, resolve the "Status" field/
    option matching the task's own status, and set it. Returns
    `(item_id, project_node_id, fields)` on success (so `_backfill_dates` can
    reuse the already-fetched `fields` for Created/Closed), or a failure
    `SyncResult` warning per Requirement 4's best-effort contract."""
    item_result = _item_list_lookup(task, project, owner, env)
    if item_result.returncode != 0:
        return _warning(task.id, _classify_gh_failure(item_result.stderr))
    item_id = item_result.stdout.strip() or task.id

    project_node_id = _resolve_project_node_id(project, owner, env)
    fields = _fetch_project_fields(project, owner, env)
    status_ids = _match_status_option(fields, task.status) if fields is not None else None
    if project_node_id is None or fields is None or status_ids is None:
        return _warning(
            task.id, f'no "Status" field/option matching "{task.status}" on this Project'
        )
    status_field_id, status_option_id = status_ids

    status_edit_result = _run_gh(
        [
            "project",
            "item-edit",
            "--id",
            item_id,
            "--project-id",
            project_node_id,
            "--field-id",
            status_field_id,
            "--single-select-option-id",
            status_option_id,
        ],
        env,
    )
    if status_edit_result.returncode != 0:
        return _warning(task.id, _classify_gh_failure(status_edit_result.stderr))

    return item_id, project_node_id, fields


def _backfill_dates(
    task: Task,
    item_id: str,
    project_node_id: str,
    fields: list[dict[str, Any]],
    tasks_dir: str | None,
    env: dict[str, str] | None,
) -> tuple[str | None, str | None]:
    """Opportunistically set the Project's "Created"/"Closed" date fields (if
    present) from the task file's git history / its own Completion date.
    Returns `(created_date, closed_date)` -- whichever was actually set, or
    None for each that was skipped (missing field, missing task file, or no
    date available)."""
    file_path = _task_file_path(task, tasks_dir)
    repo_root = _repo_root(file_path.parent) if file_path is not None else None

    created_field = _find_field_by_name(fields, "Created")
    created_date = None
    if created_field is not None and file_path is not None and repo_root is not None:
        created_date = _first_commit_date(repo_root, file_path)
        if created_date is not None:
            _item_edit_date(item_id, project_node_id, created_field["id"], created_date, env)

    closed_field = _find_field_by_name(fields, "Closed")
    closed_date = None
    if closed_field is not None and task.status == "done":
        closed_date = _closed_date(task, repo_root, file_path)
        if closed_date is not None:
            _item_edit_date(item_id, project_node_id, closed_field["id"], closed_date, env)

    return created_date, closed_date


def sync_on_pr_backfill(
    task: Task, *, env: dict[str, str] | None = None, tasks_dir: str | None = None
) -> SyncResult:
    """Backfill a historical task's Project item: create/link the item, set
    Status to match the task file's own `## Status`, and opportunistically
    set the Project's "Created"/"Closed" date fields from the task file's
    git history and its own `## Completion` date.

    Best-effort like the other sync stages: a missing Project or a "Status"
    field/option that can't be resolved is a `SyncResult(success=False,
    ...)` warning per Requirement 4. A missing "Created" or "Closed" date
    field on the Project is *not* a warning -- each is opportunistic and is
    silently skipped, per Requirement 8. Project resolution follows the
    same `.butler-project` / `BUTLER_GITHUB_PROJECT` precedence as
    `sync_on_pr_open`.
    """
    project = _project_number(env, tasks_dir)
    if not project:
        return _no_project_warning(task, env)

    owner = _owner(env)
    return _backfill(task, project, owner, env, tasks_dir)
