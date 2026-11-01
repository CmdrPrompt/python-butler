"""TASK-100: binds TASK-100-merge-diverged-local-main-pull-crash.feature.

Everything git-related is real: a bare `origin`, a working clone and a task
branch live under `tmp_path`, and `merge_pr_for` / `butler task merge` /
`make merge-pr` run against them unchanged.

Only the GitHub side is faked, by a `gh` script placed first on PATH (so the
production code issues its genuine `gh ...` subprocess calls). The fake:

* answers `gh pr list` / `gh pr view` for one open, mergeable PR (#1);
* performs `gh pr merge --squash --delete-branch` for real in the bare origin
  (temporary clone, `git merge --squash`, commit, push, delete the remote
  branch) and, like real `gh`, switches the working clone to `main` and deletes
  the local task branch;
* serves the `gh project ...` calls of the merge-stage Projects sync from one
  item whose Status lives in a state file, so "Done" is observable;
* can break the working clone's `origin` URL right after the merge to simulate
  "squash merge succeeded but updating local main fails".

Why PATH-fake instead of patching `subprocess.run`: the scenarios cross process
boundaries (`butler` CLI subprocess, `make`, `butler` inside make), which a
monkeypatch cannot reach, and the real argv the code issues is exercised.
"""

import os
import re
import shutil
import subprocess  # nosec B404 - test helper runs fixed local commands
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, scenarios, then, when

from butler_core.git_ops import GitOpsError, merge_pr_for
from butler_core.tasks import create_task

scenarios("../features/TASK-100-merge-diverged-local-main-pull-crash.feature")

REPO_ROOT = Path(__file__).resolve().parents[3]

_FAKE_GH = r"""#!__PYTHON__
import json, os, subprocess, sys, tempfile
from pathlib import Path

state = Path(os.environ["FAKE_GH_STATE"])
origin = os.environ["FAKE_GH_ORIGIN"]
args = sys.argv[1:]
with (state / "gh.log").open("a") as log:
    log.write(" ".join(args) + "\n")


def git(*a, cwd=None):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True)


def flag(name):
    return args[args.index(name) + 1]


def branch_head(branch):
    r = subprocess.run(["git", "--git-dir", origin, "rev-parse", "refs/heads/" + branch],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def remember_head(branch):
    (state / "branch").write_text(branch)
    head = branch_head(branch)
    if head:
        (state / "head_oid").write_text(head)


if args[:2] == ["pr", "list"]:
    remember_head(flag("--head"))
    print(1)
elif args[:2] == ["pr", "view"]:
    remember_head((state / "branch").read_text())
    if "mergeable" in args:
        print("MERGEABLE")
    elif "headRefOid" in args:
        print((state / "head_oid").read_text())
    else:
        print(json.dumps({"number": 1}))
elif args[:2] == ["pr", "merge"]:
    branch = (state / "branch").read_text()
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "c"
        git("clone", "-q", origin, str(clone))
        git("merge", "--squash", "origin/" + branch, cwd=clone)
        git("commit", "-q", "-m", "Squash merge of " + branch + " (#1)", cwd=clone)
        git("push", "-q", "origin", "main", cwd=clone)
        git("push", "-q", "origin", "--delete", branch, cwd=clone)
    subprocess.run(["git", "checkout", "-q", "main"], check=False)
    subprocess.run(["git", "branch", "-q", "-D", branch], check=False)
    if os.environ.get("FAKE_GH_BREAK_ORIGIN_AFTER_MERGE"):
        git("remote", "set-url", "origin", str(state / "gone.git"))
elif args[:2] == ["project", "item-list"]:
    if (state / "project_status").exists():
        print("PVI_item1")
elif args[:2] == ["project", "view"]:
    print(json.dumps({"id": "PVT_1"}))
elif args[:2] == ["project", "field-list"]:
    print(json.dumps({"fields": [{"name": "Status", "id": "FLD_status", "options": [
        {"id": "OPT_progress", "name": "In Progress"}, {"id": "OPT_done", "name": "Done"}]}]}))
elif args[:2] == ["project", "item-edit"]:
    names = {"OPT_progress": "In Progress", "OPT_done": "Done"}
    (state / "project_status").write_text(names[flag("--single-select-option-id")])
else:
    sys.stderr.write("fake gh: unsupported command: " + " ".join(args) + "\n")
    sys.exit(2)
"""


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 - fixed git invocations in tmp repos
        ["git", *args], cwd=cwd, check=check, capture_output=True, text=True
    )


