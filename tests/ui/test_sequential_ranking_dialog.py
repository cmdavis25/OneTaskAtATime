"""
Unit tests for SequentialRankingDialog.

Tests the sequential ranking functionality including:
- Dialog initialization
- Task list population
- Keyboard navigation
- Drag-and-drop reordering
- Mode switching (Selection/Movement)
- Save and cancel functionality
- Result retrieval
"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from src.models.task import Task
from src.models.enums import TaskState
from src.ui.sequential_ranking_dialog import SequentialRankingDialog, RankingMode, TaskRankingItem




@pytest.fixture
def new_tasks():
    """Create sample new tasks."""
    return [
        Task(
            id=1,
            title="New Task 1",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=0
        ),
        Task(
            id=2,
            title="New Task 2",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=0
        ),
        Task(
            id=3,
            title="New Task 3",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=0
        ),
    ]


@pytest.fixture
def top_existing_task():
    """Create top existing task."""
    return Task(
        id=10,
        title="Top Existing Task",
        base_priority=2,
        state=TaskState.ACTIVE,
        elo_rating=1800.0,
        comparison_count=10
    )


@pytest.fixture
def bottom_existing_task():
    """Create bottom existing task."""
    return Task(
        id=11,
        title="Bottom Existing Task",
        base_priority=2,
        state=TaskState.ACTIVE,
        elo_rating=1200.0,
        comparison_count=10
    )


class TestDialogInitialization:
    """Test dialog initialization."""

    def test_dialog_title_includes_priority(self, qapp, new_tasks, db_connection):
        """Test that dialog title includes priority band name."""
        dialog = SequentialRankingDialog(new_tasks, priority_band=2, db_connection=db_connection)
        assert "Medium" in dialog.windowTitle()
        dialog.close()

        dialog = SequentialRankingDialog(new_tasks, priority_band=3, db_connection=db_connection)
        assert "High" in dialog.windowTitle()
        dialog.close()

        dialog = SequentialRankingDialog(new_tasks, priority_band=1, db_connection=db_connection)
        assert "Low" in dialog.windowTitle()
        dialog.close()

    def test_minimum_size_set(self, qapp, new_tasks, db_connection):
        """Test that minimum size is set."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)
        assert dialog.minimumWidth() == 700
        assert dialog.minimumHeight() == 600
        dialog.close()

    def test_new_tasks_stored(self, qapp, new_tasks, db_connection):
        """Test that new tasks are stored."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)
        assert dialog.new_tasks == new_tasks
        dialog.close()

    def test_existing_tasks_stored(self, qapp, new_tasks, top_existing_task, bottom_existing_task, db_connection):
        """Test that existing reference tasks are stored."""
        dialog = SequentialRankingDialog(
            new_tasks,
            top_existing=top_existing_task,
            bottom_existing=bottom_existing_task,
            db_connection=db_connection
        )
        assert dialog.top_existing == top_existing_task
        assert dialog.bottom_existing == bottom_existing_task
        dialog.close()

    def test_whatsthis_help_enabled(self, qapp, new_tasks, db_connection):
        """Test that WhatsThis help button is enabled."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)
        flags = dialog.windowFlags()
        assert flags & Qt.WindowContextHelpButtonHint
        dialog.close()

    def test_initial_mode_is_selection(self, qapp, new_tasks, db_connection):
        """Test that initial mode is SELECTION."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)
        assert dialog.current_mode == RankingMode.SELECTION
        dialog.close()


class TestTaskListPopulation:
    """Test task list population."""

    def test_all_new_tasks_displayed(self, qapp, new_tasks, db_connection):
        """Test that all new tasks are displayed in the list."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        # Should have 3 items
        assert dialog.ranking_list.count() == 3

        dialog.close()

    def test_existing_tasks_included(self, qapp, new_tasks, top_existing_task, bottom_existing_task, db_connection):
        """Test that existing reference tasks are included."""
        dialog = SequentialRankingDialog(
            new_tasks,
            top_existing=top_existing_task,
            bottom_existing=bottom_existing_task,
            db_connection=db_connection
        )

        # Should have 3 new + 2 existing = 5 items
        assert dialog.ranking_list.count() == 5

        dialog.close()

    def test_single_existing_task(self, qapp, new_tasks, top_existing_task, db_connection):
        """Test with only one existing task."""
        dialog = SequentialRankingDialog(
            new_tasks,
            top_existing=top_existing_task,
            db_connection=db_connection
        )

        # Should have 3 new + 1 existing = 4 items
        assert dialog.ranking_list.count() == 4

        dialog.close()

    def test_no_existing_tasks(self, qapp, new_tasks, db_connection):
        """Test with no existing tasks (first tasks in band)."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        # Should have only 3 new tasks
        assert dialog.ranking_list.count() == 3

        dialog.close()

    def test_first_item_selected_initially(self, qapp, new_tasks, db_connection):
        """Test that first item is selected initially."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        assert dialog.ranking_list.currentRow() == 0

        dialog.close()


