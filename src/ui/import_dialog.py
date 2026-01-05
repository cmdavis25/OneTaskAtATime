"""Import dialog for restoring application data.

Provides UI for importing data from JSON backups with replace/merge modes.
"""
import json
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QGroupBox, QFileDialog, QProgressBar,
    QTextEdit, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from ..services.import_service import ImportService
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class ImportWorker(QThread):
    """Worker thread for import operations."""

    progress = pyqtSignal(str, int)  # message, percent
    finished = pyqtSignal(dict)  # result dictionary
    error = pyqtSignal(str)  # error message

    def __init__(self, import_service: ImportService, filepath: str, merge_mode: bool):
        """Initialize import worker.

        Args:
            import_service: ImportService instance
            filepath: Source file path
            merge_mode: Whether to merge (True) or replace (False)
        """
        super().__init__()
        self.import_service = import_service
        self.filepath = filepath
        self.merge_mode = merge_mode

    def run(self):
        """Run the import operation."""
        try:
            result = self.import_service.import_from_json(
                self.filepath,
                self.merge_mode,
                self.progress.emit
            )
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class ImportDialog(QDialog, GeometryMixin):
    """Dialog for importing application data."""

    def __init__(self, db_connection: sqlite3.Connection, parent=None):
        """Initialize import dialog.

        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.import_service = ImportService(db_connection)
        self.import_worker = None
        self.file_summary = None

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=550, default_height=550)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Import Data")
        self.setMinimumSize(550, 550)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Import Data")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Description
        desc_label = QLabel(
            "Import data from a JSON backup file. You can either replace "
            "all existing data or merge the imported data with your current data."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # File selection group
        file_group = QGroupBox("Import File")
        file_layout = QVBoxLayout()

        path_layout = QHBoxLayout()
        self.filepath_edit = QLineEdit()
        self.filepath_edit.setPlaceholderText("Select import file...")
        self.filepath_edit.setReadOnly(True)
        path_layout.addWidget(self.filepath_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        path_layout.addWidget(browse_btn)

        file_layout.addLayout(path_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # File summary display
        summary_group = QGroupBox("File Summary")
        summary_layout = QVBoxLayout()

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(120)
        self.summary_text.setPlaceholderText("Select a file to see import summary...")
        summary_layout.addWidget(self.summary_text)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Import mode group
        mode_group = QGroupBox("Import Mode")
        mode_layout = QVBoxLayout()

        self.replace_radio = QRadioButton("Replace All Data")
        self.replace_radio.setChecked(True)
        self.replace_radio.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.replace_radio)

        replace_desc = QLabel(
            "⚠️ WARNING: This will DELETE all existing data and replace it with the imported data."
        )
        replace_desc.setWordWrap(True)
        replace_desc.setStyleSheet("color: #d32f2f; margin-left: 20px; font-weight: bold;")
        mode_layout.addWidget(replace_desc)

        mode_layout.addSpacing(10)

        self.merge_radio = QRadioButton("Merge with Existing Data")
        mode_layout.addWidget(self.merge_radio)

        merge_desc = QLabel(
            "Import data will be added to existing data. ID conflicts will be resolved automatically."
        )
        merge_desc.setWordWrap(True)
        merge_desc.setStyleSheet("color: #666; margin-left: 20px;")
        mode_layout.addWidget(merge_desc)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Warning banner (shown for replace mode)
        self.warning_banner = QLabel(
            "⚠️ CAUTION: Replace mode will permanently delete all existing data!"
        )
        self.warning_banner.setWordWrap(True)
        self.warning_banner.setStyleSheet(
            "background-color: #ffebee; color: #c62828; "
            "padding: 10px; border: 2px solid #c62828; border-radius: 4px; font-weight: bold;"
        )
        layout.addWidget(self.warning_banner)

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

        self.import_btn = QPushButton("Import")
        self.import_btn.setObjectName("primaryButton")
        self.import_btn.clicked.connect(self._start_import)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _on_mode_changed(self):
        """Handle import mode radio button change."""
        is_replace = self.replace_radio.isChecked()
        self.warning_banner.setVisible(is_replace)

    def _browse_file(self):
        """Open file dialog to select import file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Import File",
            "",
            "JSON Files (*.json)"
        )

        if filepath:
            self.filepath_edit.setText(filepath)
            self._load_file_summary(filepath)

    def _load_file_summary(self, filepath: str):
        """Load and display summary of import file.

        Args:
            filepath: Path to JSON file
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if valid import file
            if 'metadata' not in data:
                self.summary_text.setPlainText("Error: Invalid import file (missing metadata)")
                self.import_btn.setEnabled(False)
                return

            metadata = data.get('metadata', {})
            schema_version = metadata.get('schema_version', 'Unknown')
            export_date = metadata.get('export_date', 'Unknown')

            # Check schema version compatibility
            if schema_version > ImportService.SUPPORTED_SCHEMA_VERSION:
                self.summary_text.setPlainText(
                    f"❌ ERROR: Schema version {schema_version} is not supported.\n"
                    f"This application supports up to version {ImportService.SUPPORTED_SCHEMA_VERSION}.\n"
                    "Please upgrade the application to import this file."
                )
                self.summary_text.setStyleSheet("color: #c62828;")
                self.import_btn.setEnabled(False)
                return

            # Format export date
            try:
                dt = datetime.fromisoformat(export_date)
                export_date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                export_date_str = export_date

            # Count items
            task_count = len(data.get('tasks', []))
            context_count = len(data.get('contexts', []))
            tag_count = len(data.get('project_tags', []))
            dep_count = len(data.get('dependencies', []))
            comp_count = len(data.get('task_comparisons', []))
            hist_count = len(data.get('postpone_history', []))
            notif_count = len(data.get('notifications', []))
            has_settings = 'settings' in data

            # Build summary
            summary = (
                f"Export Date: {export_date_str}\n"
                f"Schema Version: {schema_version}\n"
                f"App Version: {metadata.get('app_version', 'Unknown')}\n\n"
                f"Contents:\n"
                f"  • {task_count} tasks\n"
                f"  • {context_count} contexts\n"
                f"  • {tag_count} project tags\n"
                f"  • {dep_count} dependencies\n"
                f"  • {comp_count} task comparisons\n"
                f"  • {hist_count} postpone records\n"
                f"  • {notif_count} notifications\n"
            )

            if has_settings:
                summary += f"  • Settings included\n"

            self.summary_text.setPlainText(summary)
            self.summary_text.setStyleSheet("")
            self.import_btn.setEnabled(True)
            self.file_summary = data

        except json.JSONDecodeError as e:
            self.summary_text.setPlainText(f"Error: Invalid JSON file\n{str(e)}")
            self.summary_text.setStyleSheet("color: #c62828;")
            self.import_btn.setEnabled(False)
        except Exception as e:
            self.summary_text.setPlainText(f"Error reading file:\n{str(e)}")
            self.summary_text.setStyleSheet("color: #c62828;")
            self.import_btn.setEnabled(False)

    def _start_import(self):
        """Start the import operation."""
        filepath = self.filepath_edit.text()

        if not filepath:
            MessageBox.warning(
                self,
                self.db_connection,
                "No File Selected",
                "Please select an import file."
            )
            return

        merge_mode = self.merge_radio.isChecked()
        mode_str = "merge" if merge_mode else "replace"

        # Confirm replace mode
        if not merge_mode:
            confirm = MessageBox.warning(
                self,
                self.db_connection,
                "Confirm Data Replacement",
                "You are about to REPLACE ALL EXISTING DATA.\n\n"
                "This will PERMANENTLY DELETE:\n"
                "• All tasks\n"
                "• All contexts and project tags\n"
                "• All comparisons and history\n"
                "• All notifications\n"
                "• All settings\n\n"
                "This action CANNOT BE UNDONE!\n\n"
                "Are you sure you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if confirm != QMessageBox.Yes:
                return

        # Disable controls during import
        self.import_btn.setEnabled(False)
        self.replace_radio.setEnabled(False)
        self.merge_radio.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Create and start worker thread
        self.import_worker = ImportWorker(
            self.import_service,
            filepath,
            merge_mode
        )
        self.import_worker.progress.connect(self._on_progress)
        self.import_worker.finished.connect(self._on_import_finished)
        self.import_worker.error.connect(self._on_import_error)
        self.import_worker.start()

    def _on_progress(self, message: str, percent: int):
        """Handle progress updates.

        Args:
            message: Progress message
            percent: Progress percentage (0-100)
        """
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)

    def _on_import_finished(self, result: dict):
        """Handle import completion.

        Args:
            result: Import result dictionary
        """
        if result.get('success'):
            message = (
                f"Import completed successfully!\n\n"
                f"Imported:\n"
                f"  • {result['task_count']} tasks\n"
                f"  • {result['context_count']} contexts\n"
                f"  • {result['tag_count']} project tags\n"
                f"  • {result.get('dependency_count', 0)} dependencies\n"
                f"  • {result.get('comparison_count', 0)} comparisons\n"
                f"  • {result.get('history_count', 0)} postpone records\n"
                f"  • {result.get('notification_count', 0)} notifications"
            )

            if result.get('warnings'):
                message += "\n\nWarnings:\n"
                for warning in result['warnings']:
                    message += f"  • {warning}\n"

            MessageBox.information(
                self,
                self.db_connection,
                "Import Successful",
                message
            )
            self.accept()
        else:
            error_msg = result.get('error', 'Unknown error')
            MessageBox.critical(
                self,
                self.db_connection,
                "Import Failed",
                f"Import failed with error:\n\n{error_msg}"
            )
            self._reset_ui()

    def _on_import_error(self, error: str):
        """Handle import error.

        Args:
            error: Error message
        """
        MessageBox.critical(
            self,
            self.db_connection,
            "Import Error",
            f"An error occurred during import:\n\n{error}"
        )
        self._reset_ui()

    def _reset_ui(self):
        """Reset UI controls after import."""
        self.import_btn.setEnabled(True)
        self.replace_radio.setEnabled(True)
        self.merge_radio.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