def _commit_file(cwd: Path, name: str) -> str:
    (cwd / name).write_text(f"{name}\n")
    _git(cwd, "add", name)
    _git(cwd, "commit", "-q", "-m", f"Add {name}")
    return _git(cwd, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(
        "[user]\n\tname = Test\n\temail = test@example.com\n[init]\n\tdefaultBranch = main\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    for var in ("BUTLER_MERGE_GUARD", "MAKEFLAGS", "MFLAGS", "MAKELEVEL", "BUTLER_GITHUB_PROJECT"):
        monkeypatch.delenv(var, raising=False)

    state = tmp_path / "gh-state"
    state.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_FAKE_GH.replace("__PYTHON__", sys.executable))
    gh.chmod(0o755)
    venv_bin = str(Path(sys.executable).parent)
    monkeypatch.setenv("PATH", os.pathsep.join([str(bin_dir), venv_bin, os.environ["PATH"]]))

    origin = tmp_path / "origin.git"
    monkeypatch.setenv("FAKE_GH_STATE", str(state))
    monkeypatch.setenv("FAKE_GH_ORIGIN", str(origin))
    return SimpleNamespace(
        tmp=tmp_path,
        state=state,
        origin=origin,
        work=tmp_path / "work",
        error=None,
        local_only=[],
        task=None,
        cli=None,
        make=None,
    )


@given("a repository with a bare origin and a task branch with an open mergeable PR")
def _repo(ctx: SimpleNamespace) -> None:
    _git(ctx.tmp, "init", "-q", "--bare", "-b", "main", str(ctx.origin))
    seed = ctx.tmp / "seed"
    seed.mkdir()
    _git(seed, "init", "-q", "-b", "main")
    _commit_file(seed, "README.md")
    _git(seed, "remote", "add", "origin", str(ctx.origin))
    _git(seed, "push", "-q", "origin", "main")
    _git(ctx.tmp, "clone", "-q", str(ctx.origin), str(ctx.work))

    tasks_dir = ctx.work / "docs" / "tasks"
    ctx.task = create_task("Fix diverged merge", "desc", tasks_dir=str(tasks_dir))
    ctx.tasks_dir = tasks_dir
    _git(ctx.work, "checkout", "-q", "-b", ctx.task.branch_name)
    _git(ctx.work, "add", "docs")
    _git(ctx.work, "commit", "-q", "-m", "Task file and feature work")
    _git(ctx.work, "push", "-q", "-u", "origin", ctx.task.branch_name)


@given("local main has 2 unpushed commits that are also part of the task branch")
def _two_unpushed_in_branch(ctx: SimpleNamespace) -> None:
    _git(ctx.work, "checkout", "-q", "main")
    ctx.local_only = [_commit_file(ctx.work, "notes-1.txt"), _commit_file(ctx.work, "notes-2.txt")]
    _git(ctx.work, "checkout", "-q", ctx.task.branch_name)
    _git(ctx.work, "merge", "-q", "--no-edit", "main")  # what `make sync-main` does
    _git(ctx.work, "push", "-q", "origin", ctx.task.branch_name)


@given("local main has no commits that are missing from origin/main")
def _nothing_unpushed(ctx: SimpleNamespace) -> None:
    assert _git(ctx.work, "rev-list", "origin/main..main").stdout.strip() == ""


@given("local main has an unpushed commit that is not part of the task branch")
def _unpushed_not_in_branch(ctx: SimpleNamespace) -> None:
    _git(ctx.work, "checkout", "-q", "main")
    ctx.local_only = [_commit_file(ctx.work, "local-only.txt")]
    _git(ctx.work, "checkout", "-q", ctx.task.branch_name)


@given("the squash merge succeeds but updating local main fails")
def _update_fails(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_GH_BREAK_ORIGIN_AFTER_MERGE", "1")


@given('the task has a linked Project item with Status "In Progress"')
def _project_item(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    (ctx.state / "project_status").write_text("In Progress")
    monkeypatch.setenv("BUTLER_GITHUB_PROJECT", "7")


@when("the task PR is squash-merged with merge_pr_for")
def _merge_pr_for(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ctx.work)
    try:
        merge_pr_for(ctx.task)
    except Exception as exc:  # noqa: BLE001 - the Then steps inspect whatever was raised
        ctx.error = exc


@when("the butler task merge command runs")
def _butler_task_merge(ctx: SimpleNamespace) -> None:
    ctx.cli = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            "-m",
            "butler_cli",
            "--tasks-dir",
            str(ctx.tasks_dir),
            "task",
            "merge",
            ctx.task.id,
        ],
        cwd=ctx.work,
        capture_output=True,
        text=True,
        check=False,
    )


@when("make merge-pr is run for the task")
def _make_merge_pr(ctx: SimpleNamespace) -> None:
    shutil.copy(REPO_ROOT / "Makefile", ctx.work / "Makefile")
    ctx.make = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "merge-pr", f"f={ctx.task.id}"],
        cwd=ctx.work,
        capture_output=True,
        text=True,
        check=False,
    )


