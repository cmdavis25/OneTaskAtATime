"""
Context Single Select Dialog - Select a single context for filtering

Provides a simple interface for selecting one context to filter Focus Mode tasks.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel
)
from PyQt5.QtCore import Qt
from typing import Optional
from ..models.context import Context
from ..database.connection import DatabaseConnection
from ..database.context_dao import ContextDAO
from .geometry_mixin import GeometryMixin


class ContextSingleSelectDialog(QDialog, GeometryMixin):
    """
    Dialog for selecting a single context filter.

    Features:
    - View available contexts
    - Select one context
    - Support for "No Context" option

    Args:
        selected_context_id: Currently selected context ID (or 'NONE' or None)
        db_connection: Database connection
        parent: Parent widget
    """

    def __init__(self, selected_context_id: Optional[int], db_connection: DatabaseConnection, parent=None):
        """
        Initialize the context single select dialog.

        Args:
            selected_context_id: Currently selected context ID (can be 'NONE' or None)
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.context_dao = ContextDAO(db_connection.get_connection())

        self.all_contexts = []
        self.selected_context_id = selected_context_id

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=400, default_height=400)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Select Context Filter")
        self.setMinimumWidth(400)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Select Context Filter")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)

        info_label = QLabel(
            "Select a context to filter Focus Mode tasks. "
            "Only one context can be selected at a time."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(info_label)

        # Context list
        context_label = QLabel("Available Contexts:")
        context_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(context_label)

        self.context_list = QListWidget()
        self.context_list.setSelectionMode(QListWidget.SingleSelection)
        self.context_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.context_list)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        apply_btn.clicked.connect(self._on_apply)
        bottom_layout.addWidget(apply_btn)

        layout.addLayout(bottom_layout)

    def _load_data(self):
        """Load contexts."""
        # Load all contexts
        self.all_contexts = self.context_dao.get_all()

        self._populate_list()

    def _populate_list(self):
        """Populate the context list."""
        self.context_list.clear()

        # Add special "No Context" option
        no_context_item = QListWidgetItem("(No Context)")
        no_context_item.setData(Qt.UserRole, "NONE")
        self.context_list.addItem(no_context_item)

        # Select "No Context" if it's the current selection
        if self.selected_context_id == "NONE":
            no_context_item.setSelected(True)

        # Add all contexts
        for context in self.all_contexts:
            item = QListWidgetItem(context.name)
            item.setData(Qt.UserRole, context.id)
            self.context_list.addItem(item)

            # Select this item if it's the current selection
            if context.id == self.selected_context_id:
                item.setSelected(True)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on an item (select and close)."""
        self._on_apply()

    def _on_apply(self):
        """Handle apply button click."""
        current_item = self.context_list.currentItem()
        if current_item:
            self.selected_context_id = current_item.data(Qt.UserRole)
            self.accept()

    def get_selected_context_id(self) -> Optional[int]:
        """
        Get the selected context ID.

        Returns:
            Context ID, 'NONE' for no context filter, or None if no selection
        """
        return self.selected_context_id
