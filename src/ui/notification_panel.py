"""
Notification Panel Widget for OneTaskAtATime application.

Displays in-app notifications in a collapsible panel.
Shows unread count badge and allows users to view, mark read, and dismiss notifications.
"""

import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor
from typing import List

from ..models.notification import Notification, NotificationType
from ..services.notification_manager import NotificationManager


class NotificationItem(QFrame):
    """
    Widget representing a single notification in the panel.
    """

    # Signals
    mark_read_clicked = pyqtSignal(int)  # notification_id
    dismiss_clicked = pyqtSignal(int)  # notification_id
    action_clicked = pyqtSignal(Notification)  # Full notification object

    def __init__(self, notification: Notification, parent=None):
        """
        Initialize notification item widget.

        Args:
            notification: Notification object to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.notification = notification
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("""
            NotificationItem {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                margin: 4px;
            }
            NotificationItem:hover {
                background-color: #e9ecef;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(layout)

        # Header row: Icon + Title + Time + Dismiss
        header_layout = QHBoxLayout()

        # Icon
        icon_label = QLabel(self.notification.get_icon())
        icon_font = QFont()
        icon_font.setPointSize(14)
        icon_label.setFont(icon_font)
        header_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(self.notification.title)
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setWordWrap(False)
        header_layout.addWidget(title_label, 1)

        # Time ago
        time_label = QLabel(self.notification.get_time_ago())
        time_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        header_layout.addWidget(time_label)

        # Dismiss button
        dismiss_btn = QPushButton("×")
        dismiss_btn.setFixedSize(20, 20)
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                font-weight: bold;
                color: #6c757d;
            }
            QPushButton:hover {
                color: #dc3545;
            }
        """)
        dismiss_btn.setCursor(QCursor(Qt.PointingHandCursor))
        dismiss_btn.clicked.connect(lambda: self.dismiss_clicked.emit(self.notification.id))
        header_layout.addWidget(dismiss_btn)

        layout.addLayout(header_layout)

        # Message
        message_label = QLabel(self.notification.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #495057; font-size: 12px;")
        layout.addWidget(message_label)

        # Action buttons row
        if self.notification.action_type or not self.notification.is_read:
            action_layout = QHBoxLayout()
            action_layout.addStretch()

            # Action button (if available)
            if self.notification.action_type:
                action_btn = QPushButton(self._get_action_label())
                action_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        padding: 4px 12px;
                        border-radius: 3px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
                action_btn.setCursor(QCursor(Qt.PointingHandCursor))
                action_btn.clicked.connect(lambda: self.action_clicked.emit(self.notification))
                action_layout.addWidget(action_btn)

            # Mark as read button (if unread)
            if not self.notification.is_read:
                mark_read_btn = QPushButton("Mark Read")
                mark_read_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #6c757d;
                        border: 1px solid #6c757d;
                        padding: 4px 12px;
                        border-radius: 3px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #e9ecef;
                    }
                """)
                mark_read_btn.setCursor(QCursor(Qt.PointingHandCursor))
                mark_read_btn.clicked.connect(lambda: self.mark_read_clicked.emit(self.notification.id))
                action_layout.addWidget(mark_read_btn)

            layout.addLayout(action_layout)

    def _get_action_label(self) -> str:
        """Get display label for action button based on action type."""
        action_labels = {
            'open_focus': 'View Tasks',
            'open_review_delegated': 'Review Tasks',
            'open_review_someday': 'Review Someday',
            'open_postpone_analytics': 'View Analytics'
        }
        return action_labels.get(self.notification.action_type, 'View')