def _origin_main(ctx: SimpleNamespace) -> str:
    return _git(ctx.tmp, "--git-dir", str(ctx.origin), "rev-parse", "main").stdout.strip()


@then("merge_pr_for completes without raising")
def _completes(ctx: SimpleNamespace) -> None:
    assert ctx.error is None, f"merge_pr_for raised {type(ctx.error).__name__}: {ctx.error}"


@then("local main points at origin/main")
def _main_is_origin_main(ctx: SimpleNamespace) -> None:
    assert _git(ctx.work, "rev-parse", "main").stdout.strip() == _origin_main(ctx)


@then("the working tree has no merge conflicts and no merge in progress")
def _clean_tree(ctx: SimpleNamespace) -> None:
    assert _git(ctx.work, "diff", "--name-only", "--diff-filter=U").stdout.strip() == ""
    assert _git(ctx.work, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode != 0


@then("no merge is left in progress")
def _no_merge_in_progress(ctx: SimpleNamespace) -> None:
    assert _git(ctx.work, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode != 0


@then("local main is fast-forwarded to origin/main")
def _fast_forwarded(ctx: SimpleNamespace) -> None:
    assert _git(ctx.work, "rev-parse", "main").stdout.strip() == _origin_main(ctx)
    assert _git(ctx.work, "log", "--merges", "--oneline", "main").stdout.strip() == ""


@then("local main still contains that unpushed commit")
def _keeps_commit(ctx: SimpleNamespace) -> None:
    (sha,) = ctx.local_only
    contained = _git(ctx.work, "merge-base", "--is-ancestor", sha, "main", check=False)
    assert contained.returncode == 0


@then(
    "merge_pr_for raises a GitOpsError stating that the PR was merged "
    "and that local main has unpushed commits not in the PR"
)
def _raises_git_ops_error(ctx: SimpleNamespace) -> None:
    assert isinstance(ctx.error, GitOpsError), f"expected GitOpsError, got {ctx.error!r}"
    message = str(ctx.error).lower()
    assert "merged" in message
    assert "unpushed commits" in message
    assert "not in the pr" in message


@then("the error message names the command needed to resolve it")
def _names_command(ctx: SimpleNamespace) -> None:
    assert isinstance(ctx.error, GitOpsError), f"expected GitOpsError, got {ctx.error!r}"
    assert re.search(r"\bgit (reset|rebase|merge|cherry-pick|checkout|pull|push)\b", str(ctx.error))


@then("it exits non-zero with a one-line error message")
def _one_line_error(ctx: SimpleNamespace) -> None:
    assert ctx.cli.returncode != 0
    lines = [line for line in ctx.cli.stderr.splitlines() if line.strip()]
    assert len(lines) == 1, f"expected exactly one stderr line, got: {ctx.cli.stderr!r}"


@then("the output contains no Python traceback")
def _no_traceback(ctx: SimpleNamespace) -> None:
    assert "Traceback" not in ctx.cli.stdout + ctx.cli.stderr


@then("the butler task merge step exits 0")
def _merge_step_ok(ctx: SimpleNamespace) -> None:
    assert ctx.make.returncode == 0, ctx.make.stdout + ctx.make.stderr
    assert "Traceback" not in ctx.make.stdout + ctx.make.stderr


@then("the merge-stage Projects sync runs")
def _sync_runs(ctx: SimpleNamespace) -> None:
    output = ctx.make.stdout + ctx.make.stderr
    assert f"sync-project {ctx.task.id} --stage merge" in output
    assert "project item-edit" in (ctx.state / "gh.log").read_text()


@then('the Project item Status is set to "Done"')
def _status_done(ctx: SimpleNamespace) -> None:
    assert (ctx.state / "project_status").read_text() == "Done"
