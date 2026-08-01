"""TASK-084: binds TASK-084-obsolete-task-status.feature so `make bdd`/
`make bdd-missing` see its scenarios as red. Step implementations are
implementation-worker's job once TASK-084 is picked up; until then the
scenarios are expected to fail (`StepDefinitionNotFoundError`), so they are
marked `xfail` to keep `make test`/CI green.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.xfail(reason="TASK-084 not yet implemented", strict=False)

scenarios("../features/TASK-084-obsolete-task-status.feature")
