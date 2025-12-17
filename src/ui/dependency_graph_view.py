"""
DependencyGraphView for OneTaskAtATime application.

Text-based tree visualization of task dependency chains.
Shows which tasks are blocking other tasks in a hierarchical format.
"""

from typing import List, Set, Optional, Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ..models.task import Task
from ..models.enums import TaskState
from ..database.task_dao import TaskDAO
from ..database.dependency_dao import DependencyDAO


class DependencyGraphView(QDialog):
    """
    Dialog displaying dependency tree for a task.

    Shows:
    - Tasks that block the selected task (dependencies)
    - Tasks that the selected task blocks (dependents)
    - Visual indicators for task state (✓ completed, ⛔ blocked, etc.)
    - Indented tree structure showing dependency chains

    Example output:
    ```
    Task: Implement user authentication
    ├─ ⛔ Design database schema (ACTIVE)
    │  └─ ⛔ Set up PostgreSQL (ACTIVE)
    │     └─ ✓ Install Docker (COMPLETED)
    └─ ⛔ Create API endpoints (ACTIVE)
       └─ ⛔ Set up Flask app (ACTIVE)
    ```
    """

    def __init__(self, task: Task, db_connection, parent=None):
        """
        Initialize dependency graph view.

        Args:
            task: Task to visualize dependencies for
            db_connection: Database connection (raw or wrapper)
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task

        # Handle both raw connection and DatabaseConnection wrapper
        if hasattr(db_connection, 'get_connection'):
            self.db = db_connection.get_connection()
        else:
            self.db = db_connection

        self.task_dao = TaskDAO(self.db)
        self.dependency_dao = DependencyDAO(self.db)

        self.setWindowTitle(f"Dependency Graph: {task.title}")
        self.setModal(False)  # Non-blocking
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📊 Dependency Graph")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("padding: 10px;")
        layout.addWidget(header)

        # Task info
        task_label = QLabel(f"Task: {self.task.title}")
        task_font = QFont()
        task_font.setPointSize(11)
        task_font.setBold(True)
        task_label.setFont(task_font)
        task_label.setWordWrap(True)
        task_label.setStyleSheet("padding: 5px; background-color: #f8f9fa; border-radius: 3px;")
        layout.addWidget(task_label)

        # Legend
        legend = QLabel(
            "Legend: ✓ = Completed  |  ⛔ = Blocked  |  🔄 = In Progress  |  📅 = Deferred  |  "
            "👤 = Delegated  |  💤 = Someday/Maybe"
        )
        legend.setStyleSheet("padding: 8px; background-color: #e9ecef; font-size: 10px;")
        legend.setWordWrap(True)
        layout.addWidget(legend)

        # Graph display (text-based)
        self.graph_display = QTextEdit()
        self.graph_display.setReadOnly(True)
        self.graph_display.setFont(QFont("Courier New", 10))
        self.graph_display.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #ced4da; padding: 10px;"
        )
        layout.addWidget(self.graph_display)

        # Build and display the graph
        self._build_graph()

        # Buttons
        button_layout = QHBoxLayout()

        export_button = QPushButton("💾 Export to File")
        export_button.clicked.connect(self._export_graph)
        button_layout.addWidget(export_button)

        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.clicked.connect(self._build_graph)
        button_layout.addWidget(refresh_button)

        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _build_graph(self):
        """Build and display the dependency graph."""
        graph_text = []

        # Section 1: Tasks blocking this task (dependencies)
        if self.task.id:
            dependencies = self.dependency_dao.get_dependencies_for_task(self.task.id)

            if dependencies:
                graph_text.append("═" * 60)
                graph_text.append("TASKS BLOCKING THIS TASK")
                graph_text.append("═" * 60)
                graph_text.append("")

                for dep in dependencies:
                    blocking_task = self.task_dao.get_by_id(dep.blocking_task_id)
                    if blocking_task:
                        # Build tree starting from this blocking task
                        tree_lines = self._build_tree(blocking_task, visited=set())
                        graph_text.extend(tree_lines)
                        graph_text.append("")  # Blank line between trees
            else:
                graph_text.append("═" * 60)
                graph_text.append("TASKS BLOCKING THIS TASK")
                graph_text.append("═" * 60)
                graph_text.append("")
                graph_text.append("✓ No blocking tasks - this task is ready to work on!")
                graph_text.append("")

            # Section 2: Tasks blocked by this task (dependents)
            dependents = self.dependency_dao.get_blocking_tasks(self.task.id)

            if dependents:
                graph_text.append("═" * 60)
                graph_text.append("TASKS BLOCKED BY THIS TASK")
                graph_text.append("═" * 60)
                graph_text.append("")

                for dep in dependents:
                    dependent_task = self.task_dao.get_by_id(dep.blocked_task_id)
                    if dependent_task:
                        icon = self._get_task_icon(dependent_task)
                        state_name = dependent_task.state.value if dependent_task.state else "ACTIVE"
                        graph_text.append(f"{icon} {dependent_task.title} ({state_name})")

                graph_text.append("")
            else:
                graph_text.append("═" * 60)
                graph_text.append("TASKS BLOCKED BY THIS TASK")
                graph_text.append("═" * 60)
                graph_text.append("")
                graph_text.append("✓ No dependent tasks - completing this won't unblock anything")
                graph_text.append("")

        else:
            graph_text.append("⚠️ Task has not been saved yet - no dependency information available")

        self.graph_display.setPlainText("\n".join(graph_text))

    def _build_tree(self, task: Task, prefix: str = "", visited: Optional[Set[int]] = None,
                    is_last: bool = True, depth: int = 0) -> List[str]:
        """
        Recursively build tree structure showing dependencies.

        Args:
            task: Current task to display
            prefix: Prefix for tree formatting (e.g., "│  " or "   ")
            visited: Set of task IDs already visited (prevents infinite loops)
            is_last: Whether this is the last child at this level
            depth: Current depth in tree (for limiting recursion)

        Returns:
            List of formatted tree lines
        """
        if visited is None:
            visited = set()

        lines = []

        # Prevent infinite loops from circular dependencies
        if task.id in visited:
            icon = "🔄"  # Circular reference indicator
            state_name = "CIRCULAR"
            lines.append(f"{prefix}{'└─' if is_last else '├─'} {icon} {task.title} ({state_name})")
            return lines

        # Limit depth to prevent extremely deep trees
        MAX_DEPTH = 5
        if depth >= MAX_DEPTH:
            icon = "⋯"
            lines.append(f"{prefix}{'└─' if is_last else '├─'} {icon} {task.title} (MAX DEPTH)")
            return lines

        visited.add(task.id)

        # Display current task
        icon = self._get_task_icon(task)
        state_name = task.state.value if task.state else "ACTIVE"
        lines.append(f"{prefix}{'└─' if is_last else '├─'} {icon} {task.title} ({state_name})")

        # Get dependencies of this task
        if task.id:
            dependencies = self.dependency_dao.get_dependencies_for_task(task.id)

            if dependencies:
                # Prepare prefix for children
                child_prefix = prefix + ("   " if is_last else "│  ")

                for i, dep in enumerate(dependencies):
                    is_last_child = (i == len(dependencies) - 1)
                    blocking_task = self.task_dao.get_by_id(dep.blocking_task_id)

                    if blocking_task:
                        child_lines = self._build_tree(
                            blocking_task,
                            prefix=child_prefix,
                            visited=visited.copy(),  # Pass copy to allow parallel branches
                            is_last=is_last_child,
                            depth=depth + 1
                        )
                        lines.extend(child_lines)

        return lines

    def _get_task_icon(self, task: Task) -> str:
        """
        Get visual indicator for task state.

        Args:
            task: Task to get icon for

        Returns:
            Icon string (emoji)
        """
        if not task.state:
            return "⚪"  # No state (shouldn't happen)

        state_icons = {
            TaskState.ACTIVE: "🔄",
            TaskState.COMPLETED: "✓",
            TaskState.DEFERRED: "📅",
            TaskState.DELEGATED: "👤",
            TaskState.SOMEDAY: "💤",
            TaskState.TRASH: "🗑️"
        }

        icon = state_icons.get(task.state, "⚪")

        # Add blocker indicator if task is blocked
        if task.id and task.blocking_task_ids:
            icon = "⛔"

        return icon

    def _export_graph(self):
        """Export graph to plain text file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Dependency Graph",
            f"dependency_graph_{self.task.id}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Dependency Graph: {self.task.title}\n")
                    f.write(f"Generated: {__import__('datetime').datetime.now().isoformat()}\n")
                    f.write("\n")
                    f.write(self.graph_display.toPlainText())

                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Dependency graph exported to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export graph:\n{str(e)}"
                )
