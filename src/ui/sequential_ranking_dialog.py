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
from PyQt5.QtGui import QFont, QDrag
from typing import List, Optional
from ..models.task import Task


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

        # Style differently for new vs existing tasks
        if is_existing:
            border_color = "#007bff"  # Blue for existing tasks
            bg_color = "#e7f3ff"
        else:
            border_color = "#28a745"  # Green for new tasks
            bg_color = "#e8f5e9"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 6px;
                padding: 10px;
                margin: 4px;
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self.setLayout(layout)

        # Task title (single line with ellipsis)
        title_label = QLabel(task.title)
        title_font = QFont()
        title_font.setPointSize(11)
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
        subtitle_label.setStyleSheet("color: #666;")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

    def _create_instructions(self, layout: QVBoxLayout):
        """Create the instructions section."""
        instructions_frame = QFrame()
        instructions_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        instructions_layout = QVBoxLayout()
        instructions_frame.setLayout(instructions_layout)

        instructions_label = QLabel(
            "<b>Instructions:</b><br>"
            "• Drag and drop tasks to arrange them from <b>highest priority (top)</b> to <b>lowest priority (bottom)</b><br>"
            "• <span style='color: #28a745;'>Green tasks</span> are new and need ranking<br>"
            "• <span style='color: #007bff;'>Blue tasks</span> are existing tasks shown for reference<br>"
            "• Click <b>Save Ranking</b> when done, or <b>Skip</b> to rank later"
        )
        instructions_label.setWordWrap(True)
        instructions_layout.addWidget(instructions_label)

        layout.addWidget(instructions_frame)

    def _create_ranking_list(self, layout: QVBoxLayout):
        """Create the drag-and-drop ranking list."""
        list_label = QLabel("Drag tasks to arrange in priority order (highest first):")
        list_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(list_label)

        # Create the list widget with drag-and-drop enabled
        self.ranking_list = QListWidget()
        self.ranking_list.setDragDropMode(QListWidget.InternalMove)
        self.ranking_list.setSelectionMode(QListWidget.SingleSelection)
        self.ranking_list.setMinimumHeight(300)
        self.ranking_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 4px;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)

        # Populate the list with task items
        self._populate_ranking_list()

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
            item.setSizeHint(QWidget().sizeHint())

            # Create the task card widget
            task_widget = TaskRankingItem(task, is_existing, self.db_connection)
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
        skip_button = QPushButton("Skip for Now")
        skip_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-size: 11pt;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        skip_button.clicked.connect(self.reject)
        button_layout.addWidget(skip_button)

        button_layout.addStretch()

        # Save ranking button
        save_button = QPushButton("Save Ranking")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_button.clicked.connect(self._on_save_ranking)
        button_layout.addWidget(save_button)

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
