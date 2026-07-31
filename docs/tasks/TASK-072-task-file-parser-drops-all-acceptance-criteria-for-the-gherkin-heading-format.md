# TASK-072 Task-file parser drops all acceptance criteria for the Gherkin heading format

## Status
done

## Requirements
**Binding:** Requirement 1 (REQUIREMENTS_MCP.md); BDD-025 (REQUIREMENTS_BDD.md)
**BDD mode:** BDD-ABSENT (bug fix; no new requirement text needed — Requirement
1 already commits to the contract this restores)
**Depends on:** None
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer or agent reading a task's structured data (via `butler task
show`, `butler-mcp`'s `get_task`/`list_tasks`, or any other caller of
`butler_core.tasks.read_task`), I want the returned `acceptance_criteria`
list to reflect what is actually written in the task file, so that I can
trust `Task.acceptance_criteria` instead of it silently and always being
empty for every task file drafted since the BDD template rollout.

## Description
**Bug (found live, 2026-08-01, while completing TASK-068's workflow steps):**
`butler_core.tasks._section()` (src/butler_core/tasks.py:51-54) locates a
section with the regex `^## {heading}\s*\n`. `parse_task` calls it as
`_section(text, "Acceptance criteria")` (tasks.py:104). BDD-025
(REQUIREMENTS_BDD.md) changed the task template's heading to `## Acceptance
criteria (Gherkin)` — every task file from TASK-043 onward uses this exact
heading (confirmed: 25 of the 72 task files in `docs/tasks/`, vs. 47 using
the older plain `## Acceptance criteria`). `\s*` does not match the literal
`(Gherkin)` suffix, so the regex never matches these 25 files, `_section`
returns `""`, and `parse_task` sets `acceptance_criteria=[]` regardless of
what the file actually contains.

Reproduced live against TASK-068's own file (which has the `(Gherkin)`
heading and, at the time of reproduction, several checked criteria):
`butler task show TASK-068` printed `Acceptance criteria:` with nothing
listed underneath.

This is a **read-path-only** bug — the following are unaffected because they
don't go through `_section`/`parse_task`:
- `butler_core.tasks.check_criterion` (tasks.py:221) scans the whole file
  text directly for `^- \[( |x)\] .+$` lines, so `butler task check` /
  `butler-mcp`'s `check_acceptance_criterion` still correctly check the
  right box.
- `butler_core.projects._extract_section` (projects.py:276) matches with
  `line.startswith(f"## {heading}")`, a prefix check that tolerates the
  `(Gherkin)` suffix, so the GitHub Projects item body (Requirement 11)
  correctly includes the Acceptance criteria section.

But every *reader* of `Task.acceptance_criteria` is affected: `butler task
show`'s criteria listing, `butler-mcp`'s `get_task`/`list_tasks` tool
results (REQUIREMENTS_MCP.md Requirement 1's own doctested contract —
`assert all(c.checked for c in task.acceptance_criteria)` — cannot pass for
any current-format task file, since the list is always empty), and any
future caller (e.g. Workflow Guardian verifying criteria before checking
them off) that relies on `read_task`/`list_tasks` instead of re-parsing the
file itself.

