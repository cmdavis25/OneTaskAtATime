"""Tests for DeferWithDependenciesCommand - compound command for defer workflow."""

import pytest
from datetime import date, timedelta
from src.commands.defer_with_dependencies_command import DeferWithDependenciesCommand
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
        title="Main Task",
        base_priority=2,
        state=TaskState.ACTIVE
    )
    return task_dao.create(task)


@pytest.fixture
def blocking_tasks(task_dao):
    """Create blocking tasks."""
    tasks = []
    for i in range(3):
        task = Task(
            title=f"Blocker {i+1}",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        tasks.append(task_dao.create(task))
    return tasks


class TestCommandExecution:
    """Tests for command execution."""

    def test_execute_defer_with_dependencies(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should defer task and track dependencies."""
        start_date = date.today() + timedelta(days=7)
        blocking_ids = [t.id for t in blocking_tasks[:2]]

        # Create dependencies (simulating DependencySelectionDialog)
        for blocking_id in blocking_ids:
            dep = Dependency(
                blocked_task_id=sample_task.id,
                blocking_task_id=blocking_id
            )
            dependency_dao.create(dep)

        # Create and execute command
        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=start_date,
            dependency_task_ids=blocking_ids,
            reason="Waiting for blockers"
        )

        result = command.execute()

        assert result is True

        # Verify task was deferred
        task = task_dao.get_by_id(sample_task.id)
        assert task.state == TaskState.DEFERRED
        assert task.start_date == start_date

        # Verify dependencies are tracked
        assert len(command.created_dependency_ids) == 2

    def test_execute_saves_original_state(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should save original task state for undo."""
        original_state = sample_task.state
        original_start_date = sample_task.start_date

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=[],
            created_blocking_task_ids=[]
        )

        command.execute()

        # Verify original state was saved
        assert command.original_state == original_state
        assert command.original_start_date == original_start_date
        assert command.task_title == "Main Task"

    def test_execute_with_created_blocking_tasks(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should track newly created blocking tasks."""
        created_blocker = blocking_tasks[0]

        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=created_blocker.id
        )
        dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=[created_blocker.id],
            created_blocking_task_ids=[created_blocker.id]
        )

        result = command.execute()

        assert result is True
        assert created_blocker.id in command.created_blocking_task_ids

    def test_execute_fails_for_nonexistent_task(
        self, task_dao, dependency_dao
    ):
        """Should fail gracefully if task doesn't exist."""
        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=99999,
            start_date=date.today(),
            dependency_task_ids=[]
        )

        result = command.execute()
        assert result is False


class TestCommandUndo:
    """Tests for command undo functionality."""

    def test_undo_restores_original_state(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should restore task's original state and start_date."""
        original_state = sample_task.state
        original_start_date = sample_task.start_date
        blocking_id = blocking_tasks[0].id

        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocking_id
        )
        dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=[blocking_id]
        )

        command.execute()
        command.undo()

        # Verify state restored
        task = task_dao.get_by_id(sample_task.id)
        assert task.state == original_state
        assert task.start_date == original_start_date

    def test_undo_removes_dependencies(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should remove all created dependency relationships."""
        blocking_ids = [t.id for t in blocking_tasks[:2]]

        # Create dependencies
        for blocking_id in blocking_ids:
            dep = Dependency(
                blocked_task_id=sample_task.id,
                blocking_task_id=blocking_id
            )
            dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=blocking_ids
        )

        command.execute()

        # Verify dependencies exist
        deps_before = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_before) == 2

        command.undo()

        # Verify dependencies removed
        deps_after = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_after) == 0

    def test_undo_moves_created_blockers_to_trash(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should move created blocking tasks to TRASH on undo."""
        created_blocker = blocking_tasks[0]

        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=created_blocker.id
        )
        dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=[created_blocker.id],
            created_blocking_task_ids=[created_blocker.id]
        )

        command.execute()
        command.undo()

        # Verify blocker moved to trash
        blocker = task_dao.get_by_id(created_blocker.id)
        assert blocker.state == TaskState.TRASH

    def test_undo_fails_for_nonexistent_task(
        self, task_dao, dependency_dao
    ):
        """Should fail gracefully if task doesn't exist during undo."""
        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=99999,
            start_date=date.today(),
            dependency_task_ids=[]
        )

        # Set original state manually (simulating execute was called)
        command.original_state = TaskState.ACTIVE
        command.original_start_date = None

        result = command.undo()
        assert result is False


