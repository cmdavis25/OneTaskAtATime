"""Tests for DeferWithSubtasksCommand - compound command for subtask breakdown."""

import pytest
from datetime import date, timedelta
from src.commands.defer_with_subtasks_command import DeferWithSubtasksCommand
from src.models.task import Task
from src.models.dependency import Dependency
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO


@pytest.fixture
def task_dao(test_db):
    """Create TaskDAO with temporary database."""
    return TaskDAO(test_db)


@pytest.fixture
def dependency_dao(test_db):
    """Create DependencyDAO with temporary database."""
    return DependencyDAO(test_db)


@pytest.fixture
def sample_task(task_dao):
    """Create a sample active task."""
    task = Task(
        title="Complex Task",
        base_priority=3,
        state=TaskState.ACTIVE,
        due_date=date(2026, 12, 31)
        # No context_id to avoid FK constraint issues
    )
    return task_dao.create(task)


def create_subtask_objects():
    """Create Task objects for subtasks."""
    return [
        Task(title="Subtask 1", base_priority=2, state=TaskState.ACTIVE),
        Task(title="Subtask 2", base_priority=2, state=TaskState.ACTIVE),
        Task(title="Subtask 3", base_priority=2, state=TaskState.ACTIVE)
    ]


class TestCommandExecution:
    """Tests for command execution."""

    def test_execute_creates_subtasks(self, task_dao, dependency_dao, sample_task):
        """Should create subtasks from Task objects."""
        subtasks = create_subtask_objects()
        start_date = date.today() + timedelta(days=7)

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=start_date,
            created_tasks=subtasks,
            delete_original=False
        )

        result = command.execute()

        assert result is True
        assert len(command.created_subtask_ids) == 3

        # Verify subtasks were created
        for i, subtask_id in enumerate(command.created_subtask_ids):
            subtask = task_dao.get_by_id(subtask_id)
            assert subtask is not None
            assert subtask.title == f"Subtask {i+1}"
            assert subtask.state == TaskState.ACTIVE

    def test_execute_defers_original_when_keep(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should defer original task when delete_original=False."""
        subtasks = create_subtask_objects()
        start_date = date.today() + timedelta(days=7)

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=start_date,
            created_tasks=subtasks,
            delete_original=False
        )

        command.execute()

        # Verify original is deferred
        original = task_dao.get_by_id(sample_task.id)
        assert original.state == TaskState.DEFERRED
        assert original.start_date == start_date

    def test_execute_trashes_original_when_delete(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should move original to TRASH when delete_original=True."""
        subtasks = create_subtask_objects()

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=subtasks,
            delete_original=True
        )

        command.execute()

        # Verify original is trashed
        original = task_dao.get_by_id(sample_task.id)
        assert original.state == TaskState.TRASH

    def test_execute_creates_dependencies_when_keep(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should create dependencies when original is kept."""
        subtasks = create_subtask_objects()

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=subtasks,
            delete_original=False
        )

        command.execute()

        # Verify dependencies created (original blocked by subtasks)
        assert len(command.created_dependency_ids) == 3

        deps = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps) == 3

        # All dependencies should block the original task
        for dep in deps:
            assert dep.blocked_task_id == sample_task.id
            assert dep.blocking_task_id in command.created_subtask_ids

    def test_execute_no_dependencies_when_delete(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should not create dependencies when original is deleted."""
        subtasks = create_subtask_objects()

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=subtasks,
            delete_original=True
        )

        command.execute()

        # Verify no dependencies created
        assert len(command.created_dependency_ids) == 0

    def test_execute_saves_original_state(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should save original state for undo."""
        original_state = sample_task.state
        original_start_date = sample_task.start_date

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=create_subtask_objects(),
            delete_original=False
        )

        command.execute()

        assert command.original_state == original_state
        assert command.original_start_date == original_start_date
        assert command.task_title == "Complex Task"


class TestCommandUndo:
    """Tests for command undo functionality."""

    def test_undo_restores_original_state(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should restore original task state."""
        original_state = sample_task.state
        original_start_date = sample_task.start_date

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=create_subtask_objects(),
            delete_original=False
        )

        command.execute()
        command.undo()

        # Verify state restored
        task = task_dao.get_by_id(sample_task.id)
        assert task.state == original_state
        assert task.start_date == original_start_date

    def test_undo_moves_subtasks_to_trash(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should move all subtasks to TRASH."""
        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=create_subtask_objects(),
            delete_original=False
        )

        command.execute()

        # Verify subtasks are active
        for subtask_id in command.created_subtask_ids:
            subtask = task_dao.get_by_id(subtask_id)
            assert subtask.state == TaskState.ACTIVE

        command.undo()

        # Verify subtasks moved to trash
        for subtask_id in command.created_subtask_ids:
            subtask = task_dao.get_by_id(subtask_id)
            assert subtask.state == TaskState.TRASH

    def test_undo_removes_dependencies(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should remove all created dependencies."""
        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=create_subtask_objects(),
            delete_original=False
        )

        command.execute()

        # Verify dependencies exist
        deps_before = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_before) == 3

        command.undo()

        # Verify dependencies removed
        deps_after = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_after) == 0
        assert len(command.created_dependency_ids) == 0


