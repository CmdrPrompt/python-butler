# TASK-036 Close validate_agents.py gaps found during TASK-035 test review

## Status

todo

## Description

The Test Design Reviewer's review of TASK-035's new characterization tests
(`tests/test_validate_agents.py`, `tests/test_hooks.py`) flagged two gaps in
`scripts/validate_agents.py` / `.claude/hooks/agent_result_gate.py` that were
deliberately left uncharacterized (characterization tests document existing
behavior as-is, they do not fix it):

1. **Missing `tools:` key is not flagged, only an empty one is.**
   `validate_file()` only requires `name` and `description` (`REQUIRED_KEYS`).
   If an `.agent.md` file has no `tools:` line at all, `validate_file()`
   reports zero errors — but `tools: []` (present and empty) is reported as
   `"'tools' is empty (agent will have no tools)"`. Since the entire point of
   this validator is to catch configurations that leave a subagent with no
   real tools (the TASK-025/TASK-034 root cause), an entirely absent `tools:`
   key produces the same "no tools" runtime outcome as an empty list, but
   currently passes validation silently. Decide whether `tools` should become
   a required key (fails validation if absent), and implement accordingly.
   See `tests/test_validate_agents.py::TestValidateFile::test_no_tools_key_at_all_is_not_reported_as_an_error`,
   which currently documents (not endorses) this gap.

2. **`agent_result_gate.py`'s "validator not found" fallback path is untested.**
   When `scripts/validate_agents.py` does not exist at
   `$CLAUDE_PROJECT_DIR/scripts/validate_agents.py`, the gate falls back to
   the literal string `"validator not found (scripts/validate_agents.py
   missing)"` instead of running the validator. This path exists in the code
   but has no test coverage. Add a test exercising it (e.g. a `project_dir`
   fixture with no `scripts/` directory at all) to `tests/test_hooks.py`,
   asserting the fallback string appears in the embedded validation result.

**Depends on:** TASK-035 (must land first; this task edits code TASK-035 introduces)

## Branch

**Branch name:** `task/036-validate-agents-missing-tools-key-gap`
**Switch/create:** `git checkout -b task/036-validate-agents-missing-tools-key-gap`
**Make target:** `make branch-task f=TASK-036`

## Acceptance criteria

- [ ] Decision recorded (in this task's Completion summary) on whether `tools:` becomes a required key in `scripts/validate_agents.py`
- [ ] If made required: a missing `tools:` key now produces a `validate_file()` error, and `tests/test_validate_agents.py::test_no_tools_key_at_all_is_not_reported_as_an_error` is updated to assert the new (fixed) behavior instead of documenting the gap
- [ ] `tests/test_hooks.py` gains a test exercising `agent_result_gate.py`'s "validator not found" fallback string
- [ ] `make validate-agents` still exits 0 against the real `.claude/agents/*.agent.md` files after any change
- [ ] `make lint && make test` pass

## Completion

**Date:**
**Summary:**
