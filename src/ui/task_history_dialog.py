"""
Task History Dialog for OneTaskAtATime.

Displays a comprehensive timeline view of all events in a task's history.
"""

from datetime import datetime, timedelta
from typing import Optional
import json
import csv
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QHeaderView,
    QTextEdit, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from src.models.task import Task
from src.models.task_history_event import TaskHistoryEvent
from src.models.enums import TaskEventType
from src.services.task_history_service import TaskHistoryService
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class TaskHistoryDialog(QDialog, GeometryMixin):
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

        # Store db_connection from parent for MessageBox usage
        self.db_connection = None
        if parent and hasattr(parent, 'db_connection'):
            self.db_connection = parent.db_connection

        # Initialize geometry persistence (get db_connection from parent if available)
        if self.db_connection:
            self._init_geometry_persistence(self.db_connection, default_width=900, default_height=600)
        else:
            # Set flag to prevent GeometryMixin.showEvent from failing
            self._geometry_restored = True

        self.setWindowTitle(f"Task History: {task.title}")
        self.setMinimumSize(700, 500)
        self.setModal(False)

        # Enable WhatsThis help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # Set WhatsThis text for the dialog
        self.setWhatsThis(
            "This dialog shows a complete audit log of all changes to this task. "
            "View when the task was created, modified, completed, or changed in any way. "
            "Click the ? button for help on specific features."
        )

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
        self.filter_combo.setWhatsThis(
            "Filter the history timeline by event type. Select a specific event type to see only those events, or choose 'All Events' to see the complete history."
        )
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addStretch()

        # Export button
        self.export_button = QPushButton("Export...")
        self.export_button.clicked.connect(self._export_history)
        self.export_button.setWhatsThis(
            "Export the complete task history to a file. Choose from CSV, JSON, or text format for archiving or analysis."
        )
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
        self.timeline_tree.itemDoubleClicked.connect(self._show_event_details)
        self.timeline_tree.setWhatsThis(
            "Complete audit log of all changes to this task. Double-click an event to see detailed information including old/new values and context data."
        )
        layout.addWidget(self.timeline_tree)

        # Details button
        details_button_layout = QHBoxLayout()
        details_button_layout.addStretch()
        self.details_button = QPushButton("View Details")
        self.details_button.clicked.connect(self._show_selected_event_details)
        self.details_button.setEnabled(False)
        details_button_layout.addWidget(self.details_button)
        layout.addLayout(details_button_layout)

        # Connect selection changed signal
        self.timeline_tree.itemSelectionChanged.connect(self._on_selection_changed)

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
            MessageBox.warning(
                self,
                self.db_connection.get_connection() if self.db_connection and hasattr(self.db_connection, 'get_connection') else self.db_connection,
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

    def _on_selection_changed(self):
        """Enable/disable details button based on selection."""
        selected_items = self.timeline_tree.selectedItems()
        # Only enable if a single event is selected (not a date header)
        if selected_items and len(selected_items) == 1:
            item = selected_items[0]
            # Date headers have empty time column
            is_event = item.text(0) and item.text(0) != "" and ":" in item.text(0)
            self.details_button.setEnabled(is_event)
        else:
            self.details_button.setEnabled(False)

    def _show_selected_event_details(self):
        """Show details for the currently selected event."""
        selected_items = self.timeline_tree.selectedItems()
        if not selected_items:
            return
        self._show_event_details(selected_items[0], 0)

    def _show_event_details(self, item: QTreeWidgetItem, column: int):
        """
        Show detailed information about an event in a dialog.

        Args:
            item: The tree widget item that was clicked
            column: The column that was clicked (unused)
        """
        # Skip if this is a date header
        if not item.text(0) or ":" not in item.text(0):
            return

        # Find the corresponding event
        event = self._get_event_for_item(item)
        if not event:
            return

        # Create details dialog
        details_dialog = EventDetailsDialog(event, self.history_service, self)
        details_dialog.exec_()

    def _get_event_for_item(self, item: QTreeWidgetItem) -> Optional[TaskHistoryEvent]:
        """
        Find the event corresponding to a tree widget item.

        Args:
            item: The tree widget item

        Returns:
            The corresponding TaskHistoryEvent, or None if not found
        """
        # Get the full timestamp by combining date and time
        time_str = item.text(0)
        description = item.text(1)

        # Find the date header above this item
        index = self.timeline_tree.indexOfTopLevelItem(item)
        date_str = None
        for i in range(index - 1, -1, -1):
            potential_header = self.timeline_tree.topLevelItem(i)
            if not potential_header.text(0) or ":" not in potential_header.text(0):
                date_str = potential_header.text(0)
                break

        # Match event by timestamp and description
        for event in self.all_events:
            event_time = event.event_timestamp.strftime("%I:%M %p")
            if event_time == time_str:
                event_desc = self.history_service.get_formatted_summary(event)
                # Remove icon prefix for comparison
                clean_desc = description.split(" ", 1)[1] if " " in description else description
                if event_desc == clean_desc:
                    return event

        return None

    def _export_history(self):
        """Export the complete task history to a file."""
        if not self.all_events:
            MessageBox.information(
                self,
                self.db_connection.get_connection() if self.db_connection and hasattr(self.db_connection, 'get_connection') else self.db_connection,
                "No Data",
                "There are no history events to export."
            )
            return

        # Ask user to select export format and location
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Task History",
            f"task_history_{self.task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;JSON Files (*.json);;Text Files (*.txt)"
        )

        if not file_path:
            return

        try:
            if selected_filter == "CSV Files (*.csv)":
                self._export_as_csv(file_path)
            elif selected_filter == "JSON Files (*.json)":
                self._export_as_json(file_path)
            else:
                self._export_as_text(file_path)

            MessageBox.information(
                self,
                self.db_connection.get_connection() if self.db_connection and hasattr(self.db_connection, 'get_connection') else self.db_connection,
                "Export Successful",
                f"Task history exported successfully to:\n{file_path}"
            )
        except Exception as e:
            MessageBox.critical(
                self,
                self.db_connection.get_connection() if self.db_connection and hasattr(self.db_connection, 'get_connection') else self.db_connection,
                "Export Failed",
                f"Failed to export task history:\n{str(e)}"
            )

    def _export_as_csv(self, file_path: str):
        """
        Export history as CSV file.

        Args:
            file_path: Path to save the CSV file
        """
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow([
                'Task ID', 'Task Title', 'Timestamp', 'Event Type',
                'Description', 'Changed By', 'Old Value', 'New Value', 'Context Data'
            ])

            # Write events
            for event in reversed(self.all_events):  # Chronological order (oldest first)
                writer.writerow([
                    self.task.id,
                    self.task.title,
                    event.event_timestamp.isoformat(),
                    event.event_type.value,
                    self.history_service.get_formatted_summary(event),
                    event.changed_by,
                    event.old_value or '',
                    event.new_value or '',
                    event.context_data or ''
                ])

    def _export_as_json(self, file_path: str):
        """
        Export history as JSON file.

        Args:
            file_path: Path to save the JSON file
        """
        export_data = {
            'task': {
                'id': self.task.id,
                'title': self.task.title,
                'current_state': self.task.state.value
            },
            'export_timestamp': datetime.now().isoformat(),
            'events': []
        }

        for event in reversed(self.all_events):  # Chronological order (oldest first)
            event_data = {
                'timestamp': event.event_timestamp.isoformat(),
                'event_type': event.event_type.value,
                'description': self.history_service.get_formatted_summary(event),
                'changed_by': event.changed_by,
                'old_value': event.old_value,
                'new_value': event.new_value,
                'context_data': json.loads(event.context_data) if event.context_data else None
            }
            export_data['events'].append(event_data)

        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)

    def _export_as_text(self, file_path: str):
        """
        Export history as human-readable text file.

        Args:
            file_path: Path to save the text file
        """
        with open(file_path, 'w', encoding='utf-8') as txtfile:
            txtfile.write(f"Task History Report\n")
            txtfile.write(f"{'=' * 80}\n\n")
            txtfile.write(f"Task ID: {self.task.id}\n")
            txtfile.write(f"Task Title: {self.task.title}\n")
            txtfile.write(f"Current State: {self.task.state.value}\n")
            txtfile.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n")
            txtfile.write(f"\n{'=' * 80}\n\n")

            # Group events by date
            grouped_events = self._group_events_by_date(list(reversed(self.all_events)))

            for date_label, event_list in reversed(grouped_events):
                txtfile.write(f"{date_label}\n")
                txtfile.write(f"{'-' * 40}\n")

                for event in event_list:
                    time_str = event.event_timestamp.strftime("%I:%M %p")
                    description = self.history_service.get_formatted_summary(event)
                    txtfile.write(f"  {time_str} - {description} (by {event.changed_by})\n")

                    # Add details if available
                    if event.old_value or event.new_value:
                        txtfile.write(f"    Old Value: {event.old_value or 'N/A'}\n")
                        txtfile.write(f"    New Value: {event.new_value or 'N/A'}\n")
                    if event.context_data:
                        try:
                            context = json.loads(event.context_data)
                            txtfile.write(f"    Context: {json.dumps(context, indent=6)}\n")
                        except json.JSONDecodeError:
                            txtfile.write(f"    Context: {event.context_data}\n")
                    txtfile.write("\n")

                txtfile.write("\n")


