Feature: Merging a task PR keeps local main consistent with origin/main
  As a maintainer who commits a new task file and requirement on local main before branching
  I want make merge-current-task to finish cleanly after the squash merge
  So that I never land in a diverged main, a merge conflict or a Python traceback, and the merge-stage Projects sync still runs

  Background:
    Given a repository with a bare origin and a task branch with an open mergeable PR

  @AC-1
  Scenario: Merge succeeds when local main commits are already in the squashed PR
    Given local main has 2 unpushed commits that are also part of the task branch
    When the task PR is squash-merged with merge_pr_for
    Then merge_pr_for completes without raising
    And local main points at origin/main
    And the working tree has no merge conflicts and no merge in progress

  @AC-2
  Scenario: Local main is fast-forwarded when it has no unpushed commits
    Given local main has no commits that are missing from origin/main
    When the task PR is squash-merged with merge_pr_for
    Then local main is fast-forwarded to origin/main
    And merge_pr_for completes without raising

  @AC-3
  Scenario: Unpushed local main commits that are not in the PR are preserved and reported
    Given local main has an unpushed commit that is not part of the task branch
    When the task PR is squash-merged with merge_pr_for
    Then local main still contains that unpushed commit
    And merge_pr_for raises a GitOpsError stating that the PR was merged and that local main has unpushed commits not in the PR
    And the error message names the command needed to resolve it
    And no merge is left in progress

  @AC-4
  Scenario: A failed local update after the merge is a clean error, not a traceback
    Given the squash merge succeeds but updating local main fails
    When the butler task merge command runs
    Then it exits non-zero with a one-line error message
    And the output contains no Python traceback

  @AC-5
  Scenario: The merge-stage Projects sync runs after a merge with local-only main commits
    Given local main has 2 unpushed commits that are also part of the task branch
    And the task has a linked Project item with Status "In Progress"
    When make merge-pr is run for the task
    Then the butler task merge step exits 0
    And the merge-stage Projects sync runs
    And the Project item Status is set to "Done"
