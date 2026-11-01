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
  Scenario: Only affected packages change in the lockfile
    Given the `uv.lock` committed on `main`
    When the lockfile is upgraded for `virtualenv`, `filelock`, `urllib3`, `certifi` and `msgpack` only
    Then those five packages change to a version with no known vulnerabilities
    And only their required transitive dependencies change version
    And no other pinned package changes version
    And `pyproject.toml` is unchanged
