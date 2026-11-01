"""TASK-101: binds TASK-101-status-sync-resolved-item-id.feature so `make bdd`/
`make bdd-missing` see its scenarios as red. Step implementations are
implementation-worker's job once TASK-101 is picked up; until then the
scenarios are expected to fail (`StepDefinitionNotFoundError`), so they are
marked `xfail` to keep `make test`/CI green.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.xfail(reason="TASK-101 not yet implemented", strict=False)

scenarios("../features/TASK-101-status-sync-resolved-item-id.feature")
