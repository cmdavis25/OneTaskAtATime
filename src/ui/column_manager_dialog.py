"""
Column Manager Dialog - Manage visible columns and their order

Phase 4 Enhancement: Provides a dual-list interface for managing table columns.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel
)
from PyQt5.QtCore import Qt
from typing import List, Dict
from .geometry_mixin import GeometryMixin


class ColumnManagerDialog(QDialog, GeometryMixin):
    """
    Dialog for managing table column visibility and order.

    Features:
    - View available columns
    - Show/hide columns
    - Reorder visible columns
    - Drag and drop or use buttons to reorder

    Args:
        visible_columns: List of column names currently visible (in order)
        all_columns: Dictionary mapping column names to their display labels
        parent: Parent widget
    """

    def __init__(self, visible_columns: List[str], all_columns: Dict[str, str], parent=None):
        """
        Initialize the column manager dialog.

        Args:
            visible_columns: List of currently visible column names (in display order)
            all_columns: Dictionary of all available columns {name: display_label}
            parent: Parent widget
        """
        super().__init__(parent)
        self.all_columns = all_columns
        self.visible_columns = list(visible_columns)  # Make a copy
        self.available_columns = [col for col in all_columns.keys() if col not in visible_columns]

        # Initialize geometry persistence (get db_connection from parent if available)
        if parent and hasattr(parent, 'db_connection'):
            self._init_geometry_persistence(parent.db_connection, default_width=700, default_height=600)

        self._init_ui()
        self._refresh_lists()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Manage Columns")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Manage Table Columns")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)

        info_label = QLabel(
            "Select which columns to display and their order. "
            "Drag items in the Active Columns list to reorder them."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(info_label)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: Available columns
        available_layout = QVBoxLayout()

        available_label = QLabel("Available Columns:")
        available_label.setStyleSheet("font-weight: bold;")
        available_layout.addWidget(available_label)

        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SingleSelection)
        available_layout.addWidget(self.available_list)

        add_btn = QPushButton("Show Column →")
        add_btn.setStyleSheet("""
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
        add_btn.clicked.connect(self._on_show_column)
        available_layout.addWidget(add_btn)

        content_layout.addLayout(available_layout, 1)

        # Right side: Active columns
        active_layout = QVBoxLayout()

        active_label = QLabel("Active Columns (in display order):")
        active_label.setStyleSheet("font-weight: bold;")
        active_layout.addWidget(active_label)

        self.active_list = QListWidget()
        self.active_list.setSelectionMode(QListWidget.SingleSelection)
        self.active_list.setDragDropMode(QListWidget.InternalMove)  # Enable drag and drop
        active_layout.addWidget(self.active_list)

        # Buttons for removing and reordering
        buttons_layout = QHBoxLayout()

        remove_btn = QPushButton("← Hide Column")
        remove_btn.setStyleSheet("""
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
        remove_btn.clicked.connect(self._on_hide_column)
        buttons_layout.addWidget(remove_btn)

        move_up_btn = QPushButton("↑ Move Up")
        move_up_btn.clicked.connect(self._on_move_up)
        buttons_layout.addWidget(move_up_btn)

        move_down_btn = QPushButton("↓ Move Down")
        move_down_btn.clicked.connect(self._on_move_down)
        buttons_layout.addWidget(move_down_btn)

        active_layout.addLayout(buttons_layout)

        content_layout.addLayout(active_layout, 1)

        layout.addLayout(content_layout)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self._on_reset_to_default)
        bottom_layout.addWidget(reset_btn)

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
        apply_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(apply_btn)

        layout.addLayout(bottom_layout)

    def _refresh_lists(self):
        """Refresh both lists."""
        # Update available columns
        self.available_list.clear()
        for col_name in sorted(self.available_columns):
            if col_name in self.all_columns:
                item = QListWidgetItem(self.all_columns[col_name])
                item.setData(Qt.UserRole, col_name)
                self.available_list.addItem(item)

        # Update active columns (in order)
        self.active_list.clear()
        for col_name in self.visible_columns:
            if col_name in self.all_columns:
                item = QListWidgetItem(self.all_columns[col_name])
                item.setData(Qt.UserRole, col_name)
                self.active_list.addItem(item)

    def _on_show_column(self):
        """Handle show column button click."""
        current_item = self.available_list.currentItem()
        if not current_item:
            return

        col_name = current_item.data(Qt.UserRole)

        # Add to visible columns
        self.visible_columns.append(col_name)

        # Remove from available columns
        self.available_columns.remove(col_name)

        # Refresh lists
        self._refresh_lists()

    def _on_hide_column(self):
        """Handle hide column button click."""
        current_item = self.active_list.currentItem()
        if not current_item:
            return

        col_name = current_item.data(Qt.UserRole)

        # Don't allow hiding ID or Title columns
        if col_name in ["ID", "Title"]:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Cannot Hide Column",
                f"The '{self.all_columns[col_name]}' column cannot be hidden."
            )
            return

        # Remove from visible columns
        self.visible_columns.remove(col_name)

        # Add to available columns
        self.available_columns.append(col_name)

        # Refresh lists
        self._refresh_lists()

    def _on_move_up(self):
        """Move the selected column up in the list."""
        current_row = self.active_list.currentRow()
        if current_row <= 0:
            return

        # Swap in visible_columns list
        self.visible_columns[current_row], self.visible_columns[current_row - 1] = \
            self.visible_columns[current_row - 1], self.visible_columns[current_row]

        # Refresh and restore selection
        self._refresh_lists()
        self.active_list.setCurrentRow(current_row - 1)

    def _on_move_down(self):
        """Move the selected column down in the list."""
        current_row = self.active_list.currentRow()
        if current_row < 0 or current_row >= len(self.visible_columns) - 1:
            return

        # Swap in visible_columns list
        self.visible_columns[current_row], self.visible_columns[current_row + 1] = \
            self.visible_columns[current_row + 1], self.visible_columns[current_row]

        # Refresh and restore selection
        self._refresh_lists()
        self.active_list.setCurrentRow(current_row + 1)

    def _on_reset_to_default(self):
        """Reset columns to default configuration."""
        from PyQt5.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Reset to Default",
            "Are you sure you want to reset the column configuration to default?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Default visible columns (all columns in original order)
            self.visible_columns = list(self.all_columns.keys())
            self.available_columns = []
            self._refresh_lists()

    def get_visible_columns(self) -> List[str]:
        """
        Get the list of visible columns in display order.

        Also updates the order based on any drag-and-drop reordering done by the user.

        Returns:
            List of column names in display order
        """
        # Update visible_columns based on current list order (in case of drag-and-drop)
        self.visible_columns = []
        for i in range(self.active_list.count()):
            item = self.active_list.item(i)
            col_name = item.data(Qt.UserRole)
            self.visible_columns.append(col_name)

        return self.visible_columns