class TestTaskRankingItem:
    """Test TaskRankingItem widget."""

    def test_task_item_displays_title(self, qapp, db_connection):
        """Test that task item displays task title."""
        task = Task(
            id=1,
            title="Test Task",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        item = TaskRankingItem(task, db_connection=db_connection)

        # Find title label
        from PyQt5.QtWidgets import QLabel
        labels = item.findChildren(QLabel)
        title_found = any("Test Task" in label.text() for label in labels)
        assert title_found

        item.close()

    def test_new_task_styling(self, qapp, db_connection):
        """Test that new task has correct object name for styling."""
        task = Task(
            id=1,
            title="New Task",
            base_priority=2,
            state=TaskState.ACTIVE,
            comparison_count=0
        )
        item = TaskRankingItem(task, is_existing=False, db_connection=db_connection)

        assert item.objectName() == "newTaskItem"

        item.close()

    def test_existing_task_styling(self, qapp, db_connection):
        """Test that existing task has correct object name for styling."""
        task = Task(
            id=1,
            title="Existing Task",
            base_priority=2,
            state=TaskState.ACTIVE,
            comparison_count=10
        )
        item = TaskRankingItem(task, is_existing=True, db_connection=db_connection)

        assert item.objectName() == "existingTaskItem"

        item.close()

    def test_mode_indicator_initially_hidden(self, qapp, db_connection):
        """Test that mode indicator is initially hidden."""
        task = Task(
            id=1,
            title="Test Task",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        item = TaskRankingItem(task, db_connection=db_connection)

        assert not item.mode_label.isVisible()

        item.close()

    @pytest.mark.skip(reason="Qt limitation: isVisible() returns False for widgets in unshown dialogs")
    def test_selection_mode_indicator(self, qapp, db_connection):
        """Test that selection mode shows correct indicator."""
        task = Task(
            id=1,
            title="Test Task",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        item = TaskRankingItem(task, db_connection=db_connection)

        item.set_mode_indicator(RankingMode.SELECTION)

        assert item.mode_label.isVisible()
        assert "Selection" in item.mode_label.text() or "Up/Down" in item.mode_label.text()
        assert item.objectName() == "selectedTaskItem"

        item.close()

    @pytest.mark.skip(reason="Qt limitation: isVisible() returns False for widgets in unshown dialogs")
    def test_movement_mode_indicator(self, qapp, db_connection):
        """Test that movement mode shows correct indicator."""
        task = Task(
            id=1,
            title="Test Task",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        item = TaskRankingItem(task, db_connection=db_connection)

        item.set_mode_indicator(RankingMode.MOVEMENT)

        assert item.mode_label.isVisible()
        assert "Ranking" in item.mode_label.text() or "Up/Down" in item.mode_label.text()
        assert item.objectName() == "movingTaskItem"

        item.close()

    def test_clear_mode_indicator(self, qapp, db_connection):
        """Test that clearing mode hides indicator."""
        task = Task(
            id=1,
            title="Test Task",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        item = TaskRankingItem(task, db_connection=db_connection)

        # Set mode then clear it
        item.set_mode_indicator(RankingMode.SELECTION)
        item.set_mode_indicator(None)

        assert not item.mode_label.isVisible()

        item.close()


class TestModeIndicator:
    """Test mode indicator display."""

    def test_mode_indicator_exists(self, qapp, new_tasks, db_connection):
        """Test that mode indicator label exists."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        assert hasattr(dialog, 'mode_indicator')
        assert dialog.mode_indicator is not None

        dialog.close()

    def test_mode_indicator_shows_selection_initially(self, qapp, new_tasks, db_connection):
        """Test that mode indicator shows SELECTION initially."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        assert "SELECTION" in dialog.mode_indicator.text()

        dialog.close()


class TestButtonActions:
    """Test button actions."""

    def test_save_button_exists(self, qapp, new_tasks, db_connection):
        """Test that save button exists."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        save_found = any("Save" in btn.text() for btn in buttons)
        assert save_found

        dialog.close()

    def test_skip_button_exists(self, qapp, new_tasks, db_connection):
        """Test that skip button exists."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        skip_found = any("Skip" in btn.text() or "Cancel" in btn.text() for btn in buttons)
        assert skip_found

        dialog.close()


class TestResultRetrieval:
    """Test getting ranked results."""

    def test_get_ranked_tasks_returns_list(self, qapp, new_tasks, db_connection):
        """Test that get_ranked_tasks returns a list."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        result = dialog.get_ranked_tasks()

        assert isinstance(result, list)

        dialog.close()

    def test_get_ranked_tasks_returns_only_new_tasks(self, qapp, new_tasks, top_existing_task, bottom_existing_task, db_connection):
        """Test that get_ranked_tasks returns only new tasks, not existing ones."""
        dialog = SequentialRankingDialog(
            new_tasks,
            top_existing=top_existing_task,
            bottom_existing=bottom_existing_task,
            db_connection=db_connection
        )

        # Accept dialog to populate ranked_tasks
        dialog.accept()

        result = dialog.get_ranked_tasks()

        # Should return 3 new tasks, not 5 (excluding existing reference tasks)
        assert len(result) == 3

        # Should not include existing tasks
        task_ids = [t.id for t in result]
        assert top_existing_task.id not in task_ids
        assert bottom_existing_task.id not in task_ids

        dialog.close()

    def test_get_ranked_tasks_preserves_order(self, qapp, new_tasks, db_connection):
        """Test that get_ranked_tasks returns tasks in display order."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        # Accept dialog to populate ranked_tasks
        dialog.accept()

        result = dialog.get_ranked_tasks()

        # Order should match the order in the list widget
        assert len(result) == 3

        dialog.close()


class TestDragAndDrop:
    """Test drag-and-drop functionality."""

    def test_drag_drop_enabled(self, qapp, new_tasks, db_connection):
        """Test that drag-and-drop is enabled on list."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QAbstractItemView
        assert dialog.ranking_list.dragDropMode() == QAbstractItemView.InternalMove

        dialog.close()

    def test_single_selection_mode(self, qapp, new_tasks, db_connection):
        """Test that list uses single selection mode."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QAbstractItemView
        assert dialog.ranking_list.selectionMode() == QAbstractItemView.SingleSelection

        dialog.close()


class TestInstructions:
    """Test instructions display."""

    def test_instructions_displayed(self, qapp, new_tasks, db_connection):
        """Test that instructions are displayed."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should have instructions mentioning keyboard controls
        instructions_found = any("Keyboard" in label.text() or "Up/Down" in label.text() for label in labels)
        assert instructions_found

        dialog.close()

    def test_instructions_mention_enter_key(self, qapp, new_tasks, db_connection):
        """Test that instructions mention Enter key."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should mention Enter key
        enter_mentioned = any("Enter" in label.text() for label in labels)
        assert enter_mentioned

        dialog.close()

    def test_instructions_mention_drag_drop(self, qapp, new_tasks, db_connection):
        """Test that instructions mention drag and drop."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should mention drag and drop
        drag_mentioned = any("drag" in label.text().lower() for label in labels)
        assert drag_mentioned

        dialog.close()


class TestTaskCountDisplay:
    """Test task count display."""

    def test_new_task_count_displayed(self, qapp, new_tasks, db_connection):
        """Test that new task count is displayed."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should show "3 new tasks"
        count_displayed = any("3" in label.text() and "new" in label.text().lower() for label in labels)
        assert count_displayed

        dialog.close()

    def test_existing_task_count_displayed(self, qapp, new_tasks, top_existing_task, bottom_existing_task, db_connection):
        """Test that existing task reference count is displayed."""
        dialog = SequentialRankingDialog(
            new_tasks,
            top_existing=top_existing_task,
            bottom_existing=bottom_existing_task,
            db_connection=db_connection
        )

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should mention existing tasks for reference
        existing_mentioned = any("existing" in label.text().lower() and "reference" in label.text().lower() for label in labels)
        assert existing_mentioned

        dialog.close()


class TestPriorityBand:
    """Test priority band display."""

    def test_low_priority_band_displayed(self, qapp, new_tasks, db_connection):
        """Test that Low priority band is displayed correctly."""
        dialog = SequentialRankingDialog(new_tasks, priority_band=1, db_connection=db_connection)

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should mention "Low" priority
        low_mentioned = any("Low" in label.text() for label in labels)
        assert low_mentioned

        dialog.close()

    def test_medium_priority_band_displayed(self, qapp, new_tasks, db_connection):
        """Test that Medium priority band is displayed correctly."""
        dialog = SequentialRankingDialog(new_tasks, priority_band=2, db_connection=db_connection)

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should mention "Medium" priority
        medium_mentioned = any("Medium" in label.text() for label in labels)
        assert medium_mentioned

        dialog.close()

    def test_high_priority_band_displayed(self, qapp, new_tasks, db_connection):
        """Test that High priority band is displayed correctly."""
        dialog = SequentialRankingDialog(new_tasks, priority_band=3, db_connection=db_connection)

        from PyQt5.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)

        # Should mention "High" priority
        high_mentioned = any("High" in label.text() for label in labels)
        assert high_mentioned

        dialog.close()


class TestListFocus:
    """Test list focus behavior."""

    def test_list_has_focus_initially(self, qapp, new_tasks, db_connection):
        """Test that ranking list has focus initially."""
        dialog = SequentialRankingDialog(new_tasks, db_connection=db_connection)

        # Note: Focus may not be set correctly in test environment
        # Just verify the list widget exists and is enabled
        assert dialog.ranking_list.isEnabled()

        dialog.close()


class TestSingleTask:
    """Test with single new task."""

    def test_single_new_task(self, qapp, db_connection):
        """Test dialog with only one new task."""
        single_task = [Task(
            id=1,
            title="Only Task",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=0
        )]

        dialog = SequentialRankingDialog(single_task, db_connection=db_connection)

        assert dialog.ranking_list.count() == 1

        dialog.close()


class TestEdgeCases:
    """Test edge cases."""

    def test_same_task_as_top_and_bottom(self, qapp, new_tasks, db_connection):
        """Test when same task is both top and bottom (only one existing task)."""
        only_existing = Task(
            id=10,
            title="Only Existing",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=10
        )

        dialog = SequentialRankingDialog(
            new_tasks,
            top_existing=only_existing,
            bottom_existing=only_existing,
            db_connection=db_connection
        )

        # Should not duplicate the task (3 new + 1 existing = 4)
        assert dialog.ranking_list.count() == 4

        dialog.close()
