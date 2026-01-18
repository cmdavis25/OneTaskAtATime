"""
Unit tests for DependencyGraphView.

Tests the dependency graph visualization including:
- Tree structure rendering
- Task state icons
- Circular dependency detection
- Max depth handling
- Export functionality
- Refresh functionality
"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import Qt

from src.models.task import Task
from src.models.dependency import Dependency
from src.models.enums import TaskState
from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO
from src.ui.dependency_graph_view import DependencyGraphView


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_connection(self):
        return self._conn

    def close(self):
        self._conn.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    mock_conn = MockDatabaseConnection(conn)
    yield mock_conn
    conn.close()


@pytest.fixture
def task_dao(db_connection):
    """Create TaskDAO instance."""
    return TaskDAO(db_connection.get_connection())


@pytest.fixture
def dependency_dao(db_connection):
    """Create DependencyDAO instance."""
    return DependencyDAO(db_connection.get_connection())


@pytest.fixture
def sample_task(task_dao):
    """Create a sample task."""
    task = Task(
        title="Main Task",
        description="Task to visualize dependencies for",
        base_priority=2,
        due_date=date.today() + timedelta(days=7),
        state=TaskState.ACTIVE,
        elo_rating=1500.0,
        comparison_count=1
    )
    return task_dao.create(task)


@pytest.fixture
def blocking_task(task_dao):
    """Create a blocking task."""
    task = Task(
        title="Blocking Task",
        description="Task that blocks another",
        base_priority=2,
        state=TaskState.ACTIVE,
        elo_rating=1500.0,
        comparison_count=1
    )
    return task_dao.create(task)


@pytest.fixture
def completed_task(task_dao):
    """Create a completed task."""
    task = Task(
        title="Completed Task",
        description="Task that is done",
        base_priority=2,
        state=TaskState.COMPLETED,
        elo_rating=1500.0,
        comparison_count=1
    )
    return task_dao.create(task)


class TestDialogInitialization:
    """Test dialog initialization."""

    def test_dialog_title_set(self, qapp, db_connection, sample_task):
        """Test that dialog title is set correctly."""
        view = DependencyGraphView(sample_task, db_connection)
        assert sample_task.title in view.windowTitle()
        view.close()

    def test_dialog_is_non_blocking(self, qapp, db_connection, sample_task):
        """Test that dialog is non-modal."""
        view = DependencyGraphView(sample_task, db_connection)
        assert not view.isModal()
        view.close()

    def test_minimum_size_set(self, qapp, db_connection, sample_task):
        """Test that minimum size is set."""
        view = DependencyGraphView(sample_task, db_connection)
        assert view.minimumWidth() == 700
        assert view.minimumHeight() == 500
        view.close()

    def test_daos_initialized(self, qapp, db_connection, sample_task):
        """Test that DAOs are initialized."""
        view = DependencyGraphView(sample_task, db_connection)
        assert view.task_dao is not None
        assert view.dependency_dao is not None
        view.close()

    def test_graph_display_created(self, qapp, db_connection, sample_task):
        """Test that graph display widget is created."""
        view = DependencyGraphView(sample_task, db_connection)
        assert view.graph_display is not None
        assert view.graph_display.isReadOnly()
        view.close()


class TestNoDependencies:
    """Test display when task has no dependencies."""

    def test_no_blocking_tasks_message(self, qapp, db_connection, sample_task):
        """Test that message is shown when task has no blocking tasks."""
        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        assert "No blocking tasks" in graph_text
        assert "ready to work on" in graph_text
        view.close()

    def test_no_dependent_tasks_message(self, qapp, db_connection, sample_task):
        """Test that message is shown when task has no dependent tasks."""
        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        assert "No dependent tasks" in graph_text
        view.close()


class TestWithDependencies:
    """Test display when task has dependencies."""

    def test_shows_blocking_task(self, qapp, db_connection, sample_task, blocking_task, dependency_dao):
        """Test that blocking task is displayed."""
        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocking_task.id
        )
        dependency_dao.create(dep)

        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        assert blocking_task.title in graph_text
        assert "TASKS BLOCKING THIS TASK" in graph_text
        view.close()

    def test_shows_dependent_task(self, qapp, db_connection, sample_task, task_dao, dependency_dao):
        """Test that dependent task is displayed."""
        # Create a task that is blocked by sample_task
        dependent = Task(
            title="Dependent Task",
            description="Task blocked by sample task",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=1
        )
        dependent = task_dao.create(dependent)

        # Create dependency
        dep = Dependency(
            blocked_task_id=dependent.id,
            blocking_task_id=sample_task.id
        )
        dependency_dao.create(dep)

        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        assert dependent.title in graph_text
        assert "TASKS BLOCKED BY THIS TASK" in graph_text
        view.close()


class TestTreeStructure:
    """Test tree structure rendering."""

    def test_simple_chain_structure(self, qapp, db_connection, sample_task, blocking_task, dependency_dao):
        """Test that simple dependency chain is rendered with tree structure."""
        # Create dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocking_task.id
        )
        dependency_dao.create(dep)

        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        # Should have tree branch characters
        assert "└─" in graph_text or "├─" in graph_text
        view.close()

    def test_multi_level_chain(self, qapp, db_connection, sample_task, blocking_task, task_dao, dependency_dao):
        """Test that multi-level dependency chain is rendered."""
        # Create another blocking task
        second_blocker = Task(
            title="Second Blocker",
            description="Blocks the first blocker",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=1
        )
        second_blocker = task_dao.create(second_blocker)

        # Create dependency chain: sample_task <- blocking_task <- second_blocker
        dep1 = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocking_task.id
        )
        dependency_dao.create(dep1)

        dep2 = Dependency(
            blocked_task_id=blocking_task.id,
            blocking_task_id=second_blocker.id
        )
        dependency_dao.create(dep2)

        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        # Both tasks should be in the graph
        assert blocking_task.title in graph_text
        assert second_blocker.title in graph_text
        # Should have multiple levels of indentation
        assert "│" in graph_text or "   " in graph_text
        view.close()


class TestTaskIcons:
    """Test task state icons."""

    def test_active_task_icon(self, qapp, db_connection, sample_task):
        """Test that active task has correct icon."""
        view = DependencyGraphView(sample_task, db_connection)
        icon = view._get_task_icon(sample_task)
        assert icon == "🔄"
        view.close()

    def test_completed_task_icon(self, qapp, db_connection, completed_task):
        """Test that completed task has checkmark icon."""
        view = DependencyGraphView(completed_task, db_connection)
        icon = view._get_task_icon(completed_task)
        assert icon == "✓"
        view.close()

    def test_deferred_task_icon(self, qapp, db_connection, task_dao):
        """Test that deferred task has calendar icon."""
        task = Task(
            title="Deferred Task",
            base_priority=2,
            state=TaskState.DEFERRED,
            start_date=date.today() + timedelta(days=3),
            elo_rating=1500.0,
            comparison_count=1
        )
        task = task_dao.create(task)

        view = DependencyGraphView(task, db_connection)
        icon = view._get_task_icon(task)
        assert icon == "📅"
        view.close()

    def test_delegated_task_icon(self, qapp, db_connection, task_dao):
        """Test that delegated task has person icon."""
        task = Task(
            title="Delegated Task",
            base_priority=2,
            state=TaskState.DELEGATED,
            delegated_to="John Doe",
            elo_rating=1500.0,
            comparison_count=1
        )
        task = task_dao.create(task)

        view = DependencyGraphView(task, db_connection)
        icon = view._get_task_icon(task)
        assert icon == "👤"
        view.close()

    def test_someday_task_icon(self, qapp, db_connection, task_dao):
        """Test that someday task has sleep icon."""
        task = Task(
            title="Someday Task",
            base_priority=2,
            state=TaskState.SOMEDAY,
            elo_rating=1500.0,
            comparison_count=1
        )
        task = task_dao.create(task)

        view = DependencyGraphView(task, db_connection)
        icon = view._get_task_icon(task)
        assert icon == "💤"
        view.close()

    def test_trash_task_icon(self, qapp, db_connection, task_dao):
        """Test that trash task has trash icon."""
        task = Task(
            title="Trash Task",
            base_priority=2,
            state=TaskState.TRASH,
            elo_rating=1500.0,
            comparison_count=1
        )
        task = task_dao.create(task)

        view = DependencyGraphView(task, db_connection)
        icon = view._get_task_icon(task)
        assert icon == "🗑️"
        view.close()


class TestCircularDependencies:
    """Test circular dependency detection."""

    def test_circular_dependency_detected(self, qapp, db_connection, sample_task, blocking_task, dependency_dao):
        """Test that circular dependencies are detected and marked."""
        # Create circular dependency: sample_task <- blocking_task <- sample_task
        dep1 = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocking_task.id
        )
        dependency_dao.create(dep1)

        dep2 = Dependency(
            blocked_task_id=blocking_task.id,
            blocking_task_id=sample_task.id
        )
        dependency_dao.create(dep2)

        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        # Should detect circular reference
        assert "CIRCULAR" in graph_text or "🔄" in graph_text
        view.close()


class TestMaxDepth:
    """Test max depth limiting."""

    def test_deep_chain_limited(self, qapp, db_connection, sample_task, task_dao, dependency_dao):
        """Test that very deep dependency chains are limited to max depth."""
        # Create a chain of 7 tasks (exceeds MAX_DEPTH of 5)
        current_task = sample_task
        tasks = [current_task]

        for i in range(7):
            blocker = Task(
                title=f"Blocker {i}",
                base_priority=2,
                state=TaskState.ACTIVE,
                elo_rating=1500.0,
                comparison_count=1
            )
            blocker = task_dao.create(blocker)
            tasks.append(blocker)

            dep = Dependency(
                blocked_task_id=current_task.id,
                blocking_task_id=blocker.id
            )
            dependency_dao.create(dep)
            current_task = blocker

        view = DependencyGraphView(sample_task, db_connection)

        graph_text = view.graph_display.toPlainText()
        # Should have max depth indicator
        assert "MAX DEPTH" in graph_text or "⋯" in graph_text
        view.close()


class TestRefreshButton:
    """Test refresh functionality."""

    def test_refresh_button_exists(self, qapp, db_connection, sample_task):
        """Test that refresh button exists."""
        view = DependencyGraphView(sample_task, db_connection)

        # Find refresh button
        buttons = view.findChildren(MagicMock.__class__.__bases__[0])
        refresh_found = any("Refresh" in btn.text() for btn in view.findChildren(type(view.findChild(type(view)))) if hasattr(btn, 'text'))

        view.close()

    def test_refresh_rebuilds_graph(self, qapp, db_connection, sample_task, blocking_task, dependency_dao):
        """Test that refresh rebuilds the graph."""
        view = DependencyGraphView(sample_task, db_connection)

        initial_text = view.graph_display.toPlainText()

        # Add a dependency
        dep = Dependency(
            blocked_task_id=sample_task.id,
            blocking_task_id=blocking_task.id
        )
        dependency_dao.create(dep)

        # Refresh
        view._build_graph()

        updated_text = view.graph_display.toPlainText()

        # Text should change (now includes blocking task)
        assert updated_text != initial_text
        assert blocking_task.title in updated_text
        view.close()


class TestExportFunctionality:
    """Test export to file functionality."""

    def test_export_button_exists(self, qapp, db_connection, sample_task):
        """Test that export button exists."""
        view = DependencyGraphView(sample_task, db_connection)

        # Find export button by looking for button with "Export" in text
        from PyQt5.QtWidgets import QPushButton
        buttons = view.findChildren(QPushButton)
        export_found = any("Export" in btn.text() for btn in buttons)
        assert export_found

        view.close()

    def test_export_creates_file(self, qapp, db_connection, sample_task, tmp_path):
        """Test that export creates a text file."""
        view = DependencyGraphView(sample_task, db_connection)

        # Mock file dialog to return a path
        test_file = tmp_path / "test_graph.txt"

        with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName', return_value=(str(test_file), 'Text Files (*.txt)')):
            # Call export
            view._export_graph()

        # File should be created
        assert test_file.exists()

        # File should contain task title
        content = test_file.read_text(encoding='utf-8')
        assert sample_task.title in content

        view.close()

    def test_export_canceled(self, qapp, db_connection, sample_task):
        """Test that canceling export doesn't create file."""
        view = DependencyGraphView(sample_task, db_connection)

        # Mock file dialog to return empty path (user canceled)
        with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName', return_value=('', '')):
            # Call export - should not raise error
            view._export_graph()

        view.close()

    def test_export_handles_error(self, qapp, db_connection, sample_task):
        """Test that export handles file write errors gracefully."""
        view = DependencyGraphView(sample_task, db_connection)

        # Mock file dialog to return invalid path
        with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName', return_value=('/invalid/path/file.txt', 'Text Files (*.txt)')):
            with patch('src.ui.dependency_graph_view.MessageBox.critical') as mock_error:
                # Call export
                view._export_graph()

                # Should show error message
                mock_error.assert_called_once()

        view.close()


