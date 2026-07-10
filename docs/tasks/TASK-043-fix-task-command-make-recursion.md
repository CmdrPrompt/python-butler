# TASK-043 Fix infinite recursion between `butler task <cmd>` and Makefile task targets

## Status
todo

## Description

In a consumer project (`firefly-python-api`), running `make branch-task
f=TASK-005` after installing the current `python-butler-cli` distribution
recurses infinitely and never terminates:

```
make branch-task f=TASK-005
  -> .butler/Makefile target `branch-task` runs: butler task branch TASK-005
     -> butler/commands/task.py `branch()` runs: subprocess.run(["make", "branch-task", "f=TASK-005"])
        -> .butler/Makefile target `branch-task` runs: butler task branch TASK-005
           -> ... (repeats until the process is killed / resource limits hit)
```

The same recursive shape exists for every other `butler task` subcommand that
has a Makefile counterpart: `stage` <-> `stage-task`, `commit` <->
`commit-current-task` (via `commit-task`), `pr` <-> `pr-task`, `merge` <->
`merge-current-task` (via `merge-pr`). Each direction assumes the *other*
side holds the real implementation:

- `butler/commands/task.py`'s module docstring says "proxies to Makefile
  targets" — i.e. it assumes the Makefile holds the actual git/gh logic.
- The vendored `.butler/Makefile` shipped to consumer projects only calls
  back into `butler task <cmd>` — i.e. it assumes the CLI holds the actual
  logic.

Neither side actually contains the real implementation. Checked against git
history of a consumer project's `.butler/Makefile` (`firefly-python-api`,
every squash-merged revision going back to the first `Bootstrap project with
python-butler` commit): the `butler task branch $(f)` call-out has been
there from the very first vendored version. This has apparently never
worked as a `make`-first entry point — only `butler task branch` invoked
directly could have worked in some earlier CLI version that didn't proxy to
`make`, before `task.py` was changed to shell out to `make`.

Separately (found while diagnosing this), the vendored `.butler/Makefile`
also still passes a `--tasks-dir $(TASKS_DIR)` flag to `butler` on every
invocation, but the installed CLI's root command no longer accepts a
`--tasks-dir` option at all — `tasks_dir` moved to `[tool.butler]` in
`pyproject.toml` (`butler/config.py`). Every `butler --tasks-dir ... task
...` invocation from the vendored Makefile fails immediately with `Error: No
such option: --tasks-dir`, which is actually what surfaces first, before the
recursion is even reached, unless the flag is stripped locally.

## Impact

`make branch-task`, `make stage-task` / `make stage-current-task`, `make
commit-task` / `make commit-current-task`, `make pr-task`, `make merge-pr` /
`make merge-current-task` are all non-functional for any consumer project
using the current `python-butler-cli` release together with the currently
vendored `.butler/Makefile`. This blocks the entire task-branch workflow
(`Workflow Guardian`'s Operating Procedure steps 3, 8, 14-16) that
`CLAUDE.md` mandates consumer projects use exclusively (`git commit` directly
is explicitly forbidden by the "Commit via Makefile gate").

Workaround used in `firefly-python-api` for TASK-005: stripped the stale
`--tasks-dir $(TASKS_DIR)` flags locally and ran `git checkout -b
task/<NNN>-...` directly instead of `make branch-task` / `butler task
branch`, bypassing the broken proxy chain. This is a stopgap in one consumer
repo, not a fix.

## Branch

**Branch name:** `task/043-fix-task-command-make-recursion`
**Switch/create:** `git checkout -b task/043-fix-task-command-make-recursion`
**Make target:** `make branch-task f=TASK-043`

## Requirements

None yet — no existing `REQUIREMENTS*.md` in this repo documents the
intended direction of the `butler task <cmd>` <-> Makefile relationship, so
this is a design decision to make before implementing, not just a bug fix.
Needs a Requirements Drafter round to settle: should `butler task <cmd>` own
the real git/gh logic (with the vendored `.butler/Makefile` targets becoming
thin wrappers that call `butler task <cmd>` and nothing calls back), or
should the vendored Makefile own it (with `butler task <cmd>` calling `make`
and never being invoked from within a Makefile target)? Recommend the
former, since `python-butler-cli`'s own README already describes `butler
task branch` etc. as commands meant to be run directly by developers/agents,
with the `make` targets existing mainly for CLAUDE.md-mandated call sites
and discoverability (`make help`).

## Acceptance criteria

- [ ] Exactly one side (CLI or vendored Makefile) contains the real
      implementation for branch create/switch, stage, commit, PR open, and
      PR merge; the other side is a thin, non-recursive wrapper (or is
      removed).
- [ ] `--tasks-dir` is removed from every vendored Makefile call site (or
      the CLI regains support for it) so the two stay in sync going forward.
- [ ] A regression test (or equivalent CLI-level test) exists that would
      have caught the recursion, e.g. asserting `butler task branch` in a
      fixture project completes and does not spawn a nested `butler`
      process.
- [ ] `butler install` or `butler sync` (or a new command) can refresh a
      consumer project's vendored `.butler/Makefile` to the version matching
      the installed CLI, so this class of drift doesn't require manual
      patching in every consumer repo again.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.

## Out of scope

- Fixing already-vendored `.butler/Makefile` copies in existing consumer
  repos (e.g. `firefly-python-api`) — those pick up the fix whenever they
  next resync/re-bootstrap from an updated `python-butler-cli` release.

## Notes

- Origin: discovered 2026-07-10 while running Workflow Guardian's
  `branch-task` step for TASK-005 in `firefly-python-api`, immediately after
  installing `python-butler-cli` there for the first time via `uv add --dev
  "python-butler-cli @ git+https://github.com/CmdrPrompt/python-butler-cli.git"`.
- Reported from `firefly-python-api`, a separate consumer repo, per that
  repo's cross-workspace boundary policy: only this task file was added
  here, no code changes.

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:**
**Stage:**
**Commit:**