class TestCommandRedo:
    """Tests for command redo functionality."""

    def test_redo_reapplies_defer(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should reapply defer after undo."""
        start_date = date.today() + timedelta(days=7)
        blocking_id = blocking_tasks[0].id

        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocking_id
        )
        dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=start_date,
            dependency_task_ids=[blocking_id]
        )

        # Execute, undo, execute again (redo)
        command.execute()
        command.undo()
        command.execute()

        # Verify defer was reapplied
        task = task_dao.get_by_id(sample_task.id)
        assert task.state == TaskState.DEFERRED
        assert task.start_date == start_date

    def test_redo_restores_created_blockers(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should restore created blocking tasks from TRASH on redo."""
        created_blocker = blocking_tasks[0]

        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=created_blocker.id
        )
        dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=[created_blocker.id],
            created_blocking_task_ids=[created_blocker.id]
        )

        # Execute, undo (moves to TRASH), execute again (redo - should restore)
        command.execute()
        command.undo()

        # Verify blocker is in trash after undo
        blocker = task_dao.get_by_id(created_blocker.id)
        assert blocker.state == TaskState.TRASH

        command.execute()

        # Verify blocker restored to ACTIVE
        blocker = task_dao.get_by_id(created_blocker.id)
        assert blocker.state == TaskState.ACTIVE

    def test_redo_recreates_dependencies(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should recreate dependencies on redo."""
        blocking_ids = [t.id for t in blocking_tasks[:2]]

        # Create dependencies
        for blocking_id in blocking_ids:
            dep = Dependency(
                blocked_task_id=sample_task.id,
                blocking_task_id=blocking_id
            )
            dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=blocking_ids
        )

        # Execute, undo, execute again
        command.execute()
        command.undo()

        # Verify dependencies removed after undo
        deps_after_undo = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_after_undo) == 0

        command.execute()

        # Verify dependencies recreated
        deps_after_redo = dependency_dao.get_dependencies_for_task(sample_task.id)
        assert len(deps_after_redo) == 2


class TestCommandDescription:
    """Tests for command description."""

    def test_get_description_with_title(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should include task title in description."""
        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today(),
            dependency_task_ids=[1, 2]
        )

        command.execute()
        description = command.get_description()

        assert "Main Task" in description
        assert "2 dependencies" in description

    def test_get_description_pluralization(
        self, task_dao, dependency_dao, sample_task
    ):
        """Should pluralize correctly for single vs multiple dependencies."""
        # Single dependency
        command_single = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today(),
            dependency_task_ids=[1]
        )

        command_single.execute()
        assert "1 dependency" in command_single.get_description()

        # Multiple dependencies
        command_multi = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today(),
            dependency_task_ids=[1, 2, 3]
        )

        command_multi.execute()
        assert "3 dependencies" in command_multi.get_description()

    def test_get_description_without_title(
        self, task_dao, dependency_dao
    ):
        """Should show task ID if title not available."""
        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=123,
            start_date=date.today(),
            dependency_task_ids=[1]
        )

        description = command.get_description()

        assert "ID: 123" in description


class TestCircularDependencyHandling:
    """Tests for handling circular dependency errors."""

    def test_handles_circular_dependency_during_redo(
        self, task_dao, dependency_dao, sample_task, blocking_tasks
    ):
        """Should skip circular dependencies during redo without failing."""
        blocker_id = blocking_tasks[0].id

        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocker_id
        )
        dependency_dao.create(dep)

        command = DeferWithDependenciesCommand(
            task_dao=task_dao,
            dependency_dao=dependency_dao,
            task_id=sample_task.id,
            start_date=date.today() + timedelta(days=7),
            dependency_task_ids=[blocker_id]
        )

        command.execute()
        command.undo()

        # Create a circular dependency manually
        reverse_dep = Dependency(
            blocked_task_id=blocker_id,
            blocking_task_id=sample_task.id
        )
        dependency_dao.create(reverse_dep)

        # Redo should handle this gracefully
        result = command.execute()

        # Command should still succeed overall
        assert result is True
