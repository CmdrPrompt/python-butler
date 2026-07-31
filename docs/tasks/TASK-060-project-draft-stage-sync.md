# TASK-060 Repo-local Project config and draft-stage GitHub Projects sync

## Status
done

## Requirements
**Binding:** Requirement 6 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-059
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer who sometimes runs the Task Drafter agent against a different local repo than the one it's invoked from, I want a new task file to show up in that target repo's GitHub Project as soon as it's written, resolved from the target repo itself rather than from whatever `BUTLER_GITHUB_PROJECT` the invoking shell happens to have, so that task visibility on the Project board doesn't depend on which workspace drafted the task.

## Description
Today, `butler task sync-project` (`src/butler_core/projects.py`) only runs
at PR-open and PR-merge time, via `make pr-task`/`merge-pr`, and resolves
the target Project purely from the `BUTLER_GITHUB_PROJECT` environment
variable of whichever process invokes it. That variable identifies nothing
about *which repo* a task belongs to — it breaks down when an agent (e.g.
Task Drafter, run with `isolation: "worktree"`) writes a task file into a
different local repo than the one the invoking shell's environment was
configured for.

This task adds:

1. A repo-local `.butler-project` config file (plain text, contents = the
   Project number) that `_project_number()` in `projects.py` checks first,
   falling back to `BUTLER_GITHUB_PROJECT` only if the file is absent.
2. A new `--stage draft` option on `butler task sync-project`, behaving
   like `--stage open` (create/link a Project item).
3. An update to the Workflow Guardian agent definitions
   (`.claude/agents/workflow-guardian.agent.md`,
   `claude-agents/workflow-guardian.agent.md`, and
   `templates/workflow-guardian.agent.md.tmpl`) instructing it to run
   `butler task sync-project <id> --stage draft` for every new/modified
   task file immediately after merging Task Drafter's worktree branch,
   best-effort (never blocking the merge).

Task Drafter's own agent definition and tool set are explicitly untouched
by this task — it stays Read/Grep/Glob/Write/TodoWrite/Skill, no Bash, no
GitHub interaction, per Requirement 6.

**Implementation location:** `src/butler_core/projects.py` (project-number
resolution, new `draft` stage), `src/butler_cli/__main__.py` (CLI plumbing
for `--stage draft` if the argparse choices need updating),
`.claude/agents/workflow-guardian.agent.md`,
`claude-agents/workflow-guardian.agent.md`,
`templates/workflow-guardian.agent.md.tmpl`, plus tests in
`tests/test_projects.py` / `tests/test_projects_cli.py`.

## Branch
**Branch name:** `task/060-project-draft-stage-sync`
**Switch/create:** `git checkout -b task/060-project-draft-stage-sync`
**Make target:** `make branch-task f=TASK-060`

## Acceptance criteria (Gherkin)

- [x] Scenario: `.butler-project` resolves the Project number ahead of the environment variable
      Given a target repo has a `.butler-project` file containing a Project number, and `BUTLER_GITHUB_PROJECT` is unset or set to a different number
      When the sync resolves the Project for that repo
      Then it uses the number from `.butler-project`, not the environment variable

- [x] Scenario: Environment variable fallback when no config file exists
      Given a target repo has no `.butler-project` file, and `BUTLER_GITHUB_PROJECT` is set
      When the sync resolves the Project for that repo
      Then it uses the `BUTLER_GITHUB_PROJECT` value, matching today's Requirement 4 behavior unchanged

- [x] Scenario: `--stage draft` creates a Project item for a freshly drafted task
      Given a task file exists with no linked Project item yet, and a Project is resolvable (via `.butler-project` or the environment variable)
      When `butler task sync-project <id> --stage draft` runs
      Then it creates/links a Project item for the task, the same way `--stage open` does today

