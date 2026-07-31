# TASK-064 Investigate PR traceability from the GitHub Projects board (Linked pull requests / real Created-Closed dates)

## Status
done

## Requirements
**Binding:** Requirement 4 (REQUIREMENTS_TASK_WORKFLOW.md); related to Requirement 8
**BDD mode:** BDD-ABSENT (investigation task — no requirement text confirmed yet, see below)
**Depends on:** None (references the finding from TASK-062's Completion; not blocked by it)
**Precedence:** The requirements document is the binding definition of what the
GitHub Projects sync must currently do. This task does NOT add or change any
requirement text itself — its job is to investigate and produce a
recommendation. Any resulting behavior change MUST go through a
Requirements Drafter round and explicit user confirmation before
implementation, per CLAUDE.md's spec-driven development rule. Do not build
production code from this task file alone.

## Story (context, not binding)
As a maintainer looking at the GitHub Projects board, I want to be able to
find the pull request behind a task item directly from the board (e.g. via
the "Linked pull requests" field, or an equivalent), so I don't have to
search GitHub by TASK-ID or title to find the right PR after the fact.

## Description
**Finding (confirmed live against this repo's own Project #2, 2026-07-31):**
GitHub Projects v2's built-in "Linked pull requests" field — and, as a
closely related discovery, the also-built-in "Created"/"Closed" fields that
TASK-062's `--stage backfill` writes to — are all `ProjectV2Field` **system**
fields, not custom fields. They are derived/read-only and CANNOT be set via
`gh project item-edit`'s `--text`/`--date`/`--number`/`--single-select-option-id`
flags. A live test against this repo's Project confirmed the GraphQL error:

```text
GraphQL: The field of type created is currently not supported. (updateProjectV2ItemFieldValue)
```

`gh project field-list`'s output does not distinguish "this is a read-only
system field" from "this is a field you can write to" in its `type` value
(both show as `ProjectV2Field` for plain-text-shaped fields) — code and
future task authors relying on `field-list` alone will keep hitting this.

**Related, already-confirmed bug (not this task's to fix, but must be
carried forward):** `_backfill_dates()` in `src/butler_core/projects.py`
(added by TASK-062) calls `_item_edit_date()` for the "Created"/"Closed"
fields and never checks its return code, so when the field-write silently
fails (as it always will against a project using the built-in system
fields, per the finding above), `sync_on_pr_backfill` still reports success
with a "created: <date>"/"closed: <date>" message that was never actually
written to the board. This needs its own bug task (do not fold its fix into
this investigation task) once this investigation's recommendation is
confirmed, so the fix can account for whichever direction is chosen below.

**What this task must produce:** a written recommendation (not necessarily
code) choosing between the two realistic approaches, with tradeoffs, so a
Requirements Drafter round can turn the chosen one into confirmed
requirement text:

1. **Custom field workaround:** add a maintainer-created custom Text field
   (e.g. named "PR") to the Project, and have the sync (at `--stage open`/
   `--stage merge`) write the PR's URL into it via the existing
   `item-edit --text` mechanism (this already works for genuine custom
   fields — unlike "Created"/"Closed"/"Linked pull requests", which don't).
   Low effort, keeps today's draft-item architecture unchanged, but does not
   use GitHub's actual "Linked pull requests" UI/field — it's a
   look-alike, not the real thing.
2. **Real Issue/PR items:** stop creating title-only "draft issues" via
   `gh project item-create`, and instead add the actual PR as the Project
   item via `gh project item-add --url <PR-url>` once a PR exists. This
   gets genuine, GitHub-maintained "Linked pull requests"/"Created"/"Closed"
   values for free, but changes the sync's item-creation model
   fundamentally (draft-stage sync currently runs before any PR exists;
   existing draft-items already on real boards, including ones created
   during TASK-062/063/064's own testing, would need a migration decision:
   replace-and-delete vs. leave as legacy items).

Investigate feasibility of both (including whether `gh project item-add`
can be pointed at a PR that doesn't exist yet at draft-stage, and how a
migration of already-existing draft items would work in practice — try it
live against this repo's own Project #2 the same way the field-editability
finding above was confirmed), then present the recommendation, its
tradeoffs, and a proposed requirement-text draft to the user for
confirmation.

**Implementation location (for whichever follow-up is confirmed, not this
task):** `src/butler_core/projects.py` (`_create_item`, `sync_on_pr_merge`
or a new sync stage), `REQUIREMENTS_TASK_WORKFLOW.md` (new requirement,
pending Requirements Drafter + user confirmation).

## Branch
**Branch name:** `task/064-investigate-pr-traceability-from-projects-board`
**Switch/create:** `git checkout -b task/064-investigate-pr-traceability-from-projects-board`
**Make target:** `make branch-task f=TASK-064`

## Acceptance criteria (Gherkin)

- [x] Scenario: Both approaches are investigated against a real Project, not just reasoned about
      Given the two candidate approaches (custom text field vs. real Issue/PR items) described above
      When this task is worked
      Then both are tried live against this repo's own configured GitHub Project (`.butler-project`) — a custom Text field write via `item-edit --text`, and an `item-add --url` call against a real PR — with the actual `gh` output/errors recorded, not assumed

- [x] Scenario: A migration path for already-existing draft items is assessed
      Given draft-issue items already exist on the board (e.g. from TASK-060 through TASK-064's own testing)
      When approach 2 (real Issue/PR items) is evaluated
      Then the investigation records whether/how those existing draft items could be replaced with real PR-backed items without losing board history, or explicitly recommends leaving them as legacy items

- [x] Scenario: A recommendation is presented for user confirmation before any requirement text is written
      Given both approaches have been investigated
      When the findings are ready
      Then the user is presented with a clear recommendation and tradeoffs, and asked to confirm before a Requirements Drafter round drafts any new/changed requirement text (per CLAUDE.md's spec-driven development rule — this task does not draft requirement text itself)

- [x] Scenario: TASK-062's silent date-write failure is documented as a follow-up, not fixed here
      Given `_backfill_dates()` in `src/butler_core/projects.py` does not check `_item_edit_date()`'s return code
      When this investigation concludes
      Then a note is added to this task's Completion summary confirming a separate bug task must be filed for it once the chosen approach is confirmed (do not fix it as part of this task)

## Out of scope
- Actually implementing either approach — this task produces a
  recommendation and, if the user confirms, hands off to a Requirements
  Drafter round and a normal implementation task.
- Fixing `_backfill_dates()`'s silent failure to check `_item_edit_date()`'s
  return code — tracked as a follow-up bug task once the approach here is
  confirmed, not fixed here.
- Migrating any already-existing draft items on the real board as part of
  this task (only assessing whether/how it could be done).

## Blockers
None

## Completion
**Date:** 2026-07-31
**Summary:** Both candidate approaches were tried live against this repo's
own Project #2. Approach 1 (custom Text field): a "PR Test" field was
created via `gh project field-create` and written via
`gh project item-edit --text`, which succeeded (exit 0) and the value
round-tripped correctly through `item-list`. Approach 2 (real PR items):
`gh project item-add --url <merged-PR>` succeeded and created a genuine
`PullRequest`-typed item whose derived `createdAt`/`closedAt` (queried via
GraphQL) exactly matched the real PR's timestamps — confirming "Linked pull
requests"/"Created"/"Closed" are populated for free once an item is
PR-backed. A new constraint not previously documented was found:
`item-add --url` requires the target PR to already exist (a URL to a
not-yet-created PR returns "resource not found"), so approach 2 cannot
place an item on the board before a PR is opened — directly conflicting
with `--stage start` (TASK-065)'s early, pre-PR board visibility. All 8
existing board items are `DraftIssue`; migrating them to real PR-backed
items is mechanically simple (item-add the merged PR, item-delete the old
draft item) but loses board position/history, and since all 8 are already
"Done" with low historical value, the recommendation is to leave them as
legacy items rather than migrate. Test artifacts (the "PR Test" field and
the test PR item) were removed from the live board after the investigation.
**Recommendation presented and confirmed by user:** Approach 1 (custom
Text field) — it preserves `--stage start`'s early board visibility and
needs no migration, at the cost of not using GitHub's native
"Linked pull requests" field. A Requirements Drafter round is the next
step to turn this into confirmed requirement text; this task does not
draft that text itself, per CLAUDE.md's spec-driven development rule.
**Follow-up filed as a separate concern (not fixed here):** `_backfill_dates()`
in `src/butler_core/projects.py` (TASK-062) does not check
`_item_edit_date()`'s return code, so a silent field-write failure against
"Created"/"Closed" system fields is reported as success. A bug task for
this must be filed once the Approach 1 requirement text above is
implemented, since it will change which fields `_backfill_dates()` (or its
Approach-1 replacement) actually writes to.
**Files changed:** `docs/tasks/TASK-064-investigate-pr-traceability-from-projects-board.md`
**Branch:** `git checkout task/064-investigate-pr-traceability-from-projects-board`
**Stage:** `git add docs/tasks/TASK-064-investigate-pr-traceability-from-projects-board.md`
**Commit:** `git commit -m "Investigate PR traceability options from the GitHub Projects board"`
