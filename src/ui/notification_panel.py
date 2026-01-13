"""
Notification Panel Widget for OneTaskAtATime application.

Displays a compact notification button/badge that opens a popup dialog overlay.
"""

import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QDialog, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor
from typing import List

from ..models.notification import Notification, NotificationType
from ..services.notification_manager import NotificationManager
from .geometry_mixin import GeometryMixin


class NotificationItem(QFrame):
    """Widget representing a single notification."""

    # Signals
    mark_read_clicked = pyqtSignal(int)  # notification_id
    mark_unread_clicked = pyqtSignal(int)  # notification_id
    dismiss_clicked = pyqtSignal(int)  # notification_id
    action_clicked = pyqtSignal(Notification)  # Full notification object

    def __init__(self, notification: Notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        # Use object names to let theme handle styling
        if self.notification.is_read:
            self.setObjectName("readNotificationItem")
        else:
            self.setObjectName("unreadNotificationItem")

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(layout)

        # Header row
        header_layout = QHBoxLayout()

        # Read/Unread envelope icon
        envelope_icon = "📧" if self.notification.is_read else "📩"
        envelope_label = QLabel(envelope_icon)
        envelope_font = QFont()
        envelope_font.setPointSize(14)
        envelope_label.setFont(envelope_font)
        envelope_label.setToolTip("Read" if self.notification.is_read else "Unread")
        header_layout.addWidget(envelope_label)

        # Notification type icon
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
        time_label.setStyleSheet("font-size: 11px;")
        time_label.setObjectName("notificationTime")
        header_layout.addWidget(time_label)

        # Dismiss button
        dismiss_btn = QPushButton("×")
        dismiss_btn.setFixedSize(32, 32)  # Increased from 20x20 to 32x32 for better clickability
        dismiss_btn.setObjectName("dismissButton")
        dismiss_btn.setCursor(QCursor(Qt.PointingHandCursor))
        dismiss_btn.clicked.connect(lambda: self.dismiss_clicked.emit(self.notification.id))
        header_layout.addWidget(dismiss_btn)

        layout.addLayout(header_layout)

        # Message
        message_label = QLabel(self.notification.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 12px;")
        message_label.setObjectName("notificationMessage")
        layout.addWidget(message_label)

        # Action buttons row (always show)
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        # Action button (if available)
        if self.notification.action_type:
            action_btn = QPushButton(self._get_action_label())
            action_btn.setObjectName("primaryButton")
            action_btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 12px;
                    font-size: 11px;
                }
            """)
            action_btn.setCursor(QCursor(Qt.PointingHandCursor))
            action_btn.clicked.connect(lambda: self.action_clicked.emit(self.notification))
            action_layout.addWidget(action_btn)

        # Mark as read/unread toggle button
        mark_btn = QPushButton("Mark as Read" if not self.notification.is_read else "Mark as Unread")
        mark_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        mark_btn.setCursor(QCursor(Qt.PointingHandCursor))
        if not self.notification.is_read:
            mark_btn.clicked.connect(lambda: self.mark_read_clicked.emit(self.notification.id))
        else:
            mark_btn.clicked.connect(lambda: self.mark_unread_clicked.emit(self.notification.id))
        action_layout.addWidget(mark_btn)

        layout.addLayout(action_layout)

    def _get_action_label(self) -> str:
        """Get display label for action button."""
        action_labels = {
            'open_focus': 'View Tasks',
            'open_review_delegated': 'Review Tasks',
            'open_review_someday': 'Review Someday',
            'open_postpone_analytics': 'View Analytics'
        }
        return action_labels.get(self.notification.action_type, 'View')


class NotificationDialog(QDialog, GeometryMixin):
    """Popup dialog displaying notifications."""

    action_requested = pyqtSignal(Notification)

    def __init__(self, notification_manager: NotificationManager, db_connection: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.notification_manager = notification_manager
        self._init_geometry_persistence(db_connection, default_width=500, default_height=600)
        self._init_ui()
        self._refresh_notifications()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Notifications")
        self.setModal(False)  # Allow interaction with main window
        self.setMinimumSize(500, 600)
        self.setMaximumSize(500, 800)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Notifications")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Scroll area for notifications
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.notifications_container = QWidget()
        self.notifications_layout = QVBoxLayout()
        self.notifications_layout.setSpacing(8)
        self.notifications_layout.setContentsMargins(0, 0, 0, 0)
        self.notifications_container.setLayout(self.notifications_layout)

        scroll_area.setWidget(self.notifications_container)
        layout.addWidget(scroll_area)

        # Footer buttons
        footer_layout = QHBoxLayout()

        mark_all_btn = QPushButton("Mark All Read")
        mark_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
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

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
            }
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)

        layout.addLayout(footer_layout)

    def _refresh_notifications(self):
        """Refresh notification list display."""
        # Clear existing items more thoroughly
        for i in reversed(range(self.notifications_layout.count())):
            item = self.notifications_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
                else:
                    self.notifications_layout.removeItem(item)

        # Get all unread and recent notifications (fresh from database)
        notifications = self.notification_manager.get_all_notifications(include_dismissed=False)

        if not notifications:
            empty_label = QLabel("No notifications")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #6c757d; padding: 40px;")
            self.notifications_layout.addWidget(empty_label)
        else:
            for notification in notifications:
                item = NotificationItem(notification)
                item.mark_read_clicked.connect(self._on_mark_read)
                item.mark_unread_clicked.connect(self._on_mark_unread)
                item.dismiss_clicked.connect(self._on_dismiss)
                item.action_clicked.connect(self._on_action_clicked)
                self.notifications_layout.addWidget(item)

        self.notifications_layout.addStretch()

    def _mark_all_read(self):
        """Mark all notifications as read."""
        self.notification_manager.mark_all_read()
        self._refresh_notifications()

    def _on_mark_read(self, notification_id: int):
        """Handle mark read signal."""
        self.notification_manager.mark_as_read(notification_id)
        self._refresh_notifications()

    def _on_mark_unread(self, notification_id: int):
        """Handle mark unread signal."""
        self.notification_manager.mark_as_unread(notification_id)
        self._refresh_notifications()

    def _on_dismiss(self, notification_id: int):
        """Handle dismiss signal."""
        self.notification_manager.dismiss_notification(notification_id)
        self._refresh_notifications()

    def _on_action_clicked(self, notification: Notification):
        """Handle action button click."""
        # Mark as read
        self.notification_manager.mark_as_read(notification.id)

        # Emit signal for parent to handle action
        self.action_requested.emit(notification)

        # Close dialog
        self.accept()


class NotificationPanel(QWidget):
    """
    Compact notification button that opens a popup dialog.
    """

    action_requested = pyqtSignal(Notification)

    def __init__(self, db_connection: sqlite3.Connection, notification_manager: NotificationManager, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.notification_manager = notification_manager
        self._init_ui()
        self._connect_signals()
        self._refresh_badge()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for better alignment in header
        self.setLayout(layout)

        # Notification button
        self.notification_btn = QPushButton("🔔 Notifications")
        # Remove hardcoded styling - let theme handle it
        self.notification_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-weight: bold;
            }
        """)
        self.notification_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.notification_btn.clicked.connect(self._show_notifications)
        layout.addWidget(self.notification_btn)

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
        self.badge_label.setVisible(False)
        layout.addWidget(self.badge_label)

        # Set size policy to not expand
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMaximumHeight(50)

    def _connect_signals(self):
        """Connect notification manager signals."""
        self.notification_manager.new_notification.connect(self._on_new_notification)
        self.notification_manager.notification_updated.connect(self._refresh_badge)
        self.notification_manager.notification_dismissed.connect(self._refresh_badge)

    def _show_notifications(self):
        """Show notification dialog."""
        dialog = NotificationDialog(self.notification_manager, self.db_connection, self)
        dialog.action_requested.connect(self._on_action_requested)
        dialog.exec_()
        self._refresh_badge()

    def _refresh_badge(self):
        """Refresh unread count badge."""
        unread_count = self.notification_manager.get_unread_count()
        self.badge_label.setText(str(unread_count))
        self.badge_label.setVisible(unread_count > 0)

    def _on_new_notification(self, notification: Notification):
        """Handle new notification signal."""
        self._refresh_badge()

    def _on_action_requested(self, notification: Notification):
        """Forward action request to parent."""
        self.action_requested.emit(notification)
