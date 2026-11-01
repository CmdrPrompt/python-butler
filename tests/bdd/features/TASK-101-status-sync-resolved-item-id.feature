Feature: Status sync acts only on a resolved Project item ID, never on the task ID
  As a maintainer watching GitHub Projects status sync
  I want every status-setting sync stage to act on the Project item it resolved
  So that a newly created item shows the status the stage set, and a missing item is reported as a warning instead of failing with a GraphQL error

  @AC-1
  Scenario: Start sync on a new item sets its status in one run
    Given a task with no linked Project item
    And the Project's Status field has an "In Progress" option
    When the start sync runs
    Then the Project item created for the task has Status "In Progress"
    And the created item is not looked up a second time

  @AC-2
  Scenario: Sync of a task with an existing item updates the item found by lookup
    Given a task with a linked Project item
    And the Project's Status field has an "In Progress" option
    When the start sync runs
    Then the linked Project item has Status "In Progress"
    And the status update targets the item found by lookup, not the task ID

  @AC-3
  Scenario: No Project item can be resolved when the lookup finds nothing and creation fails
    Given a task with no linked Project item
    And creating the Project item fails
    When the start sync runs
    Then a best-effort warning names the task
    And the warning states that no Project item was found for the task
    And no Project item status is changed
    And the task ID is never used as a Project item ID
    And the sync does not raise an error

  @AC-4
  Scenario: No Project item can be resolved when the created item has no ID
    Given a task with no linked Project item
    And creating the Project item returns no item ID
    When the start sync runs
    Then a best-effort warning names the task
    And the warning states that no Project item was found for the task
    And no Project item status is changed
    And the task ID is never used as a Project item ID
    And the sync does not raise an error

  @AC-5
  Scenario: Merge sync of an existing item updates the item found by lookup
    Given a task with a linked Project item
    And the Project's Status field has a "Done" option
    When the merge sync runs
    Then the linked Project item has Status "Done"
    And the status update targets the item found by lookup, not the task ID
