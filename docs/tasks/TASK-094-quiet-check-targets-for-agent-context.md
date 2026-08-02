# TASK-094 Quiet check targets so agent runs stop filling context with passing-check output

## Status
done

## Requirements
**Binding:** Requirement 2 (REQUIREMENTS_AGENT_SKILLS.md)
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer paying for agent runs, I want the checks an agent runs on every
TDD iteration to print only what a failure needs, so that a task's context does
not fill up with coverage tables and complexity listings for code that already
passes.

## Description
Usage measurement over 24h attributed 41% of token spend to Implementation
Worker subagents, and 34% of spend to requests at >150k context. The agent
already runs on `model: sonnet`, so the cost is not model choice — it is how
much output each run accumulates.

The Implementation Worker's own prompt forbids piping command output through
`| tail`/`| head`/`| grep` to shorten it, because a piped command can fall
outside the pre-approved Bash allowlist and silently stall a subagent's turn
with no result. That rule is correct and stays. Its consequence is that the
only place output can be reduced is inside the Makefile.

The verbose parts on a *successful* run are:

- `make test` — `--cov-report=term-missing` prints a coverage row for every
  file in `src/`, including fully-covered ones, plus a line per passing test.
- `make bdd` — `-v` prints a line per passing scenario.
- `make lint` — `complexipy -s desc` prints every analysed function with its
  score; `bandit` prints a full metrics report.

None of that carries diagnostic value when the run is green, and the
Red -> Green -> Refactor loop reruns it several times per task.

Add agent-facing quiet variants that run the same commands with different
output flags, plus one combined target so the agent spends one Bash call
instead of three. `make lint`, `make test` and `make bdd` keep their current
output verbatim — CI (`.github/workflows/ci.yml`) calls them by name and must
be unaffected.

Note for implementation: `src/butler_core/data/Makefile` is a vendored copy of
the root `Makefile` and `tests/test_sync.py` fails on drift, so it must be
re-copied. `claude-agents/` and `.claude/agents/` must stay byte-identical
(`make check-agents-sync`), and `templates/implementation-worker.agent.md.tmpl`
generates the Copilot-flavoured agent file separately.

## Branch
**Branch name:** `task/094-quiet-check-targets-for-agent-context`
**Switch/create:** `git checkout -b task/094-quiet-check-targets-for-agent-context`
**Make target:** `make branch-task f=TASK-094`

## Acceptance criteria (Gherkin)
**Feature files:** None

- [x] 1. Scenario: The quiet test target keeps the coverage total but drops fully-covered files
      Given the repo's tests all pass
      When `make test-quiet` runs
      Then the command exits 0
      And the output contains the `TOTAL` coverage row
      And the output contains no coverage row for a file at 100% coverage
      And the output contains no line naming an individual passing test
- [x] 2. Scenario: The quiet lint target drops the per-function complexity listing
      Given no function in `src/` exceeds the complexity threshold of 15
      When `make lint-quiet` runs
      Then the command exits 0
      And the output contains no per-function complexity score line
- [x] 3. Scenario: The quiet BDD target drops passing scenario names
      Given `tests/bdd/` exists and all scenarios pass
      When `make bdd-quiet` runs
      Then the command exits 0
      And the output contains no line naming an individual passing scenario
- [x] 4. Scenario: A failing check is still identifiable in quiet output
      Given one test in `tests/` fails
      When `make test-quiet` runs
      Then the command exits non-zero
      And the output names the failing test and its file
- [x] 5. Scenario: One combined target runs every check
      Given the repo is green
      When `make verify` runs
      Then the command exits 0
      And lint, tests and BDD scenarios have all been run
- [x] 6. Scenario: The verbose targets are unchanged
      Given the Makefile with the quiet variants added
      When `make -n lint`, `make -n test` and `make -n bdd` are expanded
      Then each expands to the same command lines as before the quiet variants
      were introduced
- [x] 7. Scenario: The vendored Makefile copy does not drift
      Given the root `Makefile` has been modified
      When `make test` runs
      Then `tests/test_sync.py`'s drift check passes, because
      `src/butler_core/data/Makefile` was re-copied from the root `Makefile`
- [x] 8. Scenario: The Implementation Worker uses the quiet targets
      Given the Implementation Worker definition
      When its Implementation Rules are read
      Then `make verify` is named as the completion gate
      And `make test-quiet` is named for use inside the TDD loop
      And the rule forbidding shell pipes to shorten output is still present
      And `claude-agents/` and `.claude/agents/` remain byte-identical

## Out of scope
- Changing any agent's `model:` field. Implementation Worker is already on
  `sonnet`; downgrading the agent that writes code trades correctness for a
  small saving and is a separate decision.
