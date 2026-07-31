# Requirements: Reusable Python CI Workflow

## Context

Consumer projects (e.g. `firefly-bank-importer`) call a reusable GitHub
Actions workflow to run their lint/test/audit gate on pull requests, in
the form:

```yaml
jobs:
  ci:
    uses: CmdrPrompt/python-commons/.github/workflows/python-ci.yml@main
    with:
      python-version: "3.11"
      install-command: "uv sync --extra dev"
      lint-command: "make lint"
      test-command: "make test"
      audit-command: "uv run pip-audit --progress-spinner=off"
```

This workflow file never existed in `python-butler` (formerly
`python-commons` before the GitHub repo rename) — `git log --all -- "*python-ci*"`
in this repo returns nothing. The only workflow currently in
`.github/workflows/ci.yml` here is `validate-agents`, which validates this
repo's own agent definitions and takes no inputs.

As a result, every consumer PR that references the missing
`python-ci.yml` fails immediately (0s runtime) with "This run likely
failed because of a workflow file issue" — CI has never actually run
lint/test/audit for that consumer, regardless of what the PR's own commits
contain.

## Goals

1. Add a reusable, `workflow_call`-triggered workflow to this repo at
   `.github/workflows/python-ci.yml` that consumer repos can invoke via
   `uses: CmdrPrompt/python-butler/.github/workflows/python-ci.yml@main`.
2. Accept the same input contract already assumed by consumer callers
   today (see Context above), so existing consumer `ci.yml` files only
   need their `uses:` target updated (`python-commons` → `python-butler`),
   not their `with:` block.
3. Fail the calling PR's check when lint, test, or audit fails — same
   semantics a consumer would get running these commands directly.

## Non-goals

- Migrating `firefly-bank-importer`'s `.github/workflows/ci.yml` — that
  change happens in that repo, after this workflow exists here and is
  confirmed working.
- Changing the existing `validate-agents` workflow/job in this repo's own
  `ci.yml` — it stays as-is, this is an additional, separate reusable
  workflow file.
- Supporting non-`uv` install commands, matrix Python versions, or caching
  strategies beyond what's needed to satisfy the existing input contract.

## Requirement 1: Reusable `workflow_call` workflow with the existing input contract

**Description:** `.github/workflows/python-ci.yml` declares
`on: workflow_call:` with five `inputs`: `python-version` (string,
required), `install-command` (string, required), `lint-command` (string,
required), `test-command` (string, required), `audit-command` (string,
optional — audit step is skipped if not provided). A single job checks out
the caller's repo, sets up the given Python version, runs
`install-command`, then `lint-command`, then `test-command`, then
`audit-command` (if set), each as a separate step so failures are
attributable to the right step in the Actions UI.

**Use case:** `firefly-bank-importer`'s `.github/workflows/ci.yml` (after
its own `uses:` line is repointed to
`CmdrPrompt/python-butler/.github/workflows/python-ci.yml@main`) opens a
PR with a failing `make lint`. The reusable workflow's lint step fails,
the PR check goes red, and the Actions log clearly shows the lint step
(not install or test) as the failure point.

## Requirement 2: Correct failure propagation

**Description:** If any of install/lint/test/audit fails, the job fails
and the calling workflow's check fails — no step is allowed to swallow a
non-zero exit code (e.g. no unguarded `|| true`).

**Use case:** A consumer's `make test` exits non-zero due to a real test
failure. The PR's required "CI" check must show as failed, blocking merge
under standard branch protection, not silently pass.

## Acceptance criteria (overall)

- [ ] `.github/workflows/python-ci.yml` exists in this repo, triggered by
      `workflow_call`, accepting `python-version`, `install-command`,
      `lint-command`, `test-command` (required) and `audit-command`
      (optional) inputs.
- [ ] A consumer repo's `ci.yml` with `uses:
      CmdrPrompt/python-butler/.github/workflows/python-ci.yml@main` and
      the same `with:` block shown in Context runs successfully end-to-end
      (checkout → install → lint → test → audit) against a real consumer
      PR.
- [ ] A failing lint/test/audit command in the caller causes the calling
      PR's check to fail, with the failure attributable to the specific
      step in the Actions log.
- [ ] Omitting `audit-command` skips the audit step without failing the
      job.