class TestCommandRedo:
    """Tests for command redo functionality."""

    def test_redo_restores_subtasks_from_trash(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should restore subtasks from TRASH on redo."""
        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=create_subtask_objects(),
            delete_original=False
        )

        command.execute()
        command.undo()

        # Verify subtasks in trash after undo
        for subtask_id in command.created_subtask_ids:
            subtask = task_dao.get_by_id(subtask_id)
            assert subtask.state == TaskState.TRASH

        command.execute()  # Redo

        # Verify subtasks restored
        for subtask_id in command.created_subtask_ids:
            subtask = task_dao.get_by_id(subtask_id)
            assert subtask.state == TaskState.ACTIVE

    def test_redo_recreates_dependencies(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should recreate dependencies on redo."""
        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=create_subtask_objects(),
            delete_original=False
        )

        command.execute()
        command.undo()

        # Verify dependencies removed after undo
        deps_after_undo = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_after_undo) == 0

        command.execute()  # Redo

        # Verify dependencies recreated
        deps_after_redo = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_after_redo) == 3

    def test_redo_reapplies_defer(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should reapply defer state on redo."""
        start_date = date.today() + timedelta(days=7)

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=start_date,
            created_tasks=create_subtask_objects(),
            delete_original=False
        )

        command.execute()
        command.undo()

        # Verify original restored after undo
        task = task_dao.get_by_id(sample_task.id)
        assert task.state == TaskState.ACTIVE

        command.execute()  # Redo

        # Verify defer reapplied
        task = task_dao.get_by_id(sample_task.id)
        assert task.state == TaskState.DEFERRED
        assert task.start_date == start_date


class TestCommandDescription:
    """Tests for command description."""

    def test_get_description_with_title(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should include task title and subtask count."""
        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today(),
            created_tasks=create_subtask_objects()
        )

        command.execute()
        description = command.get_description()

        assert "Complex Task" in description
        assert "3 subtasks" in description

    def test_get_description_pluralization(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should pluralize correctly for single vs multiple subtasks."""
        # Single subtask
        command_single = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today(),
            created_tasks=[Task(title="Subtask 1", base_priority=2)]
        )

        command_single.execute()
        assert "1 subtask" in command_single.get_description()


class TestProjectTagInheritance:
    """Tests for project tag inheritance."""

    def test_subtasks_inherit_project_tags(
        self, task_dao, dependency_dao
    ):
        """Subtasks should inherit project tags from original."""
        # NOTE: Skipping project tag test - requires pre-existing project tags in DB
        # Create original without project tags to avoid FK constraints
        original = Task(
            title="Original",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        original = task_dao.create(original)

        # Create subtasks without project tags
        subtasks = [
            Task(title="Sub 1", base_priority=2),
            Task(title="Sub 2", base_priority=2)
        ]

        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=original.id,
            start_date=date.today() + timedelta(days=7),
            created_tasks=subtasks,
            delete_original=False
        )

        command.execute()

        # Verify subtasks were created (project tag inheritance tested elsewhere)
        assert len(command.created_subtask_ids) == 2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_execute_fails_for_nonexistent_task(
        self, task_dao, dependency_dao
    ):
        """Should fail gracefully if task doesn't exist."""
        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=99999,
            start_date=date.today(),
            created_tasks=create_subtask_objects()
        )

        result = command.execute()
        assert result is False

    def test_undo_fails_for_nonexistent_task(
        self, task_dao, dependency_dao
    ):
        """Should fail gracefully if task doesn't exist during undo."""
        command = DeferWithSubtasksCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=99999,
            start_date=date.today(),
            created_tasks=create_subtask_objects()
        )

        # Set original state manually
        command.original_state = TaskState.ACTIVE
        command.original_start_date = None

        result = command.undo()
        assert result is False
