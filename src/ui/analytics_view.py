"""
AnalyticsView for OneTaskAtATime application.

Dashboard showing postpone patterns and statistics.
Helps users identify tasks that are frequently postponed and understand why.
"""

from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QScrollArea,
    QWidget, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ..models.postpone_record import PostponeRecord
from ..models.enums import PostponeReasonType, ActionTaken
from ..database.postpone_history_dao import PostponeHistoryDAO
from ..database.task_dao import TaskDAO


class AnalyticsView(QDialog):
    """
    Dashboard displaying postpone analytics across all tasks.

    Four panels:
    1. Postpone Reason Breakdown - Distribution of reasons
    2. Most Postponed Tasks - Top 10 tasks by postpone count
    3. Recent Activity - Last 20 postpone events
    4. Action Taken Summary - Distribution of actions
    """

    def __init__(self, db_connection, parent=None):
        """
        Initialize analytics view.

        Args:
            db_connection: Database connection (raw or wrapper)
            parent: Parent widget
        """
        super().__init__(parent)

        # Handle both raw connection and DatabaseConnection wrapper
        if hasattr(db_connection, 'get_connection'):
            self.db = db_connection.get_connection()
        else:
            self.db = db_connection

        self.postpone_dao = PostponeHistoryDAO(self.db)
        self.task_dao = TaskDAO(self.db)

        self.setWindowTitle("Postpone Analytics Dashboard")
        self.setModal(False)  # Non-blocking
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📊 Postpone Analytics Dashboard")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("padding: 10px;")
        layout.addWidget(header)

        # Scroll area for panels
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Panel 1: Postpone Reason Breakdown
        self.reason_breakdown_panel = self._create_reason_breakdown_panel()
        scroll_layout.addWidget(self.reason_breakdown_panel)

        # Panel 2: Most Postponed Tasks
        self.most_postponed_panel = self._create_most_postponed_panel()
        scroll_layout.addWidget(self.most_postponed_panel)

        # Panel 3: Recent Activity
        self.recent_activity_panel = self._create_recent_activity_panel()
        scroll_layout.addWidget(self.recent_activity_panel)

        # Panel 4: Action Taken Summary
        self.action_summary_panel = self._create_action_summary_panel()
        scroll_layout.addWidget(self.action_summary_panel)

        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Buttons
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("🔄 Refresh Data")
        refresh_button.clicked.connect(self._load_data)
        button_layout.addWidget(refresh_button)

        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _create_reason_breakdown_panel(self) -> QGroupBox:
        """Create panel showing postpone reason distribution."""
        panel = QGroupBox("Postpone Reason Breakdown")
        layout = QVBoxLayout()

        self.reason_table = QTableWidget()
        self.reason_table.setColumnCount(3)
        self.reason_table.setHorizontalHeaderLabels(["Reason", "Count", "Percentage"])
        self.reason_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.reason_table.setMaximumHeight(200)

        layout.addWidget(self.reason_table)
        panel.setLayout(layout)
        return panel

    def _create_most_postponed_panel(self) -> QGroupBox:
        """Create panel showing most frequently postponed tasks."""
        panel = QGroupBox("Most Postponed Tasks (Top 10)")
        layout = QVBoxLayout()

        self.most_postponed_table = QTableWidget()
        self.most_postponed_table.setColumnCount(4)
        self.most_postponed_table.setHorizontalHeaderLabels(
            ["Task Title", "Total Postpones", "Most Common Reason", "Last Postponed"]
        )
        self.most_postponed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.most_postponed_table.setMaximumHeight(300)

        layout.addWidget(self.most_postponed_table)
        panel.setLayout(layout)
        return panel

    def _create_recent_activity_panel(self) -> QGroupBox:
        """Create panel showing recent postpone events."""
        panel = QGroupBox("Recent Activity (Last 20 Events)")
        layout = QVBoxLayout()

        self.recent_activity_table = QTableWidget()
        self.recent_activity_table.setColumnCount(5)
        self.recent_activity_table.setHorizontalHeaderLabels(
            ["Date/Time", "Task", "Reason", "Action Taken", "Notes"]
        )
        self.recent_activity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.recent_activity_table.setMaximumHeight(250)

        layout.addWidget(self.recent_activity_table)
        panel.setLayout(layout)
        return panel

    def _create_action_summary_panel(self) -> QGroupBox:
        """Create panel showing action taken distribution."""
        panel = QGroupBox("Action Taken Summary")
        layout = QVBoxLayout()

        self.action_table = QTableWidget()
        self.action_table.setColumnCount(3)
        self.action_table.setHorizontalHeaderLabels(["Action", "Count", "Percentage"])
        self.action_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.action_table.setMaximumHeight(200)

        layout.addWidget(self.action_table)
        panel.setLayout(layout)
        return panel

    def _load_data(self):
        """Load and display all analytics data."""
        # Get postpone history (last 100 records for analysis)
        recent_records = self.postpone_dao.get_recent(limit=100)

        if not recent_records:
            # Show empty state
            self._show_empty_state()
            return

        self._populate_reason_breakdown(recent_records)
        self._populate_most_postponed(recent_records)
        self._populate_recent_activity(recent_records[:20])  # Last 20
        self._populate_action_summary(recent_records)

    def _show_empty_state(self):
        """Show message when no data is available."""
        empty_msg = "No postpone data available yet. Start postponing tasks to see analytics!"

        # Clear all tables
        self.reason_table.setRowCount(1)
        self.reason_table.setItem(0, 0, QTableWidgetItem(empty_msg))
        self.reason_table.setSpan(0, 0, 1, 3)

        self.most_postponed_table.setRowCount(1)
        self.most_postponed_table.setItem(0, 0, QTableWidgetItem(empty_msg))
        self.most_postponed_table.setSpan(0, 0, 1, 4)

        self.recent_activity_table.setRowCount(1)
        self.recent_activity_table.setItem(0, 0, QTableWidgetItem(empty_msg))
        self.recent_activity_table.setSpan(0, 0, 1, 5)

        self.action_table.setRowCount(1)
        self.action_table.setItem(0, 0, QTableWidgetItem(empty_msg))
        self.action_table.setSpan(0, 0, 1, 3)

    def _populate_reason_breakdown(self, records: List[PostponeRecord]):
        """Populate reason breakdown table."""
        reason_counts = Counter(record.reason_type for record in records)
        total = len(records)

        self.reason_table.setRowCount(len(reason_counts))

        for i, (reason, count) in enumerate(reason_counts.most_common()):
            percentage = (count / total) * 100

            # Reason
            reason_item = QTableWidgetItem(self._format_reason(reason))
            self.reason_table.setItem(i, 0, reason_item)

            # Count
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.reason_table.setItem(i, 1, count_item)

            # Percentage
            percentage_item = QTableWidgetItem(f"{percentage:.1f}%")
            percentage_item.setTextAlignment(Qt.AlignCenter)
            self.reason_table.setItem(i, 2, percentage_item)

    def _populate_most_postponed(self, records: List[PostponeRecord]):
        """Populate most postponed tasks table."""
        # Group by task ID
        task_data: Dict[int, Dict[str, Any]] = {}

        for record in records:
            task_id = record.task_id

            if task_id not in task_data:
                task_data[task_id] = {
                    'count': 0,
                    'reasons': [],
                    'last_postponed': None
                }

            task_data[task_id]['count'] += 1
            task_data[task_id]['reasons'].append(record.reason_type)

            # Track most recent postpone
            if record.postponed_at:
                if (task_data[task_id]['last_postponed'] is None or
                        record.postponed_at > task_data[task_id]['last_postponed']):
                    task_data[task_id]['last_postponed'] = record.postponed_at

        # Sort by count (descending) and take top 10
        sorted_tasks = sorted(task_data.items(), key=lambda x: x[1]['count'], reverse=True)[:10]

        self.most_postponed_table.setRowCount(len(sorted_tasks))

        for i, (task_id, data) in enumerate(sorted_tasks):
            task = self.task_dao.get_by_id(task_id)
            task_title = task.title if task else f"Task #{task_id}"

            # Task title
            title_item = QTableWidgetItem(task_title)
            self.most_postponed_table.setItem(i, 0, title_item)

            # Count
            count_item = QTableWidgetItem(str(data['count']))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.most_postponed_table.setItem(i, 1, count_item)

            # Most common reason
            reason_counts = Counter(data['reasons'])
            most_common_reason = reason_counts.most_common(1)[0][0]
            reason_item = QTableWidgetItem(self._format_reason(most_common_reason))
            self.most_postponed_table.setItem(i, 2, reason_item)

            # Last postponed
            if data['last_postponed']:
                last_postponed_str = self._format_datetime(data['last_postponed'])
            else:
                last_postponed_str = "Unknown"
            last_item = QTableWidgetItem(last_postponed_str)
            self.most_postponed_table.setItem(i, 3, last_item)

    def _populate_recent_activity(self, records: List[PostponeRecord]):
        """Populate recent activity table."""
        self.recent_activity_table.setRowCount(len(records))

        for i, record in enumerate(records):
            # Date/Time
            if record.postponed_at:
                datetime_str = self._format_datetime(record.postponed_at)
            else:
                datetime_str = "Unknown"
            datetime_item = QTableWidgetItem(datetime_str)
            self.recent_activity_table.setItem(i, 0, datetime_item)

            # Task
            task = self.task_dao.get_by_id(record.task_id)
            task_title = task.title if task else f"Task #{record.task_id}"
            task_item = QTableWidgetItem(task_title)
            self.recent_activity_table.setItem(i, 1, task_item)

            # Reason
            reason_item = QTableWidgetItem(self._format_reason(record.reason_type))
            self.recent_activity_table.setItem(i, 2, reason_item)

            # Action taken
            action_item = QTableWidgetItem(self._format_action(record.action_taken))
            self.recent_activity_table.setItem(i, 3, action_item)

            # Notes
            notes = record.reason_notes if record.reason_notes else "(no notes)"
            notes_item = QTableWidgetItem(notes)
            self.recent_activity_table.setItem(i, 4, notes_item)

    def _populate_action_summary(self, records: List[PostponeRecord]):
        """Populate action summary table."""
        action_counts = Counter(record.action_taken for record in records)
        total = len(records)

        self.action_table.setRowCount(len(action_counts))

        for i, (action, count) in enumerate(action_counts.most_common()):
            percentage = (count / total) * 100

            # Action
            action_item = QTableWidgetItem(self._format_action(action))
            self.action_table.setItem(i, 0, action_item)

            # Count
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.action_table.setItem(i, 1, count_item)

            # Percentage
            percentage_item = QTableWidgetItem(f"{percentage:.1f}%")
            percentage_item.setTextAlignment(Qt.AlignCenter)
            self.action_table.setItem(i, 2, percentage_item)

    def _format_reason(self, reason: PostponeReasonType) -> str:
        """Format reason type for display."""
        reason_labels = {
            PostponeReasonType.MULTIPLE_SUBTASKS: "Task Too Complex",
            PostponeReasonType.BLOCKER: "Blocker Encountered",
            PostponeReasonType.DEPENDENCY: "Waiting on Dependency",
            PostponeReasonType.NOT_READY: "Not Ready",
            PostponeReasonType.OTHER: "Other"
        }
        return reason_labels.get(reason, reason.value)

    def _format_action(self, action: ActionTaken) -> str:
        """Format action taken for display."""
        action_labels = {
            ActionTaken.NONE: "None",
            ActionTaken.DEFERRED: "Deferred",
            ActionTaken.DELEGATED: "Delegated",
            ActionTaken.CREATED_BLOCKER: "Created Blocker Task",
            ActionTaken.ADDED_DEPENDENCY: "Added Dependency",
            ActionTaken.BROKE_DOWN: "Broke Down Task"
        }
        return action_labels.get(action, action.value if hasattr(action, 'value') else str(action))

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for display."""
        now = datetime.now()
        diff = now - dt

        # If within last 24 hours, show relative time
        if diff < timedelta(days=1):
            if diff < timedelta(hours=1):
                minutes = int(diff.total_seconds() / 60)
                return f"{minutes} min ago"
            else:
                hours = int(diff.total_seconds() / 3600)
                return f"{hours} hr ago"
        # If within last week, show day name
        elif diff < timedelta(days=7):
            return dt.strftime("%A at %I:%M %p")
        # Otherwise show date
        else:
            return dt.strftime("%b %d, %Y")
