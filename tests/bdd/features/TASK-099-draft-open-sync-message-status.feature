Feature: Draft and open sync messages do not claim a Status they did not set
  As a maintainer watching GitHub Projects status sync
  I want the draft and open sync output to report only what the sync actually did
  So that I am not told an item is "In Progress" when the Project still shows it as "Todo"

  @AC-1
  Scenario: Draft sync of a new item does not claim a status
    Given a task with no linked Project item
    When the draft sync creates the Project item
    Then the success message names the task id and title
    And the message does not contain "status:"

  @AC-2
  Scenario: Draft sync of an already linked item does not claim a status
    Given a task whose Project item already exists
    When the draft sync links the existing item
    Then the success message does not contain "status:"

  @AC-3
  Scenario: Open sync does not claim a status
    Given a task with a linked Project item
    When the open sync runs
    Then the success message does not contain "status:"

  @AC-4
  Scenario: Start sync still reports In Progress
    Given a task with a Project item whose Status field has an "In Progress" option
    When the start sync runs
    Then the item's Status is set to "In Progress"
    And the success message contains "status: In Progress"

  @AC-5
  Scenario: Appended notes are preserved
    Given the Project number resolves via $BUTLER_GITHUB_PROJECT and duplicate items exist for the task
    When the draft sync succeeds
    Then the Requirement 17 note and the duplicate-item warning are still appended to the message
