"""
Context Management Dialog - Manage work contexts

Phase 4: Allows users to create, edit, and delete contexts.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List, Optional
from ..models.context import Context
from ..database.connection import DatabaseConnection
from ..database.context_dao import ContextDAO


class ContextManagementDialog(QDialog):
    """
    Dialog for managing contexts.

    Features:
    - View all contexts
    - Create new context
    - Edit existing context
    - Delete context (with confirmation)
    """

    contexts_changed = pyqtSignal()

    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """
        Initialize the context management dialog.

        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.context_dao = ContextDAO(db_connection.get_connection())
        self.contexts: List[Context] = []

        self._init_ui()
        self._load_contexts()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Manage Contexts")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Manage Contexts")
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(header_label)

        info_label = QLabel(
            "Contexts represent work environments or tools (e.g., @computer, @phone, @home).\n"
            "They help filter tasks by what you can do in your current situation."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(info_label)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: List of contexts
        list_layout = QVBoxLayout()

        list_label = QLabel("Existing Contexts:")
        list_label.setStyleSheet("font-weight: bold;")
        list_layout.addWidget(list_label)

        self.context_list = QListWidget()
        self.context_list.currentItemChanged.connect(self._on_context_selected)
        list_layout.addWidget(self.context_list)

        # List action buttons
        list_button_layout = QHBoxLayout()

        new_btn = QPushButton("+ New")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        new_btn.clicked.connect(self._on_new_context)
        list_button_layout.addWidget(new_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        delete_btn.clicked.connect(self._on_delete_context)
        list_button_layout.addWidget(delete_btn)

        list_button_layout.addStretch()

        list_layout.addLayout(list_button_layout)

        content_layout.addLayout(list_layout, 1)

        # Right side: Edit form
        form_layout = QVBoxLayout()

        form_label = QLabel("Context Details:")
        form_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(form_label)

        form_fields = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., @computer, @phone, @errands")
        form_fields.addRow("Name*:", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Optional description...")
        self.description_edit.setMaximumHeight(100)
        form_fields.addRow("Description:", self.description_edit)

        form_layout.addLayout(form_fields)

        # Form action buttons
        form_button_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_form)
        form_button_layout.addWidget(clear_btn)

        form_button_layout.addStretch()

        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.save_btn.clicked.connect(self._on_save_context)
        form_button_layout.addWidget(self.save_btn)

        form_layout.addLayout(form_button_layout)
        form_layout.addStretch()

        content_layout.addLayout(form_layout, 1)

        layout.addLayout(content_layout)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

        # Track current context being edited
        self.current_context: Optional[Context] = None

    def _load_contexts(self):
        """Load all contexts from database."""
        self.contexts = self.context_dao.get_all()
        self._refresh_list()

    def _refresh_list(self):
        """Refresh the context list widget."""
        self.context_list.clear()

        for context in self.contexts:
            item = QListWidgetItem(context.name)
            item.setData(Qt.UserRole, context.id)
            self.context_list.addItem(item)

        if self.contexts:
            self.context_list.setCurrentRow(0)

    def _on_context_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """
        Handle context selection.

        Args:
            current: Currently selected item
            previous: Previously selected item
        """
        if not current:
            self._clear_form()
            return

        context_id = current.data(Qt.UserRole)
        context = self.context_dao.get_by_id(context_id)

        if context:
            self.current_context = context
            self.name_edit.setText(context.name)
            self.description_edit.setText(context.description or "")

    def _on_new_context(self):
        """Handle new context button click."""
        self._clear_form()
        self.context_list.clearSelection()
        self.name_edit.setFocus()

    def _on_save_context(self):
        """Handle save context button click."""
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter a context name."
            )
            self.name_edit.setFocus()
            return

        description = self.description_edit.toPlainText().strip() or None

        try:
            if self.current_context and self.current_context.id:
                # Update existing context
                self.current_context.name = name
                self.current_context.description = description
                self.context_dao.update(self.current_context)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Context '{name}' updated successfully."
                )
            else:
                # Create new context
                new_context = Context(name=name, description=description)
                self.context_dao.create(new_context)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Context '{name}' created successfully."
                )

            self._load_contexts()
            self._clear_form()
            self.contexts_changed.emit()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save context: {str(e)}"
            )

    def _on_delete_context(self):
        """Handle delete context button click."""
        current_item = self.context_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a context to delete."
            )
            return

        context_id = current_item.data(Qt.UserRole)
        context_name = current_item.text()

        reply = QMessageBox.question(
            self,
            "Delete Context",
            f"Are you sure you want to delete context '{context_name}'?\n\n"
            "Tasks using this context will have their context removed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.context_dao.delete(context_id)
                self._load_contexts()
                self._clear_form()
                self.contexts_changed.emit()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Context '{context_name}' deleted successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete context: {str(e)}"
                )

    def _clear_form(self):
        """Clear the edit form."""
        self.current_context = None
        self.name_edit.clear()
        self.description_edit.clear()