class EventDetailsDialog(QDialog, GeometryMixin):
    """
    Dialog for showing detailed information about a history event.

    Displays the old state, new state, and all context data for an event.
    """

    def __init__(self, event: TaskHistoryEvent, history_service: TaskHistoryService, parent=None):
        """
        Initialize the Event Details Dialog.

        Args:
            event: The history event to display
            history_service: Service for formatting event data
            parent: Parent widget
        """
        super().__init__(parent)
        self.event = event
        self.history_service = history_service

        # Store db_connection from parent for MessageBox usage
        self.db_connection = None
        if parent and hasattr(parent, 'db_connection'):
            self.db_connection = parent.db_connection

        # Initialize geometry persistence (get db_connection from parent if available)
        if self.db_connection:
            self._init_geometry_persistence(self.db_connection, default_width=600, default_height=400)
        else:
            # Set flag to prevent GeometryMixin.showEvent from failing
            self._geometry_restored = True

        self.setWindowTitle("Event Details")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Header with event type and timestamp
        header_label = QLabel(f"<h2>{self.event.event_type.value.replace('_', ' ').title()}</h2>")
        layout.addWidget(header_label)

        timestamp_label = QLabel(
            f"<b>Timestamp:</b> {self.event.event_timestamp.strftime('%Y-%m-%d %I:%M:%S %p')}"
        )
        layout.addWidget(timestamp_label)

        changed_by_label = QLabel(f"<b>Changed By:</b> {self.event.changed_by.capitalize()}")
        layout.addWidget(changed_by_label)

        # Description
        description_label = QLabel(f"<b>Description:</b>")
        layout.addWidget(description_label)

        description_text = QLabel(self.history_service.get_formatted_summary(self.event))
        description_text.setWordWrap(True)
        description_text.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        layout.addWidget(description_text)

        # Details text area
        details_label = QLabel("<b>Details:</b>")
        layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.details_text)

        # Populate details
        self._populate_details()

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _populate_details(self):
        """Populate the details text area with event data."""
        details = []

        # Add old value if present
        if self.event.old_value:
            details.append("=== OLD VALUE ===")
            details.append(self._format_value(self.event.old_value))
            details.append("")

        # Add new value if present
        if self.event.new_value:
            details.append("=== NEW VALUE ===")
            details.append(self._format_value(self.event.new_value))
            details.append("")

        # Add context data if present
        if self.event.context_data:
            details.append("=== CONTEXT DATA ===")
            try:
                context = json.loads(self.event.context_data)
                details.append(json.dumps(context, indent=2))
            except json.JSONDecodeError:
                details.append(self.event.context_data)
            details.append("")

        # If no details available
        if not details:
            details.append("No additional details available for this event.")

        self.details_text.setPlainText("\n".join(details))

    def _format_value(self, value: str) -> str:
        """
        Format a value for display.

        Args:
            value: The value to format

        Returns:
            Formatted string
        """
        # Try to parse as JSON for pretty printing
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, indent=2)
        except (json.JSONDecodeError, TypeError):
            # Return as-is if not JSON
            return value
