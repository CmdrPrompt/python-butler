Feature: Mark butler sync deprecated
  As a maintainer
  I want users to see a clear deprecation notice when they run `butler sync --help`
  or read the function docstrings
  So that they know the command applies only to `git subtree`-based projects
  and will be removed, and they can migrate to the submodule-based
  distribution model (`REQUIREMENTS_SUBMODULE.md`) instead

  Scenario: butler sync --help displays deprecation notice
    Given a user runs `butler sync --help`
    When the command completes
    Then the output includes a deprecation notice stating the command applies only to git-subtree-based consumer projects and will be removed in a future release
    And the output references REQUIREMENTS_SUBMODULE.md as the current distribution mechanism

  Scenario: sync_makefile docstring mentions deprecation
    Given a developer reads the `sync_makefile()` function in src/butler_core/sync.py
    When they view the function's docstring
    Then the docstring states the command is deprecated, applies only to git-subtree consumer projects, and will be removed in a future release
    And the docstring references REQUIREMENTS_SUBMODULE.md as the current mechanism

  Scenario: check_sync docstring mentions deprecation
    Given a developer reads the `check_sync()` function in src/butler_core/sync.py
    When they view the function's docstring
    Then the docstring states the command is deprecated, applies only to git-subtree consumer projects, and will be removed in a future release
    And the docstring references REQUIREMENTS_SUBMODULE.md as the current mechanism

  Scenario: Existing sync behavior continues unchanged
    Given the deprecation notices have been added to CLI help and docstrings
    When `butler sync --dry-run` is run with a local .butler/Makefile
    Then the command behaves exactly as before (comparing content hash/diff, reporting whether a change is needed, etc.)
    And the `--force` flag continues to override the working tree cleanliness check
    And the dry-run output format is unchanged

  Scenario: All existing sync tests pass
    Given the deprecation notices have been added
    When `make test` is run
    Then all tests related to `butler sync` (in src/butler_core/tests/ or similar) continue to pass unchanged
    And no new test failures are introduced by the documentation changes