**Proposed fix:** Make `_section`'s heading match tolerant of a trailing
suffix on the heading line (e.g. match `^## {heading}.*\n`, mirroring
`_extract_section`'s prefix-based approach in projects.py), so `## Acceptance
criteria (Gherkin)` and any other future suffixed heading is still found.
Add regression coverage (Hypothesis-based, per CLAUDE.md's TDD rules for
parsing functions) asserting `parse_task` returns non-empty, correctly
`checked`-flagged `acceptance_criteria` for both the plain and
`(Gherkin)`-suffixed heading forms.

**Implementation location:** `src/butler_core/tasks.py` (`_section`),
`tests/test_tasks.py`.

## Branch
**Branch name:** `task/072-task-file-parser-drops-all-acceptance-criteria-for-the-gherkin-heading-format`
**Switch/create:** `git checkout -b task/072-task-file-parser-drops-all-acceptance-criteria-for-the-gherkin-heading-format`
**Make target:** `make branch-task f=TASK-072`

## Acceptance criteria (Gherkin)

- [x] Scenario: `read_task` returns non-empty acceptance criteria for the current Gherkin-heading template
      Given a task file whose acceptance criteria section is headed
      `## Acceptance criteria (Gherkin)` and contains one checked and one
      unchecked `- [ ]`/`- [x]` line
      When `butler_core.tasks.read_task` (or `parse_task`) reads that file
      Then the returned `Task.acceptance_criteria` contains both criteria
      with their correct `text` and `checked` values, matching what
      `butler task show` and `butler-mcp`'s `get_task`/`list_tasks` display

- [x] Scenario: Older plain-heading task files keep working unchanged
      Given a task file whose acceptance criteria section is headed
      `## Acceptance criteria` (no suffix), the format used by task files
      before TASK-043
      When `read_task` reads that file
      Then the returned `acceptance_criteria` is unchanged from today's
      behavior (no regression for the legacy heading form)

- [x] Hypothesis-based regression coverage exists for `_section`/
      `parse_task`'s heading matching across both heading forms, per
      CLAUDE.md's rule that parsing/data-transformation functions use
      Hypothesis

- [x] make lint && make test pass, with coverage not below the task-start
      baseline

- [x] CHANGELOG.md updated

## Out of scope
- Changing the task file template or heading text itself — this task only
  fixes the parser to correctly read the template that BDD-025 already
  established.
- `butler_core.projects._extract_section` and `check_criterion` — both
  already handle the `(Gherkin)` suffix correctly and need no change.
- Auditing other `_section()` callers (`Description`, `Branch`,
  `Completion`) for similar suffix drift — none currently use a suffixed
  heading in any task file, but the fix's regex change will cover them too
  if that ever happens.

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Fixed `_section()` in `src/butler_core/tasks.py` to match a
heading's trailing suffix with `[^\n]*` instead of `\s*`, so `## Acceptance
criteria (Gherkin)` (and any other suffixed heading) is found the same way
`## Acceptance criteria` always was. Chose `[^\n]*` rather than a DOTALL-`.*`
suffix match: with `re.DOTALL` already active for the section body capture,
a bare `.*` before the first `\n` would greedily cross line boundaries and
backtrack from the end of the whole file looking for a `\n`, potentially
matching far past the intended heading line before backing off — bounding
the suffix match to `[^\n]*` keeps it on the heading's own line regardless
of `DOTALL`. Added a Hypothesis-parametrized regression test
(`test_parse_task_finds_acceptance_criteria_regardless_of_heading_suffix`)
covering both the plain and `(Gherkin)`-suffixed heading forms, plus a
concrete `read_task`-level test reproducing TASK-068's live symptom.
Confirmed red before the fix (both new tests failed), green after. Full
suite: 314 passed, coverage 98% on `tasks.py` (unchanged from baseline).
**Files changed:**
- `src/butler_core/tasks.py` - widened `_section()`'s heading match to tolerate a trailing suffix
- `tests/test_tasks.py` - added Hypothesis and concrete regression coverage
- `CHANGELOG.md` - documented the fix
- `docs/tasks/TASK-072-task-file-parser-drops-all-acceptance-criteria-for-the-gherkin-heading-format.md` - checked off criteria, completion
**Branch:** `git checkout task/072-task-file-parser-drops-all-acceptance-criteria-for-the-gherkin-heading-format`
**Stage:** `git add src/butler_core/tasks.py tests/test_tasks.py CHANGELOG.md docs/tasks/TASK-072-task-file-parser-drops-all-acceptance-criteria-for-the-gherkin-heading-format.md`
**Commit:** `git commit -m "Fix task-file parser to find Acceptance criteria sections with a Gherkin-suffixed heading"`
