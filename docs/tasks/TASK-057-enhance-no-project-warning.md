# TASK-057 Enhance "no project configured" warning with repo-specific setup instructions

## Status
done

## Requirements
**Binding:** Requirement 4 (REQUIREMENTS_TASK_WORKFLOW.md), lines 192–203 and 258–263
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer setting up GitHub Projects sync in a new task-driven repository, I want the "no project configured" warning to include concrete, copy-pasteable commands with my actual owner and repository name filled in, so I don't have to manually edit placeholders to set up the integration.

## Description
When `BUTLER_GITHUB_PROJECT` environment variable is unset and the task-to-Projects sync attempt fails, the warning message currently says "no project configured for this repo" with no guidance.

This task enhances the warning to include concrete, directly-executable setup commands:
- `gh project create --owner <owner> --title <repo>`
- `export BUTLER_GITHUB_PROJECT=<number from the command above>`

The owner and repository name MUST be derived at runtime from the current repository (via `gh repo view --json owner,name` or by parsing the `origin` remote URL) so the commands are immediately copy-pasteable without placeholder editing.

If the owner/repository cannot be determined at runtime (e.g., `gh` is not installed/authenticated or there is no `origin` remote), the sync MUST fall back gracefully to the existing generic warning rather than failing or raising an error.

**Implementation location:** `src/butler_core/projects.py`, functions `_project_number()` and `_warning()` (currently around lines 40–55).

## Branch
**Branch name:** `task/057-enhance-no-project-warning`
**Switch/create:** `git checkout -b task/057-enhance-no-project-warning`
**Make target:** `make branch-task f=TASK-057`

## Acceptance criteria (Gherkin)

- [x] Scenario: Warning includes repo-specific setup commands when owner/repo can be determined
      Given the environment variable BUTLER_GITHUB_PROJECT is unset
      And the current repository owner and name can be determined (via `gh repo view --json owner,name` or by parsing the `origin` remote)
      When a task-driven operation (e.g., `make pr-current-task`) attempts to sync the task to a GitHub Projects item
      Then the warning message includes the concrete commands `gh project create --owner <owner> --title <repo>` and `export BUTLER_GITHUB_PROJECT=<number from the command above>`, with the actual owner and repository name filled in (not placeholders)

- [x] Scenario: Warning falls back to generic message when owner/repo cannot be determined
      Given the environment variable BUTLER_GITHUB_PROJECT is unset
      And the current repository owner and name cannot be determined (e.g., `gh` not installed or not authenticated, no `origin` remote)
      When a task-driven operation attempts to sync to a GitHub Projects item
      Then the warning message contains "no project configured for this repo" and does not include concrete setup commands

- [x] Scenario: Repo-specific suggestion is directly copy-pasteable
      Given a repository with owner "CmdrPrompt" and repository name "python-butler"
      And BUTLER_GITHUB_PROJECT is unset
      When the no-project-configured warning is displayed
      Then a user can copy the suggested `gh project create --owner CmdrPrompt --title python-butler` command directly from the output and paste it into their terminal without editing any part of it

## Out of scope
- Implementation of the full GitHub Projects sync feature (that is Requirement 4 overall; this task addresses only the warning enhancement)
- Testing the entire task-to-Projects workflow end-to-end
- Changes to the task file format, task workflow, or agent behavior (Workflow Guardian, Implementation Worker, etc.)
- Integration with GitHub's GraphQL API or `gh` CLI beyond what is needed to detect and report owner/repo in the warning message

## Blockers
None

## Completion
**Date:** 2026-07-31
**Summary:** When no `BUTLER_GITHUB_PROJECT` is configured, `_sync()` now attempts a best-effort,
read-only lookup of the current repository's owner/name (first `gh repo view --json owner,name`,
falling back to parsing `git remote get-url origin`) before building the warning. If the lookup
succeeds, the warning is extended with a directly copy-pasteable
`gh project create --owner <owner> --title <repo>` command and an
`export BUTLER_GITHUB_PROJECT=<number from the command above>` follow-up line. Any lookup failure
(gh not installed/authenticated, no origin remote, malformed JSON, or any other error) is caught
and the sync silently falls back to the previous generic warning, never raising. An existing
test in `tests/test_projects_cli.py` (`TestSyncProjectCliBestEffort::test_sync_project_merge_stage_exits_zero_when_no_project_configured`)
asserted zero `subprocess.run` calls when no project was configured; since this task
legitimately introduces a read-only lookup call on that path, the test was updated to assert no
*mutating* `gh project item-create`/`item-edit` calls occur instead, consistent with the
equivalent assertion already present in `tests/test_projects.py` from TASK-056.
**Files changed:**
- `src/butler_core/projects.py` - added `_lookup_owner_repo()` and
  `_parse_owner_repo_from_git_remote()`, and extended `_warning()`/`_sync()` to include the
  repo-specific setup suggestion when the owner/repo can be determined at runtime.
- `tests/test_projects_cli.py` - updated a pre-existing best-effort assertion (no longer asserts
  zero subprocess calls; asserts no mutating `gh project` write call) to match the legitimate
  behavior change.
- `CHANGELOG.md` - behavior-first entry (TASK-057).
- `REQUIREMENTS_TASK_WORKFLOW.md` - binding requirements update for this task (Requirement 4),
  confirmed prior to implementation per this task's precondition.

**Branch:** `git checkout task/057-enhance-no-project-warning`
**Stage:** `git add src/butler_core/projects.py tests/test_projects_no_project_warning.py tests/test_projects.py tests/test_projects_cli.py CHANGELOG.md docs/tasks/TASK-057-enhance-no-project-warning.md REQUIREMENTS_TASK_WORKFLOW.md`
**Commit:** `git commit -m "Include repo-specific setup commands in 'no project configured' warning"`
