"""
Task History Dialog for OneTaskAtATime.

Displays a comprehensive timeline view of all events in a task's history.
"""

from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

from src.models.task import Task
from src.models.task_history_event import TaskHistoryEvent
from src.models.enums import TaskEventType
from src.services.task_history_service import TaskHistoryService


class TaskHistoryDialog(QDialog):
    """
    Dialog for viewing a task's complete history timeline.

    Displays all events that have occurred in a task's lifecycle,
    grouped by date with human-readable descriptions.
    """

    def __init__(self, task: Task, history_service: TaskHistoryService, parent=None):
        """
        Initialize the Task History Dialog.

        Args:
            task: The task to show history for
            history_service: Service for retrieving history events
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task
        self.history_service = history_service
        self.all_events = []

        self.setWindowTitle(f"Task History: {task.title}")
        self.setMinimumSize(700, 500)
        self.setModal(False)

        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Header with task title
        header_label = QLabel(f"<h2>Task History</h2><p><b>{self.task.title}</b></p>")
        layout.addWidget(header_label)

        # Filter controls
        filter_layout = QHBoxLayout()

        filter_label = QLabel("Filter:")
        filter_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Events", None)
        self.filter_combo.addItem("Task Created", TaskEventType.CREATED)
        self.filter_combo.addItem("Edits", TaskEventType.EDITED)
        self.filter_combo.addItem("Completed", TaskEventType.COMPLETED)
        self.filter_combo.addItem("Deferred", TaskEventType.DEFERRED)
        self.filter_combo.addItem("Delegated", TaskEventType.DELEGATED)
        self.filter_combo.addItem("State Changes", "state_changes")
        self.filter_combo.addItem("Priority Changes", TaskEventType.PRIORITY_CHANGED)
        self.filter_combo.addItem("Comparisons", "comparisons")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addStretch()

        # Export button (placeholder for future)
        self.export_button = QPushButton("Export...")
        self.export_button.setEnabled(False)  # TODO: Implement export functionality
        filter_layout.addWidget(self.export_button)

        layout.addLayout(filter_layout)

        # Timeline tree widget
        self.timeline_tree = QTreeWidget()
        self.timeline_tree.setHeaderLabels(["Time", "Event", "Changed By"])
        self.timeline_tree.setColumnWidth(0, 180)
        self.timeline_tree.setColumnWidth(1, 380)
        self.timeline_tree.setColumnWidth(2, 100)
        self.timeline_tree.setAlternatingRowColors(True)
        self.timeline_tree.setRootIsDecorated(False)
        self.timeline_tree.header().setStretchLastSection(True)
        layout.addWidget(self.timeline_tree)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _load_history(self):
        """Load task history events from the database."""
        try:
            self.all_events = self.history_service.get_timeline(self.task.id, limit=500)
            self._populate_timeline(self.all_events)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Loading History",
                f"Failed to load task history: {str(e)}"
            )

    def _populate_timeline(self, events: list):
        """
        Populate the timeline tree with events.

        Args:
            events: List of TaskHistoryEvent objects to display
        """
        self.timeline_tree.clear()

        if not events:
            item = QTreeWidgetItem(["", "No history events found", ""])
            item.setForeground(1, Qt.gray)
            self.timeline_tree.addTopLevelItem(item)
            return

        # Group events by date
        grouped_events = self._group_events_by_date(events)

        # Add events to tree
        for date_label, event_list in grouped_events:
            # Add date header
            date_item = QTreeWidgetItem([date_label, "", ""])
            date_item.setForeground(0, Qt.darkGray)
            date_item.setBackground(0, Qt.lightGray)
            date_item.setBackground(1, Qt.lightGray)
            date_item.setBackground(2, Qt.lightGray)
            font = date_item.font(0)
            font.setBold(True)
            date_item.setFont(0, font)
            self.timeline_tree.addTopLevelItem(date_item)

            # Add events under this date
            for event in event_list:
                time_str = event.event_timestamp.strftime("%I:%M %p")
                description = self.history_service.get_formatted_summary(event)
                changed_by = event.changed_by.capitalize()

                event_item = QTreeWidgetItem([time_str, description, changed_by])

                # Add icon/indicator based on event type
                self._style_event_item(event_item, event.event_type)

                self.timeline_tree.addTopLevelItem(event_item)

        # Expand all by default
        self.timeline_tree.expandAll()

    def _group_events_by_date(self, events: list) -> list:
        """
        Group events by date with human-readable labels.

        Args:
            events: List of TaskHistoryEvent objects

        Returns:
            List of tuples (date_label, events_for_date)
        """
        grouped = {}
        now = datetime.now()
        today = now.date()
        yesterday = (now - timedelta(days=1)).date()

        for event in events:
            event_date = event.event_timestamp.date()

            if event_date == today:
                date_label = "Today"
            elif event_date == yesterday:
                date_label = "Yesterday"
            elif event_date > today - timedelta(days=7):
                date_label = event.event_timestamp.strftime("%A")  # Day name
            else:
                date_label = event.event_timestamp.strftime("%B %d, %Y")

            if date_label not in grouped:
                grouped[date_label] = []

            grouped[date_label].append(event)

        # Return in chronological order (most recent first)
        return [(label, grouped[label]) for label in grouped.keys()]

    def _style_event_item(self, item: QTreeWidgetItem, event_type: TaskEventType):
        """
        Apply styling to an event item based on its type.

        Args:
            item: QTreeWidgetItem to style
            event_type: Type of event
        """
        # Add bullet/icon indicator
        if event_type == TaskEventType.CREATED:
            item.setText(1, "● " + item.text(1))
            item.setForeground(1, Qt.blue)
        elif event_type == TaskEventType.COMPLETED:
            item.setText(1, "✓ " + item.text(1))
            item.setForeground(1, Qt.darkGreen)
        elif event_type in [TaskEventType.DEFERRED, TaskEventType.DELEGATED]:
            item.setText(1, "◷ " + item.text(1))
            item.setForeground(1, Qt.darkYellow)
        elif event_type in [TaskEventType.MOVED_TO_TRASH]:
            item.setText(1, "✗ " + item.text(1))
            item.setForeground(1, Qt.red)
        elif event_type in [TaskEventType.PRIORITY_CHANGED]:
            item.setText(1, "★ " + item.text(1))
            item.setForeground(1, Qt.darkMagenta)
        elif event_type in [TaskEventType.COMPARISON_WON, TaskEventType.COMPARISON_LOST]:
            item.setText(1, "⚖ " + item.text(1))
            item.setForeground(1, Qt.darkCyan)
        else:
            item.setText(1, "• " + item.text(1))

    def _apply_filter(self):
        """Apply the selected event type filter."""
        selected_filter = self.filter_combo.currentData()

        if selected_filter is None:
            # Show all events
            filtered_events = self.all_events
        elif selected_filter == "state_changes":
            # Show all state change events
            state_change_types = [
                TaskEventType.COMPLETED,
                TaskEventType.DEFERRED,
                TaskEventType.DELEGATED,
                TaskEventType.ACTIVATED,
                TaskEventType.MOVED_TO_SOMEDAY,
                TaskEventType.MOVED_TO_TRASH,
                TaskEventType.RESTORED
            ]
            filtered_events = [e for e in self.all_events if e.event_type in state_change_types]
        elif selected_filter == "comparisons":
            # Show comparison events
            filtered_events = [
                e for e in self.all_events
                if e.event_type in [TaskEventType.COMPARISON_WON, TaskEventType.COMPARISON_LOST]
            ]
        else:
            # Filter by specific event type
            filtered_events = [e for e in self.all_events if e.event_type == selected_filter]

        self._populate_timeline(filtered_events)
