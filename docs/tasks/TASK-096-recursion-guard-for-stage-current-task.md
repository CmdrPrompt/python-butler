# TASK-096 Recursion guard for `stage-current-task`/`stage-task` against runaway nested `make`

## Status
todo

## Note
Discovered live in `firefly-bills-analyzer` (a consumer project), not in
python-butler itself. Filed here per that project's cross-workspace policy:
task files describing a bug that belongs to butler are created in this repo
after explicit user approval, without editing any butler source from the
consumer project.

## Requirements
**Binding:** None yet. Requirement 15 (REQUIREMENTS_TASK_WORKFLOW.md, fixed
via TASK-086) already addresses this bug's original root cause (the
Completion `**Stage:**` field being executed as a free-form shell command).
This task proposes a *second*, independent safeguard and needs its own new
requirement drafted and confirmed in REQUIREMENTS_TASK_WORKFLOW.md before
implementation — see Description for why Requirement 15 alone is not
sufficient.
**BDD mode:** BDD-ABSENT
**Depends on:** None
**Precedence:** N/A until a requirement exists. Do not implement from this
task file until a Requirements Drafter round has produced and the user has
confirmed the requirement text this task should bind to.

## Story (context, not binding)
As a maintainer of a project governed by butler, I want `make
stage-current-task` (and `butler task stage`) to refuse to run if it detects
it is already running inside itself, so that a bug or misconfiguration that
causes it to re-invoke itself fails fast with one clear error instead of
silently forking an unbounded tree of `make`/`butler` processes that has to
be found and killed by hand.

## Description
**Bug (reproduced live, not from source-reading):** on 2026-09-20, running
`make stage-current-task` in `firefly-bills-analyzer` spawned a runaway,
ever-growing tree of nested `make`/`butler` processes — over 60 accumulated
over ~8 minutes (visible in `ps aux` as `make[34]` through `make[109]`, and
dozens of `.../lib/firefly-python-api/.venv/bin/butler --tasks-dir docs/tasks
task stage TASK-037` processes sleeping, not progressing) — until manually
killed with `pkill`. `make`'s own output confirmed the mechanism:
`stage-current-task`/`stage-task` kept invoking themselves recursively.

**Root cause of this specific incident:** exactly Requirement 15's
already-documented failure mode. The task file's Completion `**Stage:**`
field had been filled with `` `make stage-current-task` `` (a command)
instead of a literal file list. But — and this is why the incident happened
even though Requirement 15 is already implemented in python-butler's current
source (`src/butler_core/git_ops.py::stage_for` uses `task.stage_paths` and
always constructs `git add` itself) — the `butler` binary that actually ran
was an old, pre-fix version installed inside an unrelated dependency's venv
(`lib/firefly-python-api/.venv/bin/butler`), still using the old
`Task.stage_cmd: str` executed via `subprocess.run(shlex.split(task.stage_cmd))`.
The project's own vendored `.butler/` submodule already had the fix, but it
was never the one on `PATH`/actually invoked. Confirmed by diffing the two
installed copies' `git_ops.py`/`tasks.py`: the submodule copy has
`stage_paths: list[str]`, the installed copy still has `stage_cmd: str`.

**Why Requirement 15 alone doesn't close this out:** it protects only
against *this one* cause (a command string in the Stage field), and only in
butler versions that actually contain the TASK-086 fix. In practice:
- Consumer projects can have a stale installed `butler` (as demonstrated
  here) for a long time after a fix ships, with nothing surfacing that
  mismatch.
- Any *other* future cause of `make stage-current-task`/`stage-task`
  recursing (a Makefile refactor introducing a circular target dependency,
  a different field or code path reinvoking `make`, etc.) would reproduce
  the exact same runaway-process symptom, unprotected by Requirement 15.

**Proposed safeguard (subject to Requirements Drafter refinement):** have
`stage-current-task`/`stage-task` (and/or `butler task stage` itself) detect
that it is already running — e.g. via a sentinel environment variable set at
the start of the target/command and checked before proceeding — and fail
immediately with a clear error ("stage-current-task is already running;
refusing to recurse") instead of proceeding into a second invocation. This
is defense-in-depth: it should catch recursion regardless of *why* it
happened, independent of which specific bug caused it, and independent of
whether the invoking butler version already has Requirement 15's fix.

A related, separate concern worth a follow-up task (out of scope here): some
way for `butler` (or `make check-butler`) to detect and warn when the
installed `butler` version predates known-fixed incident-class bugs like
this one, so a stale install in a consumer project's dependency venv doesn't
silently reintroduce an already-fixed hazard.

## Branch
**Branch name:** `task/096-recursion-guard-for-stage-current-task`
**Switch/create:** `git checkout -b task/096-recursion-guard-for-stage-current-task`
**Make target:** `make branch-task f=TASK-096`

## Acceptance criteria (Gherkin)
Draft only — to be finalized once the requirement is confirmed and this task
file is re-drafted by Task Drafter.

- [ ] Scenario: `make stage-current-task` invoked while already running for the same task fails fast
      Given `stage-current-task` (or `stage-task`) is already in progress for a task
      When it is invoked again (directly or via a bug that causes self-reinvocation)
      Then the second invocation exits immediately with a clear "already running" error
      And no additional nested `make`/`butler` process is spawned

- [ ] Scenario: Normal, non-recursive invocation is unaffected
      Given no `stage-current-task`/`stage-task` invocation is currently in progress
      When `make stage-current-task` runs normally
      Then it completes exactly as it does today, with no behavior change

## Out of scope
- Re-fixing Requirement 15's original root cause (already fixed, TASK-086)
- Detecting or warning about a stale/outdated installed `butler` version
  (flagged above as a separate follow-up task)
- Any change to `.butler/` submodule distribution or `make butler-pull`
  mechanics

## Blockers
Requirement not yet drafted or confirmed. Needs a Requirements Drafter round
(new requirement in `REQUIREMENTS_TASK_WORKFLOW.md`, e.g. "Requirement 18")
and explicit user confirmation before implementation can start.

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/096-recursion-guard-for-stage-current-task`
**Stage:** `REQUIREMENTS_TASK_WORKFLOW.md docs/tasks/TASK-096-recursion-guard-for-stage-current-task.md`
**Commit:** `git commit -m "Add Requirement 18: Makefile recursion guard for *-current-task/*-task targets (TASK-096)"`
