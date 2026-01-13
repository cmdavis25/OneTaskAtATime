"""Export dialog for backing up application data.

Provides UI for exporting data to JSON or creating database backups.
"""
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QGroupBox, QFileDialog, QProgressBar,
    QCheckBox, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from ..services.export_service import ExportService
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class ExportWorker(QThread):
    """Worker thread for export operations."""

    progress = pyqtSignal(str, int)  # message, percent
    finished = pyqtSignal(dict)  # result dictionary
    error = pyqtSignal(str)  # error message

    def __init__(self, export_service: ExportService, export_type: str,
                 filepath: str, include_settings: bool):
        """Initialize export worker.

        Args:
            export_service: ExportService instance
            export_type: 'json' or 'database'
            filepath: Destination file path
            include_settings: Whether to include settings (JSON only)
        """
        super().__init__()
        self.export_service = export_service
        self.export_type = export_type
        self.filepath = filepath
        self.include_settings = include_settings

    def run(self):
        """Run the export operation."""
        try:
            if self.export_type == 'json':
                result = self.export_service.export_to_json(
                    self.filepath,
                    self.include_settings,
                    self.progress.emit
                )
            else:  # database
                self.progress.emit("Creating database backup...", 50)
                result = self.export_service.export_database_backup(self.filepath)
                self.progress.emit("Backup complete!", 100)

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class ExportDialog(QDialog, GeometryMixin):
    """Dialog for exporting application data."""

    def __init__(self, db_connection: sqlite3.Connection, parent=None):
        """Initialize export dialog.

        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.export_service = ExportService(db_connection)
        self.export_worker = None

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=500, default_height=400)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Export Data")
        self.setMinimumSize(500, 400)

        # Enable WhatsThis help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # Set WhatsThis text for the dialog
        self.setWhatsThis(
            "This dialog allows you to export your data for backup purposes. "
            "Choose JSON format for cross-platform backups or database format for complete system backups. "
            "Click the ? button for help."
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Export Data")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Description
        desc_label = QLabel(
            "Export your data to JSON format for backup or migration, "
            "or create a direct database file backup."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Export type group
        export_type_group = QGroupBox("Export Type")
        export_type_layout = QVBoxLayout()

        self.json_radio = QRadioButton("JSON Export (recommended)")
        self.json_radio.setChecked(True)
        self.json_radio.toggled.connect(self._on_export_type_changed)
        self.json_radio.setWhatsThis(
            "Export all data in human-readable JSON format. This is the recommended option for cross-platform backups and data migration."
        )
        export_type_layout.addWidget(self.json_radio)

        json_desc = QLabel("Export all data in human-readable JSON format")
        json_desc.setStyleSheet("color: #666; margin-left: 20px;")
        export_type_layout.addWidget(json_desc)

        self.database_radio = QRadioButton("SQLite Database Backup")
        self.database_radio.toggled.connect(self._on_export_type_changed)
        self.database_radio.setWhatsThis(
            "Create a direct copy of the SQLite database file. This is a complete system backup including all data and settings."
        )
        export_type_layout.addWidget(self.database_radio)

        db_desc = QLabel("Create a direct copy of the database file")
        db_desc.setStyleSheet("color: #666; margin-left: 20px;")
        export_type_layout.addWidget(db_desc)

        export_type_group.setLayout(export_type_layout)
        layout.addWidget(export_type_group)

        # Options group (only for JSON)
        self.options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout()

        self.include_settings_check = QCheckBox("Include settings")
        self.include_settings_check.setChecked(True)
        self.include_settings_check.setToolTip(
            "Include application settings in the export"
        )
        self.include_settings_check.setWhatsThis(
            "Include application settings in the JSON export. This includes preferences like window positions and display options."
        )
        options_layout.addWidget(self.include_settings_check)

        self.options_group.setLayout(options_layout)
        layout.addWidget(self.options_group)

        # File path group
        file_group = QGroupBox("Destination")
        file_layout = QVBoxLayout()

        path_layout = QHBoxLayout()
        self.filepath_edit = QLineEdit()
        self.filepath_edit.setPlaceholderText("Select destination file...")
        self.filepath_edit.setReadOnly(True)
        path_layout.addWidget(self.filepath_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        browse_btn.setWhatsThis(
            "Choose a custom location and filename for the export file. By default, a timestamped filename is provided."
        )
        path_layout.addWidget(browse_btn)

        file_layout.addLayout(path_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.export_btn = QPushButton("Export")
        self.export_btn.setObjectName("primaryButton")
        self.export_btn.clicked.connect(self._start_export)
        self.export_btn.setEnabled(False)
        self.export_btn.setWhatsThis(
            "Start the export operation. Your data will be saved to the specified file location."
        )
        button_layout.addWidget(self.export_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        # Set default file path
        self._update_default_filepath()

    def _on_export_type_changed(self):
        """Handle export type radio button change."""
        is_json = self.json_radio.isChecked()
        self.options_group.setVisible(is_json)
        self._update_default_filepath()

    def _update_default_filepath(self):
        """Update the default file path based on export type."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.json_radio.isChecked():
            default_filename = f"onetask_backup_{timestamp}.json"
        else:
            default_filename = f"onetask_backup_{timestamp}.db"

        self.filepath_edit.setText(default_filename)
        self.export_btn.setEnabled(True)

    def _browse_file(self):
        """Open file dialog to select destination."""
        if self.json_radio.isChecked():
            filter_str = "JSON Files (*.json)"
            default_ext = ".json"
        else:
            filter_str = "SQLite Database (*.db)"
            default_ext = ".db"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Select Export Destination",
            self.filepath_edit.text(),
            filter_str
        )

        if filepath:
            # Ensure correct extension
            if not filepath.endswith(default_ext):
                filepath += default_ext
            self.filepath_edit.setText(filepath)
            self.export_btn.setEnabled(True)

    def _start_export(self):
        """Start the export operation."""
        filepath = self.filepath_edit.text()

        if not filepath:
            MessageBox.warning(
                self,
                self.db_connection,
                "No File Selected",
                "Please select a destination file for the export."
            )
            return

        # Disable controls during export
        self.export_btn.setEnabled(False)
        self.json_radio.setEnabled(False)
        self.database_radio.setEnabled(False)
        self.include_settings_check.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Create and start worker thread
        export_type = 'json' if self.json_radio.isChecked() else 'database'
        include_settings = self.include_settings_check.isChecked()

        self.export_worker = ExportWorker(
            self.export_service,
            export_type,
            filepath,
            include_settings
        )
        self.export_worker.progress.connect(self._on_progress)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.error.connect(self._on_export_error)
        self.export_worker.start()

    def _on_progress(self, message: str, percent: int):
        """Handle progress updates.

        Args:
            message: Progress message
            percent: Progress percentage (0-100)
        """
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)

    def _on_export_finished(self, result: dict):
        """Handle export completion.

        Args:
            result: Export result dictionary
        """
        if result.get('success'):
            if 'task_count' in result:
                # JSON export
                message = (
                    f"Export completed successfully!\n\n"
                    f"File: {result['filepath']}\n\n"
                    f"Exported:\n"
                    f"  • {result['task_count']} tasks\n"
                    f"  • {result['context_count']} contexts\n"
                    f"  • {result['tag_count']} project tags\n"
                    f"  • {result['dependency_count']} dependencies\n"
                    f"  • {result['comparison_count']} comparisons\n"
                    f"  • {result['history_count']} postpone records\n"
                    f"  • {result['notification_count']} notifications"
                )
            else:
                # Database backup
                size_mb = result['size_bytes'] / (1024 * 1024)
                message = (
                    f"Database backup completed successfully!\n\n"
                    f"File: {result['filepath']}\n"
                    f"Size: {size_mb:.2f} MB"
                )

            MessageBox.information(
                self,
                self.db_connection,
                "Export Successful",
                message
            )
            self.accept()
        else:
            error_msg = result.get('error', 'Unknown error')
            MessageBox.critical(
                self,
                self.db_connection,
                "Export Failed",
                f"Export failed with error:\n\n{error_msg}"
            )
            self._reset_ui()

    def _on_export_error(self, error: str):
        """Handle export error.

        Args:
            error: Error message
        """
        MessageBox.critical(
            self,
            self.db_connection,
            "Export Error",
            f"An error occurred during export:\n\n{error}"
        )
        self._reset_ui()

    def _reset_ui(self):
        """Reset UI controls after export."""
        self.export_btn.setEnabled(True)
        self.json_radio.setEnabled(True)
        self.database_radio.setEnabled(True)
        self.include_settings_check.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