- The same treatment for `Test Writer` and `Characterization Test Writer`,
  which carry the same `make lint && make test` instruction but together
  account for ~5% of usage.
- Reducing how much context the Implementation Worker is *given* at spawn
  time, or how often the Workflow Guardian spawns it.
- Fixing the pre-existing mismatch between `clean-complexity`'s
  `complexipy_results_*.json` glob and the `complexipy-results.json` file that
  `complexipy -j` actually writes.

## Blockers
None

## Completion
**Date:** 2026-08-03
**Summary:** Added `lint-quiet`, `test-quiet`, `bdd-quiet` and a combined
`verify` target. Each delegates to its verbose counterpart via
command-line-overridden verbosity variables (`RUFF_QUIET`, `MYPY_QUIET`,
`BANDIT_QUIET`, `COMPLEXIPY_QUIET`, `PYTEST_COV_REPORT`,
`PYTEST_EXTRA_FLAGS`, `BDD_QUIET`), all defaulting to empty/full-output so
`make lint`, `make test` and `make bdd` are byte-unchanged for humans and
CI (verified via `make -n` dry-run diffing against the pre-change
Makefile). `test-quiet` uses `--cov-report=term:skip-covered -q
--no-header --tb=short`, which keeps the `TOTAL` row (coverage-baseline
comparisons still work) while dropping fully-covered files and passing
test names; a failing test still prints its name and file. `lint-quiet`
uses `--failed`/`--quiet`/`--no-error-summary` on the underlying tools to
drop the per-function complexity listing. `bdd-quiet` sets `BDD_QUIET=1`,
which switches `bdd`'s own pytest invocation from `-v` to `-q --no-header
--tb=short`. The Implementation Worker (`.claude/agents/` and
`claude-agents/`, kept byte-identical) now names `make verify` as its
completion gate and `make test-quiet` for the inner TDD loop, while the
pipe-forbidding rule (`| tail`/`| head`/`| grep`) stays in place — the
quiet targets are the sanctioned way to shrink output instead.
`src/butler_core/data/Makefile` was re-copied to keep `tests/test_sync.py`
green. Discovered and fixed a real hermeticity bug while writing
`tests/test_quiet_check_targets.py`'s baseline-diff test: Make re-exports
command-line variable overrides to every nested `make`/subprocess via
`MAKEFLAGS`, so running the new test suite nested inside `make verify`
(itself running `make test-quiet` -> `pytest tests/`) leaked
`PYTEST_COV_REPORT`/`PYTEST_EXTRA_FLAGS` into the test's own `make -n test`
dry-run comparison; fixed by stripping the verbosity vars and `MAKEFLAGS`/
`MFLAGS` from the subprocess environment before each dry run. Confirmed
end-to-end by running `make verify` directly (not via a test) and
observing it pass, including the nested `make test-quiet` run of this
task's own test file.

CI caught a second hermeticity issue after the PR was opened: the
Scenario 6 baseline comparison used `git show 64ae502:Makefile`, which
fails with exit 128 in CI's shallow (`fetch-depth: 1`) checkout because
that commit isn't fetched. Fixed by checking in
`tests/fixtures/Makefile.baseline` (a static snapshot of the pre-quiet-
variant Makefile) and comparing against that file instead of git
history.
**Files changed:**
- `Makefile` - added `lint-quiet`, `test-quiet`, `bdd-quiet`, `verify` targets and their verbosity-knob variables
- `src/butler_core/data/Makefile` - re-synced copy of the root Makefile
- `.claude/agents/implementation-worker.agent.md` / `claude-agents/implementation-worker.agent.md` - reference the quiet targets in Implementation Rules and Output Contract
- `templates/implementation-worker.agent.md.tmpl` - Copilot-flavoured agent file updated to match
- `REQUIREMENTS_AGENT_SKILLS.md` - added Requirement 2
- `tests/test_quiet_check_targets.py` - created, covers all 8 acceptance scenarios
- `tests/fixtures/Makefile.baseline` - checked-in pre-quiet-variant Makefile snapshot, used by the Scenario 6 test instead of `git show` (CI's shallow checkout doesn't have the historical commit)
- `CHANGELOG.md` - added entry
**Branch:** `git checkout task/094-quiet-check-targets-for-agent-context`
**Stage:** `Makefile src/butler_core/data/Makefile claude-agents/implementation-worker.agent.md .claude/agents/implementation-worker.agent.md templates/implementation-worker.agent.md.tmpl REQUIREMENTS_AGENT_SKILLS.md CHANGELOG.md tests/test_quiet_check_targets.py tests/fixtures/Makefile.baseline docs/tasks/TASK-094-quiet-check-targets-for-agent-context.md`
**Commit:** `git commit -m "Add quiet check targets so agent runs stop filling context with passing-check output (TASK-094)"`
