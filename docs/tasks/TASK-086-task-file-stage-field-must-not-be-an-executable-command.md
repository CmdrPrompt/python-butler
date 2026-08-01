# TASK-086 Task file Completion `Stage:` field must not be an executable command

## Status
done

## Requirements
**Binding:** Requirement 15: Task file Completion `Stage:` field is data, not an executable command
**BDD mode:** BDD-ABSENT
**Depends on:** None
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer, I want the task file's Completion `**Stage:**` field to be
treated as plain data (a list of file paths) instead of an arbitrary shell
command, so that a mistakenly-written `make`/`butler` invocation in that
field can never recurse into a runaway process tree the way it did in
TASK-069, TASK-082, and TASK-083.

## Description
Change `butler_core.tasks.Task` and its parser/renderer so the Completion
section's `**Stage:**` field can never be executed as a command:

1. Replace `Task.stage_cmd: str` with `Task.stage_paths: list[str]`,
   parsed from the Completion section's `**Stage:**` backtick content as a
   whitespace-separated list of file paths (no leading `git add`, no
   command syntax at all).
2. Change `git_ops.stage_for()` to always construct
   `["git", "add", *task.stage_paths]` itself instead of
   `subprocess.run(shlex.split(task.stage_cmd))` — no parsed string is ever
   passed to a shell or treated as a command line.
3. Update `create_task()`'s default Completion rendering and every
   reference to the old `git add <files...>` Stage-field format (the
   `task-file-format` skill's canonical template, `templates/*.tmpl`,
   `claude-agents/*.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`)
   to show a plain file list instead.
4. Leave the `**Commit:**` field and `commit_for()` unchanged — they already
   follow this pattern (message-only field, command always constructed by
   `git_ops.py`).
5. Do not migrate historical task files; only the parser/template for
   newly-drafted and in-progress task files changes, since a completed
   task's Stage field is never re-parsed after that task's `butler task
   stage` has already run once.

## Branch
**Branch name:** `task/086-task-file-stage-field-must-not-be-an-executable-command`
**Switch/create:** `git checkout -b task/086-task-file-stage-field-must-not-be-an-executable-command`
**Make target:** `make branch-task f=TASK-086`

## Acceptance criteria (Gherkin)

- [x] Scenario: Stage field is parsed as a file list, not a command
      Given a task file's Completion `**Stage:**` field contains `src/foo.py tests/test_foo.py CHANGELOG.md`
      When `butler_core.tasks.parse_task()` reads the file
      Then `Task.stage_paths` equals `["src/foo.py", "tests/test_foo.py", "CHANGELOG.md"]`
      And no `Task.stage_cmd` string attribute exists to be executed

- [x] Scenario: git_ops.stage_for() always constructs git add itself
      Given a `Task` with `stage_paths = ["src/foo.py", "CHANGELOG.md"]`
      When `git_ops.stage_for()` runs
      Then it invokes `["git", "add", "src/foo.py", "CHANGELOG.md"]` directly
      And no parsed string is passed through `shlex.split`/`subprocess.run` as a shell command

- [x] Scenario: A mistaken make/butler invocation in the Stage field fails safely
      Given a task file's Completion `**Stage:**` field contains the text `make stage-current-task`
      When `butler task stage` runs against it
      Then `git add make stage-current-task` is attempted
      And it fails immediately with a "pathspec did not match any files" error
      And no nested `make`/`butler` process is spawned

- [x] Scenario: Commit field behavior is unchanged
      Given a task file's Completion `**Commit:**` field contains `git commit -m "Add foo"`
      When `butler task commit` runs
      Then it invokes `["git", "commit", "-m", "Add foo"]` exactly as before

- [x] Scenario: Rendered template shows a plain file list
      Given `create_task()` renders a new task file's Completion section
      And the `task-file-format` skill's canonical template
      When either is inspected
      Then the `**Stage:**` example shows a whitespace-separated file list with no leading `git add`

## Out of scope
- Migrating historical task files already using the old `git add ...` Stage format
- Any change to the `**Commit:**` field or `commit_for()`
- Removing or changing `stage_for()`'s ruff/pymarkdown auto-fix steps

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Replaced `Task.stage_cmd: str` with `Task.stage_paths: list[str]`
in `butler_core.tasks`. `parse_task()` now splits the Completion section's
`**Stage:**` backtick content on whitespace into a path list instead of
extracting a free-form command string, and `render_task()`/`create_task()`
emit a plain file list with no leading `git add`. `git_ops.stage_for()` now
always constructs `["git", "add", *task.stage_paths]` itself — no parsed
string is ever passed to `shlex.split`/`subprocess.run` as a shell command,
matching the pattern `commit_for()` already used for the `**Commit:**`
field. Added a regression test
(`test_a_make_invocation_in_stage_paths_fails_as_invalid_pathspec_not_recursion`)
that runs `stage_for()` against a real git repo with `stage_paths = ["make",
"stage-current-task"]` and asserts it fails as an invalid pathspec, not a
recursive invocation. Updated the `task-file-format` skill (both
`.claude/skills/` and `claude-skills/` copies, kept identical) and
`templates/workflow-guardian.agent.md.tmpl`'s Stage-field examples to the
new plain-file-list format, and added a skill rule explicitly stating the
field is never executed as a command. Did not migrate historical task files
(e.g. TASK-015) that still show `git add ...` in their Stage field — per
the requirement, those are read-only history and are simply parsed as
literal (harmless, never-reused) path tokens now.
**Files changed:**
- `src/butler_core/tasks.py` - modified (`stage_paths` field, parser, renderer, `create_task`)
- `src/butler_core/git_ops.py` - modified (`stage_for` constructs `git add` directly, dropped `shlex`)
- `.claude/skills/task-file-format/SKILL.md` - modified
- `claude-skills/task-file-format/SKILL.md` - modified (kept identical to `.claude/skills/`)
- `templates/workflow-guardian.agent.md.tmpl` - modified
- `tests/test_tasks.py` - modified
- `tests/test_git_ops.py` - modified
- `tests/test_cli.py` - modified
- `tests/test_projects.py` - modified
- `tests/test_projects_backfill.py` - modified
- `REQUIREMENTS_TASK_WORKFLOW.md` - modified (Requirement 15)
- `CHANGELOG.md` - modified
**Branch:** `git checkout task/086-task-file-stage-field-must-not-be-an-executable-command`
**Stage:** `src/butler_core/tasks.py src/butler_core/git_ops.py .claude/skills/task-file-format/SKILL.md claude-skills/task-file-format/SKILL.md templates/workflow-guardian.agent.md.tmpl tests/test_tasks.py tests/test_git_ops.py tests/test_cli.py tests/test_projects.py tests/test_projects_backfill.py REQUIREMENTS_TASK_WORKFLOW.md CHANGELOG.md docs/tasks/TASK-086-task-file-stage-field-must-not-be-an-executable-command.md`
**Commit:** `git commit -m "Make task file Stage field data instead of an executable command (TASK-086)"`
