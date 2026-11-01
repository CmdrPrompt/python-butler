# TASK-097 `CLAUDE.md.tmpl` routes to skills instead of restating them

## Status
done

## Requirements
**Binding:** Requirements 1-5 (REQUIREMENTS_CLAUDE_MD_ROUTING.md)
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of python-butler and its consumer projects, I want the
generated `CLAUDE.md` to state only the rules no skill owns and point to the
skills for the rest, so that every session preloads less duplicated text and
the two copies of each rule can no longer drift apart.

## Description
`templates/CLAUDE.md.tmpl` renders to 122 lines in every consumer and
restates the `commit-workflow`, `tdd-cycle` and `changelog` skills, with two
stale details (`git merge main` instead of `make sync-main`, and
`.github/agents/` paths). python-butler has no `CLAUDE.md` of its own and
relies on the user's global `~/.claude/CLAUDE.md`, which is therefore also
loaded on top of every consumer's own copy.

Trim the template to route to skills while keeping its section headings (so
BDD-040, `REQUIREMENTS_CROSS_WORKSPACE.md` Requirement 1 and
`REQUIREMENTS_TASK_WORKFLOW.md` Requirement 10 stay satisfied), track a
python-butler `CLAUDE.md` rendered from it with a drift test, and shorten
the five shipped skill descriptions. Consumers pick this up through the
existing `make butler-pull` → `make generate-governance-files FORCE=1` flow.

## Branch
**Branch name:** `task/097-claude-md-template-routes-to-skills`
**Switch/create:** `git checkout -b task/097-claude-md-template-routes-to-skills`
**Make target:** `make branch-task f=TASK-097`

## Acceptance criteria (Gherkin)
**Feature files:** None

- [x] 1. Scenario: Template names skills instead of restating skill-owned content
      Given `templates/CLAUDE.md.tmpl`
      When it is read
      Then it contains no task workflow code block, no changelog rule list,
      no coverage-baseline rule and no "Bug Discovery" section
      And it names the skills `commit-workflow`, `task-file-format`,
      `tdd-cycle` and `changelog`
- [x] 2. Scenario: Template keeps every rule no skill owns
      Given `templates/CLAUDE.md.tmpl`
      When it is read
      Then it keeps the spec-first gate with "Is this what you intended?",
      the Workflow Guardian auto-apply and `make`/`butler`/`butler-mcp`
      statements in "Task Management", the `task/<NNN>-short-description`
      branch policy, the Hypothesis rule, the Cross-Workspace Boundary
      section, the BDD section and the What NOT to Do rules (lint/test,
      dependencies, `# type: ignore`, raw `git commit`)
- [x] 3. Scenario: Generated CLAUDE.md is at most 70 lines
      Given a consumer project with no prior `CLAUDE.md`
      When `make generate-governance-files ENABLE_BDD=1` runs
      Then the generated `CLAUDE.md` is at most 70 lines excluding the H1
      and the description paragraph
- [x] 4. Scenario: Template references match what a generated project has
      Given `templates/CLAUDE.md.tmpl`
      When it is read
      Then it says `make sync-main` and not `git merge main`
      And it names no `.github/agents/` path
- [x] 5. Scenario: python-butler's CLAUDE.md matches the rendered template
      Given python-butler's tracked root `CLAUDE.md`
      When the template is rendered with `ENABLE_BDD=1`,
      `PROJECT_NAME=python-butler`, python-butler's description and
      `REQUIREMENTS_PATH` set to the root `REQUIREMENTS_*.md` files
      Then the two are identical
      And on a difference the test fails with a message saying how to
      regenerate the file
- [x] 6. Scenario: Skill descriptions are at most 200 characters
      Given the shipped skills `changelog`, `characterization-tests`,
      `commit-workflow`, `task-file-format` and `tdd-cycle`
      When their `description:` lines are read
      Then each is at most 200 characters and still states when to use the
      skill
      And `make check-skills-sync` passes
- [x] 7. Scenario: Existing governance-template behavior is unchanged
      Given the existing tests for BDD-040, project-identity preservation,
      file gating and template variable shell safety
      When `make test` runs
      Then they pass unchanged

## Out of scope
- `templates/copilot-instructions.md.tmpl` and `.github/agents/`.
- The `generate-governance-files` recipe, its variables, and project-identity
  preservation.
- Agent files and skill bodies.
- Regenerating consumer repos' `CLAUDE.md` (each does it via its own task).
- The user's global `~/.claude/CLAUDE.md` (outside this repo).

## Blockers
None

## Completion
**Date:** 2026-11-01
**Summary:** `templates/CLAUDE.md.tmpl` now renders to 68 lines (was 118,
excluding title and description). Section headings are unchanged so BDD-040,
Cross-Workspace Requirement 1 and Task Workflow Requirement 10 stay satisfied
with their existing tests. Changelog, task-file, TDD-mechanics and
commit-flow details are replaced by the skill names; the separate Changelog
and Bug Discovery sections are gone (the changelog pointer moved into the
Task Management flow line). `git merge main` became `make sync-main` and the
`.github/agents/` paths became `.claude/agents/workflow-guardian.agent.md`.
`BUG_TRIAGE_NAME` is still substituted by the generator but no longer used by
the template; the generator was left untouched per the non-goals.
python-butler's root `CLAUDE.md` is rendered through the real generator in a
fixture consumer (the root Makefile reads `.butler/templates/`, which does
not exist in python-butler itself); `BUTLER_REGEN_CLAUDE_MD=1 uv run pytest
tests/test_claude_md_routing.py` rewrites it. Skill descriptions are now
129-167 characters. Coverage 99% (815/9) at start and at completion.
Process notes: the task file was drafted in the main conversation (Task
Drafter fallback: the requirements file was not yet committed, so a worktree
drafter could not see it), and implementation was done in the main
conversation instead of via Implementation Worker.
**Files changed:**
- `templates/CLAUDE.md.tmpl` - modified
- `CLAUDE.md` - created
- `claude-skills/*/SKILL.md`, `.claude/skills/*/SKILL.md` (5 each) - modified (description only)
- `tests/test_claude_md_routing.py` - created
- `CHANGELOG.md` - modified
**Branch:** `git checkout task/097-claude-md-template-routes-to-skills`
**Stage:** `templates/CLAUDE.md.tmpl CLAUDE.md claude-skills/changelog/SKILL.md claude-skills/characterization-tests/SKILL.md claude-skills/commit-workflow/SKILL.md claude-skills/task-file-format/SKILL.md claude-skills/tdd-cycle/SKILL.md .claude/skills/changelog/SKILL.md .claude/skills/characterization-tests/SKILL.md .claude/skills/commit-workflow/SKILL.md .claude/skills/task-file-format/SKILL.md .claude/skills/tdd-cycle/SKILL.md tests/test_claude_md_routing.py docs/tasks/TASK-097-claude-md-template-routes-to-skills.md CHANGELOG.md`
**Commit:** `git commit -m "Trim CLAUDE.md template to route to skills and give python-butler its own CLAUDE.md (TASK-097)"`
