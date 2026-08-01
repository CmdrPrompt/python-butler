"""TASK-085: binds TASK-085-mark-butler-sync-deprecated.feature so `make
bdd`/`make bdd-missing` see its scenarios as red. Step implementations are
implementation-worker's job once TASK-085 is picked up; until then the
scenarios are expected to fail (`StepDefinitionNotFoundError`), so they are
marked `xfail` to keep `make test`/CI green.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.xfail(reason="TASK-085 not yet implemented", strict=False)

scenarios("../features/TASK-085-mark-butler-sync-deprecated.feature")
