"""
Sequential Ranking Dialog - UI for ranking new tasks in order.

When new tasks are added to a priority band, this dialog presents them
along with the top and bottom existing tasks for the user to rank sequentially.
This prevents new tasks from being "buried in the middle" of the priority band.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QListWidget, QListWidgetItem,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDrag, QPalette, QColor
from typing import List, Optional
from enum import Enum
from ..models.task import Task


class RankingMode(Enum):
    """Modes for the ranking dialog."""
    SELECTION = "selection"  # Navigating to select a task
    MOVEMENT = "movement"    # Moving the selected task


class TaskRankingItem(QFrame):
    """
    A single task item card for the ranking list.
    """

    def __init__(self, task: Task, is_existing: bool = False, db_connection=None, parent=None):
        """
        Initialize a task ranking item.

        Args:
            task: The task to display
            is_existing: True if this is an existing (non-new) task
            db_connection: Shared database connection for loading context/tag info
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task
        self.is_existing = is_existing
        self.db_connection = db_connection

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        # Set object name for styling via QSS
        if is_existing:
            self.setObjectName("existingTaskItem")
        else:
            self.setObjectName("newTaskItem")

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.setLayout(layout)

        # Task title (single line with ellipsis)
        title_label = QLabel(task.title)
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setWordWrap(False)
        # Enable ellipsis for long titles
        from PyQt5.QtCore import Qt
        title_label.setTextFormat(Qt.PlainText)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Build tooltip with full information
        tooltip_parts = [f"<b>{task.title}</b>"]

        # Add state
        if hasattr(task, 'state'):
            tooltip_parts.append(f"State: {task.state.value if hasattr(task.state, 'value') else task.state}")

        # Add context if available (using shared db connection)
        if hasattr(task, 'context_id') and task.context_id and self.db_connection:
            from ..database.context_dao import ContextDAO
            try:
                context_dao = ContextDAO(self.db_connection.get_connection())
                context = context_dao.get_by_id(task.context_id)
                if context:
                    tooltip_parts.append(f"Context: {context.name}")
            except Exception as e:
                # Silently skip if there's an error
                pass

        # Add project tags if available (using shared db connection)
        if hasattr(task, 'project_tags') and task.project_tags and self.db_connection:
            from ..database.project_tag_dao import ProjectTagDAO
            try:
                tag_dao = ProjectTagDAO(self.db_connection.get_connection())
                tag_names = []
                for tag_id in task.project_tags:
                    tag = tag_dao.get_by_id(tag_id)
                    if tag:
                        tag_names.append(tag.name)
                if tag_names:
                    tooltip_parts.append(f"Tags: {', '.join(tag_names)}")
            except Exception as e:
                # Silently skip if there's an error
                pass

        # Add due date
        if task.due_date:
            tooltip_parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d')}")

        # Add description if available
        if task.description:
            tooltip_parts.append(f"<br><i>{task.description}</i>")

        title_label.setToolTip("<br>".join(tooltip_parts))
        layout.addWidget(title_label)

        # Mode indicator label (initially hidden, positioned below title)
        self.mode_label = QLabel("")
        mode_font = QFont()
        mode_font.setPointSize(7)
        mode_font.setBold(True)
        self.mode_label.setFont(mode_font)
        self.mode_label.setVisible(False)
        self.mode_label.setWordWrap(True)
        layout.addWidget(self.mode_label)

    def set_mode_indicator(self, mode: Optional[RankingMode]):
        """
        Set the visual mode indicator for this item.

        Args:
            mode: The current mode (SELECTION or MOVEMENT), or None to clear
        """
        if mode is None:
            self.mode_label.setVisible(False)
            # Reset to default styling
            if self.is_existing:
                self.setObjectName("existingTaskItem")
            else:
                self.setObjectName("newTaskItem")
        elif mode == RankingMode.SELECTION:
            self.mode_label.setText("[Up/Down to Change Task Selection]\n[Enter to Confirm Selection]")
            self.mode_label.setVisible(True)
            self.setObjectName("selectedTaskItem")
        elif mode == RankingMode.MOVEMENT:
            self.mode_label.setText("[Up/Down to Change Task Ranking]\n[Enter or Esc to Confirm Ranking]")
            self.mode_label.setVisible(True)
            self.setObjectName("movingTaskItem")

        # Force style update
        self.style().unpolish(self)
        self.style().polish(self)

        # Update size to accommodate the mode label
        self.adjustSize()
        self.updateGeometry()


