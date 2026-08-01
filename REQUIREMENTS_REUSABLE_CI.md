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
optional — audit step is skipped if not provided). Install, Lint, Test, and
Audit each run as their **own job** (`install`, `lint`, `test`, `audit`),
`needs`-chained in that order, rather than as steps within one job — each
checks out the caller's repo, sets up the given Python version and `uv`,
and re-runs `install-command` (fast, since `astral-sh/setup-uv`'s
`enable-cache: true` restores the resolved packages from cache so repeat
installs don't re-download anything) before its own Lint/Test/Audit step.
This is purely an internal restructuring of this workflow — the
`workflow_call` input contract consumers pass under `with:` is unchanged.

**Use case:** `firefly-bank-importer`'s `.github/workflows/ci.yml` opens a
PR with a failing `make lint`. Instead of a single "ci / ci" check that
must be opened to see which step failed, the PR's checks list shows
separate "ci / lint", "ci / test", "ci / audit" entries — `lint` shows red
at a glance, `test`/`audit` show as skipped (since they `needs: lint`),
without opening any logs.

## Requirement 2: Correct failure propagation

**Description:** If any of install/lint/test/audit fails, the job fails
and the calling workflow's check fails — no step is allowed to swallow a
non-zero exit code (e.g. no unguarded `|| true`).

**Use case:** A consumer's `make test` exits non-zero due to a real test
failure. The PR's required "CI" check must show as failed, blocking merge
under standard branch protection, not silently pass.

## Requirement 3: `uv` is available before the install step runs

**Description:** The reusable workflow's `install-command` input is, in
practice, always a `uv` invocation (`uv sync --extra dev`), since every
current and expected consumer manages dependencies with `uv`. The workflow
sets up a `uv` toolchain (e.g. via `astral-sh/setup-uv`) before the Install
step runs, so `install-command` does not fail with `uv: command not found`.

**Use case:** `firefly-bank-importer`'s PR #38 (first real end-to-end run of
this reusable workflow, after repointing its `uses:` from the renamed
`python-commons` to `python-butler`) fails at the Install step with
`uv: command not found` (exit 127) — `uv` was never installed on the
runner. Once this requirement is met, the same PR's Install step succeeds
and proceeds to Lint/Test/Audit.

## Requirement 4: Consumer submodules are checked out

**Description:** The `actions/checkout@v4` step checks out the caller's repo
with `submodules: true` (or `recursive`), so a consumer whose build depends
on a git submodule (e.g. `.butler`) has that submodule's contents present
before Install/Lint/Test/Audit run.

**Use case:** `firefly-bank-importer`'s PR #38, after Requirement 3 is met,
fails at the Lint step with `Makefile:1: .butler/Makefile: No such file or
directory` — `.butler` is a git submodule (TASK-054) and the checkout step
left it as an empty directory. Once this requirement is met, the same PR's
checkout populates `.butler` and the Lint step can `include .butler/Makefile`.

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
- [ ] The workflow sets up `uv` before the Install step, so a `uv`-based
      `install-command` succeeds without `uv: command not found`.
- [ ] The checkout step fetches the caller's submodules, so a consumer with
      a git submodule dependency (e.g. `.butler`) has it populated before
      Install/Lint/Test/Audit run.
- [ ] Install, Lint, Test, and Audit each run as their own `needs`-chained
      job, so a PR's checks list shows them as separate entries instead of
      one combined "ci / ci" check.
