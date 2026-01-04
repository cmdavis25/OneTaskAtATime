"""Reset confirmation dialog with multi-step verification.

Provides strong confirmation for nuclear data reset operations.
"""
import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ..services.data_reset_service import DataResetService
from .geometry_mixin import GeometryMixin


class ResetConfirmationDialog(QDialog, GeometryMixin):
    """Dialog for confirming nuclear reset with multiple verification steps."""

    CONFIRMATION_TEXT = "RESET"

    def __init__(self, db_connection: sqlite3.Connection, parent=None):
        """Initialize reset confirmation dialog.

        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.reset_service = DataResetService(db_connection)

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=500, default_height=550)

        self._init_ui()
        self._update_button_state()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Reset All Data")
        self.setMinimumSize(500, 550)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Danger header
        header_label = QLabel("⚠️ DANGER: Reset All Data")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setStyleSheet("color: #c62828;")
        layout.addWidget(header_label)

        # Warning message
        warning_label = QLabel(
            "You are about to PERMANENTLY DELETE all data from this application.\n\n"
            "This action CANNOT BE UNDONE!"
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet(
            "background-color: #ffebee; color: #c62828; "
            "padding: 15px; border: 2px solid #c62828; border-radius: 4px; "
            "font-weight: bold; font-size: 11pt;"
        )
        layout.addWidget(warning_label)

        # Summary of what will be deleted
        summary_group = QGroupBox("What will be deleted:")
        summary_layout = QVBoxLayout()

        summary = self.reset_service.get_reset_summary()

        summary_text = (
            f"✓ {summary['tasks']} tasks\n"
            f"✓ {summary['dependencies']} task dependencies\n"
            f"✓ {summary['comparisons']} task comparisons\n"
            f"✓ {summary['history']} postpone history records\n"
            f"✓ {summary['notifications']} notifications"
        )

        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("font-family: monospace; font-size: 10pt;")
        summary_layout.addWidget(summary_label)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Options group
        options_group = QGroupBox("Additional Options:")
        options_layout = QVBoxLayout()

        self.delete_contexts_check = QCheckBox(
            f"Also delete contexts ({summary['contexts']})"
        )
        self.delete_contexts_check.setChecked(True)
        options_layout.addWidget(self.delete_contexts_check)

        self.delete_tags_check = QCheckBox(
            f"Also delete project tags ({summary['project_tags']})"
        )
        self.delete_tags_check.setChecked(True)
        options_layout.addWidget(self.delete_tags_check)

        self.reset_settings_check = QCheckBox(
            f"Reset settings to defaults ({summary['settings']} settings)"
        )
        self.reset_settings_check.setChecked(False)
        self.reset_settings_check.setToolTip(
            "Warning: This will reset all application settings including theme, "
            "notification preferences, and Elo parameters"
        )
        options_layout.addWidget(self.reset_settings_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Confirmation step 1: Type "RESET"
        confirm1_group = QGroupBox("Confirmation Step 1:")
        confirm1_layout = QVBoxLayout()

        confirm1_label = QLabel(f"Type exactly: {self.CONFIRMATION_TEXT}")
        confirm1_label.setStyleSheet("font-weight: bold;")
        confirm1_layout.addWidget(confirm1_label)

        self.confirmation_edit = QLineEdit()
        self.confirmation_edit.setPlaceholderText(f"Type '{self.CONFIRMATION_TEXT}' here...")
        self.confirmation_edit.textChanged.connect(self._update_button_state)
        confirm1_layout.addWidget(self.confirmation_edit)

        confirm1_group.setLayout(confirm1_layout)
        layout.addWidget(confirm1_group)

        # Confirmation step 2: Checkbox acknowledgment
        confirm2_group = QGroupBox("Confirmation Step 2:")
        confirm2_layout = QVBoxLayout()

        self.understand_check = QCheckBox(
            "☑ I understand this action is PERMANENT and CANNOT BE UNDONE"
        )
        self.understand_check.setStyleSheet("font-weight: bold;")
        self.understand_check.stateChanged.connect(self._update_button_state)
        confirm2_layout.addWidget(self.understand_check)

        confirm2_group.setLayout(confirm2_layout)
        layout.addWidget(confirm2_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_btn = QPushButton("Reset All Data")
        self.reset_btn.setObjectName("dangerButton")
        self.reset_btn.clicked.connect(self._confirm_and_reset)
        self.reset_btn.setEnabled(False)
        button_layout.addWidget(self.reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _update_button_state(self):
        """Update reset button enabled state based on confirmations."""
        text_correct = self.confirmation_edit.text() == self.CONFIRMATION_TEXT
        checkbox_checked = self.understand_check.isChecked()

        self.reset_btn.setEnabled(text_correct and checkbox_checked)

    def _confirm_and_reset(self):
        """Show final confirmation and perform reset."""
        # Final warning with system dialog
        reply = QMessageBox.warning(
            self,
            "FINAL WARNING",
            "This is your LAST CHANCE to cancel!\n\n"
            "Are you ABSOLUTELY SURE you want to delete all data?\n\n"
            "This action is PERMANENT and IRREVERSIBLE!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Perform the reset
        result = self.reset_service.reset_all_data(
            include_contexts=self.delete_contexts_check.isChecked(),
            include_tags=self.delete_tags_check.isChecked(),
            reset_settings=self.reset_settings_check.isChecked()
        )

        if result['success']:
            deleted = result['deleted']
            total_deleted = sum(deleted.values())

            QMessageBox.information(
                self,
                "Reset Complete",
                f"All data has been deleted successfully.\n\n"
                f"Total items deleted: {total_deleted}\n\n"
                f"Details:\n"
                f"  • Tasks: {deleted['tasks']}\n"
                f"  • Dependencies: {deleted['dependencies']}\n"
                f"  • Comparisons: {deleted['comparisons']}\n"
                f"  • History: {deleted['history']}\n"
                f"  • Notifications: {deleted['notifications']}\n"
                f"  • Contexts: {deleted['contexts']}\n"
                f"  • Project Tags: {deleted['project_tags']}\n"
                f"  • Settings: {deleted['settings']}"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Reset Failed",
                f"Failed to reset data:\n\n{result.get('error', 'Unknown error')}"
            )