class SequentialRankingDialog(QDialog):
    """
    Dialog for ranking new tasks sequentially within a priority band.

    Presents new tasks along with top and bottom existing tasks in randomized order.
    User drags tasks to arrange them in priority order from highest to lowest.
    """

    ranking_completed = pyqtSignal(list)  # Emits list of tasks in ranked order

    def __init__(self,
                 new_tasks: List[Task],
                 top_existing: Optional[Task] = None,
                 bottom_existing: Optional[Task] = None,
                 priority_band: int = 2,
                 db_connection=None,
                 parent=None):
        """
        Initialize the sequential ranking dialog.

        Args:
            new_tasks: List of new tasks (comparison_count = 0) to rank
            top_existing: Highest-ranked existing task in the band (for reference)
            bottom_existing: Lowest-ranked existing task in the band (for reference)
            priority_band: Priority band being ranked (1=Low, 2=Medium, 3=High)
            db_connection: Shared database connection for loading context/tag info
            parent: Parent widget
        """
        super().__init__(parent)
        self.new_tasks = new_tasks
        self.top_existing = top_existing
        self.bottom_existing = bottom_existing
        self.priority_band = priority_band
        self.db_connection = db_connection
        self.ranked_tasks: List[Task] = []

        # Mode tracking
        self.current_mode = RankingMode.SELECTION
        self.previous_selected_row = -1

        priority_names = {1: "Low", 2: "Medium", 3: "High"}
        self.priority_name = priority_names.get(priority_band, "Unknown")

        self.setWindowTitle(f"Rank New {self.priority_name} Priority Tasks")
        self.setMinimumSize(700, 600)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)

        # Title section
        self._create_title_section(layout)

        # Instructions
        self._create_instructions(layout)

        # Ranking list
        self._create_ranking_list(layout)

        # Action buttons
        self._create_action_buttons(layout)

    def _create_title_section(self, layout: QVBoxLayout):
        """Create the title section."""
        title_label = QLabel(f"Rank Your New {self.priority_name} Priority Tasks")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        count_new = len(self.new_tasks)

        # Count existing reference tasks (accounting for potential duplicates if top == bottom)
        existing_refs = []
        if self.top_existing is not None:
            existing_refs.append(self.top_existing)
        if self.bottom_existing is not None and (self.top_existing is None or self.bottom_existing.id != self.top_existing.id):
            existing_refs.append(self.bottom_existing)
        count_ref = len(existing_refs)

        subtitle_text = (
            f"You have {count_new} new task{'s' if count_new != 1 else ''} "
            f"in the {self.priority_name} priority band."
        )
        if count_ref > 0:
            subtitle_text += f" ({count_ref} existing task{'s' if count_ref != 1 else ''} shown for reference)"

        subtitle_label = QLabel(subtitle_text)
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setWordWrap(True)
        subtitle_label.setObjectName("subtitleLabel")
        layout.addWidget(subtitle_label)

    def _create_instructions(self, layout: QVBoxLayout):
        """Create the instructions section."""
        instructions_frame = QFrame()
        instructions_frame.setObjectName("instructionsFrame")
        instructions_layout = QVBoxLayout()
        instructions_frame.setLayout(instructions_layout)

        instructions_label = QLabel(
            "<b>Keyboard Controls:</b><br>"
            "• <b>Up/Down</b>: Navigate tasks (Selection mode) or move task (Movement mode)<br>"
            "• <b>Enter</b>: Toggle between Selection and Movement modes<br>"
            "• <b>Ctrl+S</b>: Save ranking and close | <b>Escape</b>: Exit Movement mode or skip ranking<br>"
            "• Or <b>drag and drop</b> tasks to reorder them"
        )
        instructions_label.setWordWrap(True)
        instructions_layout.addWidget(instructions_label)

        layout.addWidget(instructions_frame)

    def _create_ranking_list(self, layout: QVBoxLayout):
        """Create the drag-and-drop ranking list."""
        # Header with list label and mode indicator
        header_layout = QHBoxLayout()

        list_label = QLabel("Arrange tasks in priority order (highest first):")
        list_label_font = QFont()
        list_label_font.setBold(True)
        list_label.setFont(list_label_font)
        header_layout.addWidget(list_label)

        header_layout.addStretch()

        # Mode indicator
        self.mode_indicator = QLabel("Mode: SELECTION")
        mode_indicator_font = QFont()
        mode_indicator_font.setBold(True)
        mode_indicator_font.setPointSize(9)
        self.mode_indicator.setFont(mode_indicator_font)
        self.mode_indicator.setObjectName("modeIndicator")
        header_layout.addWidget(self.mode_indicator)

        layout.addLayout(header_layout)

        # Create the list widget with drag-and-drop enabled
        self.ranking_list = QListWidget()
        self.ranking_list.setDragDropMode(QListWidget.InternalMove)
        self.ranking_list.setSelectionMode(QListWidget.SingleSelection)
        self.ranking_list.setMinimumHeight(250)
        self.ranking_list.setObjectName("rankingList")

        # Install event filter to intercept key presses
        self.ranking_list.installEventFilter(self)

        # Populate the list with task items
        self._populate_ranking_list()

        # Set focus to list and select first item
        self.ranking_list.setFocus()
        if self.ranking_list.count() > 0:
            self.ranking_list.setCurrentRow(0)
            self._update_mode_visuals()

        layout.addWidget(self.ranking_list)

    def _populate_ranking_list(self):
        """Populate the ranking list with task items."""
        # Combine new tasks and existing reference tasks
        all_items = []

        for task in self.new_tasks:
            all_items.append((task, False))  # False = not existing

        if self.top_existing:
            all_items.append((self.top_existing, True))  # True = existing

        if self.bottom_existing and (not self.top_existing or self.bottom_existing.id != self.top_existing.id):
            all_items.append((self.bottom_existing, True))

        # Randomize the order
        import random
        random.shuffle(all_items)

        # Add items to the list
        for task, is_existing in all_items:
            item = QListWidgetItem(self.ranking_list)

            # Create the task card widget
            task_widget = TaskRankingItem(task, is_existing, self.db_connection)

            # Force the widget to calculate its size
            task_widget.adjustSize()

            # Set the item size hint to match the widget's actual size with some padding
            widget_height = task_widget.sizeHint().height()
            item.setSizeHint(task_widget.sizeHint())

            self.ranking_list.addItem(item)
            self.ranking_list.setItemWidget(item, task_widget)

            # Store task reference in item for later retrieval
            item.setData(Qt.UserRole, task)
            item.setData(Qt.UserRole + 1, is_existing)

    def _create_action_buttons(self, layout: QVBoxLayout):
        """Create action buttons."""
        button_layout = QHBoxLayout()

        # Skip button
        self.skip_button = QPushButton("Skip for Now")
        self.skip_button.clicked.connect(self.reject)
        button_layout.addWidget(self.skip_button)

        button_layout.addStretch()

        # Save ranking button
        self.save_button = QPushButton("Save Ranking")
        self.save_button.setObjectName("primaryButton")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._on_save_ranking)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def _on_save_ranking(self):
        """Handle save ranking button click."""
        # Extract ranked tasks from the list in current order
        ranked_order = []

        for i in range(self.ranking_list.count()):
            item = self.ranking_list.item(i)
            task = item.data(Qt.UserRole)
            is_existing = item.data(Qt.UserRole + 1)

            # Only include new tasks in the result (exclude reference tasks)
            if not is_existing:
                ranked_order.append(task)

        if not ranked_order:
            QMessageBox.warning(
                self,
                "No New Tasks",
                "The ranking list should contain new tasks to rank. "
                "If you want to skip ranking, click 'Skip for Now'."
            )
            return

        self.ranked_tasks = ranked_order
        self.accept()

    def get_ranked_tasks(self) -> List[Task]:
        """
        Get the list of tasks in ranked order.

        Returns:
            List of tasks ordered from highest to lowest priority
        """
        return self.ranked_tasks

    def eventFilter(self, obj, event):
        """
        Event filter to intercept key presses on the ranking list.

        Args:
            obj: The object that generated the event
            event: The event

        Returns:
            True if event was handled, False otherwise
        """
        from PyQt5.QtCore import QEvent

        # Only filter key presses on the ranking list
        if obj == self.ranking_list and event.type() == QEvent.KeyPress:
            key = event.key()

            # Intercept control keys and pass to dialog handler
            if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
                self.keyPressEvent(event)
                return True  # Prevent default list widget behavior

            # Also intercept Ctrl+S
            if key == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
                self.keyPressEvent(event)
                return True

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """
        Handle keyboard events for two-mode navigation system.

        Selection Mode:
        - Up/Down: Navigate between tasks
        - Enter: Enter Movement mode for selected task

        Movement Mode:
        - Up/Down: Move selected task up/down
        - Enter: Return to Selection mode (or save if no changes)
        - Escape: Return to Selection mode

        Args:
            event: The key press event
        """
        from PyQt5.QtCore import Qt

        key = event.key()

        # Escape key behavior depends on mode
        if key == Qt.Key_Escape:
            if self.current_mode == RankingMode.MOVEMENT:
                # Exit movement mode back to selection
                self._switch_to_selection_mode()
                return
            else:
                # Cancel/skip the dialog
                self.reject()
                return

        # Ctrl+S to save and close
        if key == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
            self._on_save_ranking()
            return

        # Enter key behavior depends on mode
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.current_mode == RankingMode.SELECTION:
                # Enter movement mode
                self._switch_to_movement_mode()
                return
            else:  # MOVEMENT mode
                # Return to selection mode
                self._switch_to_selection_mode()
                return

        # Up/Down key behavior depends on mode
        if key == Qt.Key_Up:
            if self.current_mode == RankingMode.SELECTION:
                # Navigate to previous task
                self._navigate_up()
                return
            else:  # MOVEMENT mode
                # Move task up
                self._move_selected_item_up()
                return

        if key == Qt.Key_Down:
            if self.current_mode == RankingMode.SELECTION:
                # Navigate to next task
                self._navigate_down()
                return
            else:  # MOVEMENT mode
                # Move task down
                self._move_selected_item_down()
                return

        # Pass other events to parent
        super().keyPressEvent(event)

    def _switch_to_movement_mode(self):
        """Switch from Selection mode to Movement mode."""
        self.current_mode = RankingMode.MOVEMENT
        self.mode_indicator.setText("Mode: MOVEMENT")
        self._update_mode_visuals()

    def _switch_to_selection_mode(self):
        """Switch from Movement mode to Selection mode."""
        self.current_mode = RankingMode.SELECTION
        self.mode_indicator.setText("Mode: SELECTION")
        self._update_mode_visuals()

    def _update_mode_visuals(self):
        """Update visual indicators for all items based on current mode and selection."""
        current_row = self.ranking_list.currentRow()
        if current_row < 0:
            return  # No selection

        for i in range(self.ranking_list.count()):
            item = self.ranking_list.item(i)
            if not item:
                continue

            widget = self.ranking_list.itemWidget(item)
            if not isinstance(widget, TaskRankingItem):
                continue

            try:
                if i == current_row:
                    # Current item shows mode indicator
                    widget.set_mode_indicator(self.current_mode)
                    # Update item size hint to accommodate mode label
                    item.setSizeHint(widget.sizeHint())
                else:
                    # Other items have no indicator
                    widget.set_mode_indicator(None)
                    # Update item size hint
                    item.setSizeHint(widget.sizeHint())
            except Exception as e:
                # Log error but don't crash
                print(f"Error updating mode visuals for item {i}: {e}")
                continue

    def _navigate_up(self):
        """Navigate to the previous task in Selection mode."""
        current_row = self.ranking_list.currentRow()
        if current_row > 0:
            self.ranking_list.setCurrentRow(current_row - 1)
            self._update_mode_visuals()

    def _navigate_down(self):
        """Navigate to the next task in Selection mode."""
        current_row = self.ranking_list.currentRow()
        if current_row < self.ranking_list.count() - 1:
            self.ranking_list.setCurrentRow(current_row + 1)
            self._update_mode_visuals()

    def _move_selected_item_up(self):
        """Move the currently selected item up in Movement mode."""
        current_row = self.ranking_list.currentRow()
        if current_row <= 0:
            return  # Already at top

        # Get the task data from both items
        current_item = self.ranking_list.item(current_row)
        above_item = self.ranking_list.item(current_row - 1)

        if not current_item or not above_item:
            return

        current_task = current_item.data(Qt.UserRole)
        current_is_existing = current_item.data(Qt.UserRole + 1)
        above_task = above_item.data(Qt.UserRole)
        above_is_existing = above_item.data(Qt.UserRole + 1)

        # Swap the data
        current_item.setData(Qt.UserRole, above_task)
        current_item.setData(Qt.UserRole + 1, above_is_existing)
        above_item.setData(Qt.UserRole, current_task)
        above_item.setData(Qt.UserRole + 1, current_is_existing)

        # Recreate widgets with swapped data
        self._recreate_widget_for_item(current_item, above_task, above_is_existing)
        self._recreate_widget_for_item(above_item, current_task, current_is_existing)

        # Update the current selection
        self.ranking_list.setCurrentRow(current_row - 1)

        # Update visuals
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._update_mode_visuals)

    def _move_selected_item_down(self):
        """Move the currently selected item down in Movement mode."""
        current_row = self.ranking_list.currentRow()
        if current_row < 0 or current_row >= self.ranking_list.count() - 1:
            return  # Already at bottom or invalid

        # Get the task data from both items
        current_item = self.ranking_list.item(current_row)
        below_item = self.ranking_list.item(current_row + 1)

        if not current_item or not below_item:
            return

        current_task = current_item.data(Qt.UserRole)
        current_is_existing = current_item.data(Qt.UserRole + 1)
        below_task = below_item.data(Qt.UserRole)
        below_is_existing = below_item.data(Qt.UserRole + 1)

        # Swap the data
        current_item.setData(Qt.UserRole, below_task)
        current_item.setData(Qt.UserRole + 1, below_is_existing)
        below_item.setData(Qt.UserRole, current_task)
        below_item.setData(Qt.UserRole + 1, current_is_existing)

        # Recreate widgets with swapped data
        self._recreate_widget_for_item(current_item, below_task, below_is_existing)
        self._recreate_widget_for_item(below_item, current_task, current_is_existing)

        # Update the current selection
        self.ranking_list.setCurrentRow(current_row + 1)

        # Update visuals
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._update_mode_visuals)

    def _recreate_widget_for_item(self, item: QListWidgetItem, task: Task, is_existing: bool):
        """
        Recreate the widget for a list item with new task data.

        Args:
            item: The list widget item
            task: The task to display
            is_existing: Whether this is an existing reference task
        """
        # Remove old widget if it exists
        old_widget = self.ranking_list.itemWidget(item)
        if old_widget:
            old_widget.setParent(None)
            old_widget.deleteLater()

        # Create new widget
        new_widget = TaskRankingItem(task, is_existing, self.db_connection)
        new_widget.adjustSize()

        # Set the new widget
        item.setSizeHint(new_widget.sizeHint())
        self.ranking_list.setItemWidget(item, new_widget)
