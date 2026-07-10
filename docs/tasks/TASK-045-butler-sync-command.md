# TASK-045 Implement `butler sync` command to refresh vendored Makefile

## Status

todo

## Requirements

**Binding:** Requirement 3 from REQUIREMENTS_TASK_WORKFLOW.md
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer project maintainer, I want to refresh my project's vendored
`.butler/Makefile` when it drifts from the installed butler package version, so
that I don't have to manually diff and patch files by hand (as happened with
firefly-python-api before this command existed).

## Description

Implement a new CLI command, `butler sync`, that overwrites a consumer project's
`.butler/Makefile` with the version bundled in the currently installed `butler`
package, but only if the content actually differs. The command MUST compare the
actual content (via hash or diff) of the local `.butler/Makefile` against the
bundled version and report whether a change is needed (not unconditionally
report "would overwrite"). The command MUST refuse to run on a dirty working
tree unless `--force` is passed (consistent with REQUIREMENTS_UNINSTALL.md
Requirement 3), and MUST support `--dry-run` to preview changes.

This requires:
- Finding where the bundled `.butler/Makefile` is stored (likely in `butler`'s
  package data or installed files).
- Implementing content comparison logic (hash-based or diff-based).
- Implementing the `butler sync` subcommand in the CLI with `--dry-run` and
  `--force` flag support.
- Adding comprehensive tests covering all scenarios (content differs/matches,
  --dry-run behavior, --force override, dirty-tree detection).
- Updating CHANGELOG.md with behavior-first entry.

## Branch

**Branch name:** `task/045-butler-sync-command`
**Switch/create:** `git checkout -b task/045-butler-sync-command`
**Make target:** `make branch-task f=TASK-045`

## Acceptance criteria (Gherkin)

- [ ] Scenario: `butler sync --dry-run` reports that Makefile is up to date when content matches
      Given a consumer project with `.butler/Makefile` whose content exactly matches the bundled version
      When `butler sync --dry-run` is run
      Then the output reports ".butler/Makefile is already up to date; nothing to do" and the exit code is 0

- [ ] Scenario: `butler sync --dry-run` reports difference when content diverges
      Given a consumer project with `.butler/Makefile` whose content differs from the bundled version
      When `butler sync --dry-run` is run
      Then the output shows a difference (hash mismatch or diff summary, e.g. "would overwrite .butler/Makefile (local hash abc123 != bundled hash def456)") and the exit code is 0

- [ ] Scenario: `butler sync --dry-run` does not modify files
      Given a consumer project with `.butler/Makefile` that differs from the bundled version
      When `butler sync --dry-run` is run
      Then no files are modified; `.butler/Makefile` retains its original content

- [ ] Scenario: `butler sync` overwrites Makefile only if content differs
      Given a consumer project with `.butler/Makefile` whose content differs from the bundled version
      When `butler sync` is run
      Then `.butler/Makefile` is overwritten with the bundled version's content

- [ ] Scenario: `butler sync` does not overwrite Makefile if content matches
      Given a consumer project with `.butler/Makefile` whose content exactly matches the bundled version
      When `butler sync` is run
      Then `.butler/Makefile` is not modified

- [ ] Scenario: `butler sync` reports success when Makefile is already up to date
      Given a consumer project with `.butler/Makefile` whose content matches the bundled version
      When `butler sync` is run
      Then the output reports ".butler/Makefile is already up to date; nothing to do" and the exit code is 0

- [ ] Scenario: `butler sync` reports success when content differs and Makefile is updated
      Given a consumer project with `.butler/Makefile` whose content differs from the bundled version
      When `butler sync` is run
      Then the output confirms the update (e.g. "Updated .butler/Makefile") and the exit code is 0

- [ ] Scenario: `butler sync` refuses to run on a dirty working tree
      Given a consumer project with uncommitted changes in the working tree
      When `butler sync` is run without the `--force` flag
      Then the command fails with a message like "Working tree is dirty" or "Refusing to sync: working tree contains uncommitted changes" and the exit code is non-zero

- [ ] Scenario: `butler sync --force` overrides dirty-tree check
      Given a consumer project with uncommitted changes in the working tree and `.butler/Makefile` differs from the bundled version
      When `butler sync --force` is run
      Then `.butler/Makefile` is overwritten despite the dirty working tree and the exit code is 0

- [ ] Scenario: `butler sync --dry-run --force` respects both flags (dry-run takes precedence)
      Given a consumer project with uncommitted changes and `.butler/Makefile` that differs from the bundled version
      When `butler sync --dry-run --force` is run
      Then the dry-run behavior is honored (no files modified, output shows what would change), the exit code is 0

- [ ] Scenario: Dirty-tree check considers only working tree, not staging area
      Given a consumer project with staged changes but a clean working tree (no unstaged changes)
      When `butler sync` is run
      Then the command does not refuse; staged changes do not trigger the dirty-tree check

- [ ] Scenario: Dirty-tree check is gated by git status
      Given a consumer project where git status reports no uncommitted changes
      When `butler sync` is run
      Then the working-tree check passes and the command proceeds normally

- [ ] Scenario: Bundled Makefile is located and compared correctly
      Given the currently installed `butler` package
      When `butler sync --dry-run` is run
      Then the command locates the bundled `.butler/Makefile` from the package and compares it against the local version

- [ ] Scenario: CHANGELOG.md updated with behavior-first entry
      Given a current CHANGELOG.md
      When this task is completed
      Then CHANGELOG.md contains a new entry describing the `butler sync` command added

- [ ] Scenario: Tests pass and coverage maintained
      Given the existing test suite with current coverage baseline
      When `make test` and `make lint` are run after implementation
      Then all tests pass and code coverage does not decrease below the baseline

## Out of scope

- Syncing any vendored files other than `.butler/Makefile` (e.g. governance docs, agents). This task focuses on the Makefile only.
- Changing the `git subtree add` adoption mechanism itself — only refreshing the Makefile within an already-adopted project.
- Automatically running `butler sync` as part of `butler install` or other setup commands. The sync command is opt-in and must be run explicitly by the consumer project maintainer.
- Fixing already-vendored `.butler/Makefile` copies in existing consumer repos before they run `butler sync` — that's their responsibility once this command ships.

## Blockers

None

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/045-butler-sync-command`
**Stage:**
**Commit:**
