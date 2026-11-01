"""Tests for TASK-101 / Requirement 20: the new Project item's node ID is
read from `gh project item-create --format json`'s output, and anything
without a usable `id` yields None rather than a fallback ID."""

from __future__ import annotations

import json

from hypothesis import given
from hypothesis import strategies as st

from butler_core.projects import _created_item_id

_json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=10,
)


@given(item_id=st.text(min_size=1), extra=st.dictionaries(st.text(), _json_values))
def test_returns_the_id_field_of_the_created_item(item_id: str, extra: dict) -> None:
    payload = {**extra, "id": item_id}
    assert _created_item_id(json.dumps(payload)) == item_id


@given(payload=st.dictionaries(st.text().filter(lambda k: k != "id"), _json_values))
def test_returns_none_when_output_has_no_id(payload: dict) -> None:
    assert _created_item_id(json.dumps(payload)) is None


@given(stdout=st.text())
def test_never_raises_on_arbitrary_output(stdout: str) -> None:
    result = _created_item_id(stdout)
    assert result is None or isinstance(result, str)


def test_returns_none_for_empty_id() -> None:
    assert _created_item_id(json.dumps({"id": ""})) is None
