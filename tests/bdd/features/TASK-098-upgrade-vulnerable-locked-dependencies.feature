Feature: Upgrade locked dependencies so the CI security audit passes
  As a maintainer of python-butler and its consumer projects
  I want every locked dependency to pass the CI security audit
  So that unrelated pull requests are no longer blocked by advisories against versions already in the lockfile

  @AC-1
  Scenario: Locked dependencies report no known vulnerabilities
    Given the packages pinned in `uv.lock`
    When the dependency audit `uv run pip-audit --progress-spinner=off` runs
    Then no known vulnerabilities are reported
    And the audit exits 0

  @AC-2
  Scenario: Only the local package is skipped
    Given the packages pinned in `uv.lock`, including the local package `butler-core`
    When the dependency audit runs
    Then `butler-core` is listed under "Skip" as not found on PyPI
    And no other package is listed under "Skip"

  @AC-3
  Scenario: Quality gates still pass after the upgrade
    Given the upgraded `uv.lock`
    When `make lint`, `make test`, `make bdd` and the pre-commit hooks run
    Then each of them passes

  @AC-4
  Scenario: Affected packages stay at or above their fixed versions
    Given the packages pinned in `uv.lock`
    When the locked versions of the affected packages are read
    Then each affected package is locked at or above its first fixed version
      | package    | fixed version |
      | virtualenv | 21.7.13       |
      | filelock   | 4.2.1         |
      | urllib3    | 2.8.0         |
      | certifi    | 2026.10.18    |
      | msgpack    | 1.2.3         |