class NotificationPanel(QWidget):
    """
    Collapsible notification panel widget.

    Displays unread notification count badge and expandable notification list.
    """

    # Signals
    action_requested = pyqtSignal(Notification)  # When user clicks action button

    def __init__(self, db_connection: sqlite3.Connection, notification_manager: NotificationManager, parent=None):
        """
        Initialize notification panel.

        Args:
            db_connection: Database connection
            notification_manager: NotificationManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.notification_manager = notification_manager
        self.is_expanded = False

        self._init_ui()
        self._connect_signals()
        self._refresh_badge()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Header bar (always visible)
        self.header_widget = QFrame()
        self.header_widget.setFrameShape(QFrame.StyledPanel)
        self.header_widget.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 8, 8, 8)
        self.header_widget.setLayout(header_layout)

        # Bell icon and title
        title_label = QLabel("🔔 Notifications")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        # Unread count badge
        self.badge_label = QLabel("0")
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.badge_label.setFixedSize(24, 24)
        self.badge_label.setStyleSheet("""
            QLabel {
                background-color: #dc3545;
                color: white;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(self.badge_label)

        header_layout.addStretch()

        # Expand/collapse button
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(30, 30)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-radius: 4px;
            }
        """)
        self.toggle_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.toggle_btn.clicked.connect(self._toggle_panel)
        header_layout.addWidget(self.toggle_btn)

        layout.addWidget(self.header_widget)

        # Notification list (collapsible)
        self.content_widget = QFrame()
        self.content_widget.setVisible(False)
        self.content_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dee2e6;
                border-top: none;
                border-radius: 0 0 4px 4px;
            }
        """)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_widget.setLayout(content_layout)

        # Scroll area for notifications
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(400)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.notifications_container = QWidget()
        self.notifications_layout = QVBoxLayout()
        self.notifications_layout.setSpacing(8)
        self.notifications_layout.setContentsMargins(0, 0, 0, 0)
        self.notifications_container.setLayout(self.notifications_layout)

        scroll_area.setWidget(self.notifications_container)
        content_layout.addWidget(scroll_area)

        # Footer buttons
        footer_layout = QHBoxLayout()

        mark_all_btn = QPushButton("Mark All Read")
        mark_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        mark_all_btn.setCursor(QCursor(Qt.PointingHandCursor))
        mark_all_btn.clicked.connect(self._mark_all_read)
        footer_layout.addWidget(mark_all_btn)

        footer_layout.addStretch()

        content_layout.addLayout(footer_layout)

        layout.addWidget(self.content_widget)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

    def _connect_signals(self):
        """Connect notification manager signals."""
        self.notification_manager.new_notification.connect(self._on_new_notification)
        self.notification_manager.notification_updated.connect(self._on_notification_updated)
        self.notification_manager.notification_dismissed.connect(self._on_notification_dismissed)

    def _toggle_panel(self):
        """Toggle panel expand/collapse."""
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self.toggle_btn.setText("▲" if self.is_expanded else "▼")

        if self.is_expanded:
            self._refresh_notifications()

    def _refresh_badge(self):
        """Refresh unread count badge."""
        unread_count = self.notification_manager.get_unread_count()
        self.badge_label.setText(str(unread_count))
        self.badge_label.setVisible(unread_count > 0)

    def _refresh_notifications(self):
        """Refresh notification list display."""
        # Clear existing items
        while self.notifications_layout.count():
            item = self.notifications_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get all unread and recent notifications
        notifications = self.notification_manager.get_all_notifications(include_dismissed=False)

        if not notifications:
            empty_label = QLabel("No notifications")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #6c757d; padding: 20px;")
            self.notifications_layout.addWidget(empty_label)
        else:
            for notification in notifications:
                item = NotificationItem(notification)
                item.mark_read_clicked.connect(self._on_mark_read)
                item.dismiss_clicked.connect(self._on_dismiss)
                item.action_clicked.connect(self._on_action_clicked)
                self.notifications_layout.addWidget(item)

        self.notifications_layout.addStretch()

    def _mark_all_read(self):
        """Mark all notifications as read."""
        self.notification_manager.mark_all_read()
        self._refresh_badge()
        self._refresh_notifications()

    def _on_mark_read(self, notification_id: int):
        """Handle mark read signal."""
        self.notification_manager.mark_as_read(notification_id)
        self._refresh_badge()
        self._refresh_notifications()

    def _on_dismiss(self, notification_id: int):
        """Handle dismiss signal."""
        self.notification_manager.dismiss_notification(notification_id)
        self._refresh_badge()
        self._refresh_notifications()

    def _on_action_clicked(self, notification: Notification):
        """Handle action button click."""
        # Mark as read when action is clicked
        self.notification_manager.mark_as_read(notification.id)

        # Emit signal for parent to handle action
        self.action_requested.emit(notification)

        # Collapse panel to give visual feedback
        if self.is_expanded:
            self._toggle_panel()

        # Refresh display
        self._refresh_badge()
        if self.is_expanded:
            self._refresh_notifications()

    def _on_new_notification(self, notification: Notification):
        """Handle new notification signal."""
        self._refresh_badge()
        if self.is_expanded:
            self._refresh_notifications()

    def _on_notification_updated(self, notification: Notification):
        """Handle notification updated signal."""
        self._refresh_badge()
        if self.is_expanded:
            self._refresh_notifications()

    def _on_notification_dismissed(self, notification_id: int):
        """Handle notification dismissed signal."""
        self._refresh_badge()
        if self.is_expanded:
            self._refresh_notifications()
