"""Tests for butler_core.tasks."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from butler_core.tasks import (
    AcceptanceCriterion,
    Completion,
    Task,
    check_criterion,
    create_task,
    list_tasks,
    parse_task,
    read_task,
    render_task,
    set_status,
)

REAL_TASKS_DIR = "docs/tasks"


def test_read_task_returns_structured_data_for_existing_file() -> None:
    task = read_task("TASK-015", tasks_dir=REAL_TASKS_DIR)

    assert task.id == "TASK-015"
    assert task.title == "Add butler-trim, butler-fetch, and butler-pull targets"
    assert task.status == "done"
    assert task.branch_name == "task/015-butler-trim-target"
    assert task.switch_create_cmd == "git checkout -b task/015-butler-trim-target"
    # TASK-015's Stage field predates TASK-086 and still has "git add" in the
    # backticks; that's parsed as literal path tokens now, unmigrated.
    assert task.stage_paths[:2] == ["git", "add"]
    assert "Makefile" in task.stage_paths
    assert "butler-trim, butler-fetch, butler-pull" in task.commit_message
    assert len(task.acceptance_criteria) == 8
    assert all(criterion.checked for criterion in task.acceptance_criteria)
    assert task.completion is not None
    assert task.completion.date == "2026-04-30"
    assert "Makefile" in task.completion.files_changed


def test_list_tasks_filters_by_status(tmp_path: Path) -> None:
    create_task("First todo task", "desc one", tasks_dir=str(tmp_path))
    second = create_task("Second todo task", "desc two", tasks_dir=str(tmp_path))
    set_status(second.id, "done", tasks_dir=str(tmp_path))

    todo_tasks = list_tasks(tasks_dir=str(tmp_path), status="todo")
    done_tasks = list_tasks(tasks_dir=str(tmp_path), status="done")

    assert [t.title for t in todo_tasks] == ["First todo task"]
    assert [t.title for t in done_tasks] == ["Second todo task"]
    assert len(list_tasks(tasks_dir=str(tmp_path))) == 2


def test_create_task_allocates_next_number_and_writes_parseable_file(tmp_path: Path) -> None:
    (tmp_path / "TASK-005-existing.md").write_text(
        render_task(
            Task(
                id="TASK-005",
                title="Existing",
                status="done",
                description="desc",
                branch_name="task/005-existing",
                switch_create_cmd="git checkout -b task/005-existing",
                stage_paths=["foo.py", "CHANGELOG.md"],
                commit_message="Do the thing",
                acceptance_criteria=[],
                completion=None,
            )
        )
    )

    task = create_task("New feature", "Implement the new feature.", tasks_dir=str(tmp_path))

    assert task.id == "TASK-006"
    written = (tmp_path / "TASK-006-new-feature.md").read_text()
    reparsed = parse_task(written)
    assert reparsed.id == "TASK-006"
    assert reparsed.status == "todo"
    assert reparsed.branch_name == "task/006-new-feature"


def test_stage_field_parses_as_a_whitespace_separated_path_list(tmp_path: Path) -> None:
    """TASK-086: the Completion `**Stage:**` field is data (file paths), never
    an executable command line — see REQUIREMENTS_TASK_WORKFLOW.md Requirement 15."""
    (tmp_path / "TASK-001-sample.md").write_text(
        render_task(
            Task(
                id="TASK-001",
                title="Sample",
                status="todo",
                description="desc",
                branch_name="task/001-sample",
                switch_create_cmd="git checkout -b task/001-sample",
                stage_paths=["src/foo.py", "tests/test_foo.py", "CHANGELOG.md"],
                commit_message="Add foo",
                acceptance_criteria=[],
                completion=None,
            )
        )
    )

    task = read_task("TASK-001", tasks_dir=str(tmp_path))

    assert task.stage_paths == ["src/foo.py", "tests/test_foo.py", "CHANGELOG.md"]


def test_created_task_files_stage_field_has_no_leading_git_add(tmp_path: Path) -> None:
    task = create_task("New feature", "desc", tasks_dir=str(tmp_path))
    text = (tmp_path / f"{task.id}-new-feature.md").read_text()

    stage_line = next(line for line in text.splitlines() if line.startswith("**Stage:**"))

    assert "git add" not in stage_line
    assert "CHANGELOG.md" in task.stage_paths


def test_created_task_file_is_makefile_grep_compatible(tmp_path: Path) -> None:
    task = create_task("Grep compatible task", "desc", tasks_dir=str(tmp_path))
    text = (tmp_path / f"{task.id}-grep-compatible-task.md").read_text()

    switch_match = re.search(r"\*\*Switch/create:\*\*.*`(git checkout[^`]*)`", text)
    stage_match = re.search(r"\*\*Stage:\*\*.*`([^`]*CHANGELOG\.md[^`]*)`", text)
    commit_match = re.search(r'\*\*Commit:\*\*.*`git commit -m "(.*)"`', text)

    assert switch_match is not None
    assert stage_match is not None
    assert commit_match is not None


def test_check_criterion_toggles_only_target_checkbox(tmp_path: Path) -> None:
    task = create_task("Checkbox task", "desc", tasks_dir=str(tmp_path))
    path = tmp_path / f"{task.id}-checkbox-task.md"
    text = path.read_text().replace(
        "## Acceptance criteria\n",
        "## Acceptance criteria\n\n- [ ] first\n- [ ] second\n- [ ] third\n",
    )
    path.write_text(text)

    check_criterion(task.id, index=1, tasks_dir=str(tmp_path))

    updated = read_task(task.id, tasks_dir=str(tmp_path))
    assert [criterion.checked for criterion in updated.acceptance_criteria] == [
        False,
        True,
        False,
    ]
    assert [criterion.text for criterion in updated.acceptance_criteria] == [
        "first",
        "second",
        "third",
    ]


def test_set_status_updates_status_line_without_touching_description(tmp_path: Path) -> None:
    task = create_task("Status task", "desc", tasks_dir=str(tmp_path))
    original_description = read_task(task.id, tasks_dir=str(tmp_path)).description

    set_status(task.id, "in-progress", tasks_dir=str(tmp_path))

    updated = read_task(task.id, tasks_dir=str(tmp_path))
    assert updated.status == "in-progress"
    assert updated.description == original_description


def test_read_task_raises_for_unknown_task_id(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_task("TASK-999", tasks_dir=str(tmp_path))


def test_read_task_finds_criteria_under_gherkin_suffixed_heading(tmp_path: Path) -> None:
    task = create_task("Gherkin heading task", "desc", tasks_dir=str(tmp_path))
    path = tmp_path / f"{task.id}-gherkin-heading-task.md"
    text = path.read_text().replace(
        "## Acceptance criteria\n",
        "## Acceptance criteria (Gherkin)\n\n- [ ] first\n- [x] second\n",
    )
    path.write_text(text)

    updated = read_task(task.id, tasks_dir=str(tmp_path))

    assert [criterion.text for criterion in updated.acceptance_criteria] == [
        "first",
        "second",
    ]
    assert [criterion.checked for criterion in updated.acceptance_criteria] == [
        False,
        True,
    ]


_safe_field = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters='`#\n"',
        max_codepoint=0x2FFF,
    ),
    min_size=1,
    max_size=25,
).filter(lambda s: s == s.strip())

_path_token = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters='`#\n"',
        max_codepoint=0x2FFF,
    ),
    min_size=1,
    max_size=25,
).filter(lambda s: s == s.strip() and not any(c.isspace() for c in s))
_stage_paths = st.lists(_path_token, max_size=5)

_task_ids = st.integers(min_value=1, max_value=999).map(lambda n: f"TASK-{n:03d}")
_statuses = st.sampled_from(["todo", "in-progress", "done"])
_criteria = st.lists(
    st.builds(AcceptanceCriterion, text=_safe_field, checked=st.booleans()),
    max_size=5,
)
_completions = st.one_of(
    st.none(),
    st.builds(
        Completion,
        date=_safe_field,
        summary=_safe_field,
        files_changed=st.lists(_safe_field, max_size=5),
    ),
)


@given(
    task_id=_task_ids,
    title=_safe_field,
    status=_statuses,
    description=_safe_field,
    branch_name=_safe_field,
    switch_create_cmd=_safe_field,
    stage_paths=_stage_paths,
    commit_message=_safe_field,
    acceptance_criteria=_criteria,
    completion=_completions,
)
def test_render_and_parse_round_trip(
    task_id: str,
    title: str,
    status: str,
    description: str,
    branch_name: str,
    switch_create_cmd: str,
    stage_paths: list[str],
    commit_message: str,
    acceptance_criteria: list[AcceptanceCriterion],
    completion: Completion | None,
) -> None:
    task = Task(
        id=task_id,
        title=title,
        status=status,
        description=description,
        branch_name=branch_name,
        switch_create_cmd=switch_create_cmd,
        stage_paths=stage_paths,
        commit_message=commit_message,
        acceptance_criteria=acceptance_criteria,
        completion=completion,
    )

    reparsed = parse_task(render_task(task))

    assert reparsed == task


_heading_suffixes = st.sampled_from(["", " (Gherkin)"])


@given(acceptance_criteria=_criteria, heading_suffix=_heading_suffixes)
def test_parse_task_finds_acceptance_criteria_regardless_of_heading_suffix(
    acceptance_criteria: list[AcceptanceCriterion], heading_suffix: str
) -> None:
    task = Task(
        id="TASK-001",
        title="Sample",
        status="todo",
        description="desc",
        branch_name="task/001-sample",
        switch_create_cmd="git checkout -b task/001-sample",
        stage_paths=["foo.py", "CHANGELOG.md"],
        commit_message="Do the thing",
        acceptance_criteria=acceptance_criteria,
        completion=None,
    )
    text = render_task(task).replace(
        "## Acceptance criteria\n", f"## Acceptance criteria{heading_suffix}\n"
    )

    reparsed = parse_task(text)

    assert reparsed.acceptance_criteria == acceptance_criteria