- [x] Scenario: Workflow Guardian syncs after merging Task Drafter's branch, best-effort
      Given Workflow Guardian has just merged Task Drafter's worktree branch containing one or more new/modified task files
      When Workflow Guardian completes the merge
      Then it runs the draft-stage sync for each of those task files, and a sync failure (no Project configured, `gh` not authenticated, etc.) produces a warning without blocking or failing the merge

- [x] Scenario: "No Project configured" warning offers both setup options
      Given neither `.butler-project` nor `BUTLER_GITHUB_PROJECT` resolves a Project for the repo
      When the sync reports the warning
      Then the suggestion includes both creating `.butler-project` and `export BUTLER_GITHUB_PROJECT=...` as configuration options

## Out of scope
- Changing Task Drafter's tool set or giving it Bash/GitHub-interaction
  capability — it stays a pure file-writing agent (Requirement 6).
- Caching or memoizing the resolved Project number across invocations.
- Any change to the `--stage open`/`--stage merge` behavior beyond the
  project-number resolution change that applies uniformly to all stages.
- The Requirement 5 node-ID resolution fix (TASK-059) — this task depends
  on it but does not re-implement it.

## Blockers
None

## Completion
**Date:** 2026-07-31
**Summary:** Added `_repo_root`/`_butler_project_file_value` helpers in
`src/butler_core/projects.py` that walk up from `tasks_dir` to the target
repo's root (marked by `.git`) and read `.butler-project` if present;
`_project_number()` now checks that file before falling back to
`BUTLER_GITHUB_PROJECT`. Threaded a new `tasks_dir` keyword through `_sync`,
`sync_on_pr_open`, and `sync_on_pr_merge`, and added `sync_on_pr_draft`
(identical behavior to `sync_on_pr_open`, kept as a separate name for
call-site clarity). Added `--stage draft` to the `butler task sync-project`
CLI (`src/butler_cli/__main__.py`). Extended the "no project configured"
warning's setup suggestion to offer `.butler-project` alongside `export
BUTLER_GITHUB_PROJECT=...`. Updated `.claude/agents/workflow-guardian.agent.md`
and its mirror `claude-agents/workflow-guardian.agent.md` (kept byte-identical
per `check-agents-sync`) with a new "GitHub Projects draft sync gate" rule and
an Operating Procedure step 6 addition instructing Workflow Guardian to run
`butler task sync-project <id> --stage draft` for each new/modified task file
immediately after merging Task Drafter's worktree branch, best-effort. Added
a lighter matching addition to the generic consumer-project scaffold
`templates/workflow-guardian.agent.md.tmpl`. Task Drafter's own agent
definition and tool set are untouched (verified by a docs-level test
asserting no `Bash` in its `tools:` line). Also created this repo's own
`.butler-project` (contents: `2`), and verified live against the real
`CmdrPrompt/python-butler` GitHub Project: `butler task sync-project
TASK-060 --stage draft` (run with `BUTLER_GITHUB_PROJECT` explicitly unset)
successfully created the TASK-060 item using only the config file.
**Files changed:**
- `src/butler_core/projects.py` - modified
- `src/butler_cli/__main__.py` - modified
- `.claude/agents/workflow-guardian.agent.md` - modified
- `claude-agents/workflow-guardian.agent.md` - modified
- `templates/workflow-guardian.agent.md.tmpl` - modified
- `.butler-project` - created
- `tests/test_projects_draft_stage.py` - created
- `tests/test_workflow_guardian_draft_sync_docs.py` - created
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-060-project-draft-stage-sync.md` - modified
**Branch:** `git checkout task/060-project-draft-stage-sync`
**Stage:** `git add src/butler_core/projects.py src/butler_cli/__main__.py .claude/agents/workflow-guardian.agent.md claude-agents/workflow-guardian.agent.md templates/workflow-guardian.agent.md.tmpl .butler-project tests/test_projects_draft_stage.py tests/test_workflow_guardian_draft_sync_docs.py CHANGELOG.md docs/tasks/TASK-060-project-draft-stage-sync.md`
**Commit:** `git commit -m "Add repo-local .butler-project config and a draft-stage GitHub Projects sync"`
