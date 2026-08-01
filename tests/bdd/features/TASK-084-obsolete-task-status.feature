Feature: Add an obsolete task Status for work superseded before completion
  As a Workflow Guardian reconciling task files against reality
  I want a terminal `obsolete` Status distinct from `todo`/`blocked`/`done`
  So that a task superseded by other work is never miscounted as outstanding
  or silently mismarked, in the task file or on the linked GitHub Projects item

  Scenario: obsolete is a documented, valid Status value
    Given the task-file-format skill's canonical template
    When a reader looks at the Status line
    Then it lists `todo | in-progress | blocked | done | obsolete`
    And a nearby note states only the Workflow Guardian or the user sets `obsolete`, and only when the file documents the superseding task/requirement

  Scenario: butler_core accepts obsolete as a valid Status
    Given a task file with `## Status` set to `obsolete`
    When `butler task show`/`set-status`/the Projects sync status-matching process it
    Then it is accepted identically to `todo`/`in-progress`/`blocked`/`done`, with no error

  Scenario: backfill sync sets the Project item's Status to Obsolete
    Given a task file with Status `obsolete` and a configured GitHub Project whose Status field has an "Obsolete" option
    When `butler task sync-project <ID> --stage backfill` runs
    Then the linked Project item's Status is set to "Obsolete"

  Scenario: missing Obsolete option warns instead of raising
    Given a configured GitHub Project whose Status field has no "Obsolete" option
    When `--stage backfill` runs against an `obsolete` task
    Then it produces a best-effort warning and does not raise or block