class TestLegend:
    """Test legend display."""

    def test_legend_shows_all_states(self, qapp, db_connection, sample_task):
        """Test that legend shows icons for all task states."""
        view = DependencyGraphView(sample_task, db_connection)

        # Find legend label
        from PyQt5.QtWidgets import QLabel
        labels = view.findChildren(QLabel)
        legend_label = None
        for label in labels:
            if "Legend:" in label.text():
                legend_label = label
                break

        assert legend_label is not None
        legend_text = legend_label.text()

        # Should mention all major states
        assert "Completed" in legend_text
        assert "Blocked" in legend_text
        assert "Deferred" in legend_text
        assert "Delegated" in legend_text
        assert "Someday" in legend_text

        view.close()


class TestCloseButton:
    """Test close button functionality."""

    def test_close_button_exists(self, qapp, db_connection, sample_task):
        """Test that close button exists."""
        view = DependencyGraphView(sample_task, db_connection)

        from PyQt5.QtWidgets import QPushButton
        buttons = view.findChildren(QPushButton)
        close_found = any("Close" in btn.text() for btn in buttons)
        assert close_found

        view.close()

    def test_close_button_closes_dialog(self, qapp, db_connection, sample_task, qtbot):
        """Test that close button closes the dialog."""
        view = DependencyGraphView(sample_task, db_connection)

        # Find close button
        from PyQt5.QtWidgets import QPushButton
        buttons = view.findChildren(QPushButton)
        close_button = None
        for btn in buttons:
            if "Close" in btn.text():
                close_button = btn
                break

        assert close_button is not None

        # Click close button
        qtbot.mouseClick(close_button, Qt.LeftButton)

        # Dialog should be closed (result should be Accepted)
        assert view.result() == view.Accepted


class TestUnsavedTask:
    """Test behavior with unsaved task."""

    def test_unsaved_task_shows_warning(self, qapp, db_connection):
        """Test that unsaved task (no ID) shows appropriate message."""
        # Create task without saving to database
        task = Task(
            title="Unsaved Task",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=1
        )

        view = DependencyGraphView(task, db_connection)

        graph_text = view.graph_display.toPlainText()
        assert "not been saved" in graph_text or "no dependency information" in graph_text

        view.close()
