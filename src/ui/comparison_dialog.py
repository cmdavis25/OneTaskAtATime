"""
Comparison Dialog - Side-by-side task comparison UI.

When multiple tasks have equal importance scores, this dialog allows users
to make direct comparisons to determine which task is truly higher priority.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Optional, Tuple
from ..models.task import Task


class ComparisonDialog(QDialog):
    """
    Dialog for comparing two tasks side-by-side.

    The user selects which task is higher priority, and the loser's
    priority_adjustment is incremented according to the exponential decay formula.
    """

    def __init__(self, task1: Task, task2: Task, parent=None):
        """
        Initialize the comparison dialog.

        Args:
            task1: First task to compare
            task2: Second task to compare
            parent: Parent widget
        """
        super().__init__(parent)
        self.task1 = task1
        self.task2 = task2
        self.selected_task: Optional[Task] = None

        self.setWindowTitle("Choose Your Priority")
        self.setMinimumSize(800, 500)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)

        # Title section
        self._create_title_section(layout)

        # Comparison cards (side by side)
        self._create_comparison_cards(layout)

        # Action buttons
        self._create_action_buttons(layout)

    def _create_title_section(self, layout: QVBoxLayout):
        """Create the title section explaining the comparison."""
        title_label = QLabel("Which task is more important right now?")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        subtitle_label = QLabel(
            "These tasks have equal importance scores. "
            "Your choice helps refine the priority ranking."
        )
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

    def _create_comparison_cards(self, layout: QVBoxLayout):
        """Create side-by-side task cards."""
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # Task 1 card
        task1_card = self._create_task_card(self.task1, 1)
        cards_layout.addWidget(task1_card)

        # VS label
        vs_label = QLabel("VS")
        vs_font = QFont()
        vs_font.setPointSize(18)
        vs_font.setBold(True)
        vs_label.setFont(vs_font)
        vs_label.setAlignment(Qt.AlignCenter)
        vs_label.setStyleSheet("color: #999; margin: 20px 10px;")
        cards_layout.addWidget(vs_label)

        # Task 2 card
        task2_card = self._create_task_card(self.task2, 2)
        cards_layout.addWidget(task2_card)

        layout.addLayout(cards_layout)

    def _create_task_card(self, task: Task, task_number: int) -> QFrame:
        """
        Create a single task card.

        Args:
            task: Task to display
            task_number: Task number (1 or 2)

        Returns:
            QFrame containing the task card
        """
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setFrameShadow(QFrame.Raised)
        card.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        card_layout = QVBoxLayout()
        card.setLayout(card_layout)

        # Card header
        header_label = QLabel(f"Task {task_number}")
        header_font = QFont()
        header_font.setPointSize(10)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setStyleSheet("color: #007bff;")
        card_layout.addWidget(header_label)

        # Task title
        title_label = QLabel(task.title)
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        title_label.setMinimumHeight(60)
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        card_layout.addWidget(title_label)

        # Task metadata
        metadata_parts = []

        # Priority
        priority_text = task.get_priority_enum().name.capitalize()
        metadata_parts.append(f"Priority: {priority_text}")

        # Effective priority (if adjusted)
        if task.priority_adjustment > 0:
            eff_pri = task.get_effective_priority()
            metadata_parts.append(f"(Eff: {eff_pri:.2f})")

        # Due date
        if task.due_date:
            metadata_parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d')}")

        metadata_label = QLabel(" | ".join(metadata_parts))
        metadata_font = QFont()
        metadata_font.setPointSize(9)
        metadata_label.setFont(metadata_font)
        metadata_label.setStyleSheet("color: #555; margin-top: 5px;")
        metadata_label.setWordWrap(True)
        card_layout.addWidget(metadata_label)

        # Task description (scrollable)
        if task.description:
            desc_scroll = QScrollArea()
            desc_scroll.setWidgetResizable(True)
            desc_scroll.setMaximumHeight(120)
            desc_scroll.setStyleSheet("""
                QScrollArea {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    margin-top: 8px;
                }
            """)

            desc_label = QLabel(task.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("padding: 8px; color: #333;")
            desc_label.setFont(QFont("", 9))
            desc_scroll.setWidget(desc_label)

            card_layout.addWidget(desc_scroll)

        card_layout.addStretch()

        # Select button
        select_button = QPushButton(f"Choose Task {task_number}")
        select_button.setMinimumHeight(40)
        select_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        select_button.clicked.connect(
            lambda: self._on_task_selected(task)
        )
        card_layout.addWidget(select_button)

        return card

    def _create_action_buttons(self, layout: QVBoxLayout):
        """Create bottom action buttons."""
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumSize(100, 35)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-size: 10pt;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _on_task_selected(self, task: Task):
        """
        Handle task selection.

        Args:
            task: The task that was selected as higher priority
        """
        self.selected_task = task
        self.accept()

    def get_winner(self) -> Optional[Task]:
        """
        Get the task that was selected as higher priority.

        Returns:
            The winning task, or None if dialog was cancelled
        """
        return self.selected_task

    def get_loser(self) -> Optional[Task]:
        """
        Get the task that was not selected (lower priority).

        Returns:
            The losing task, or None if dialog was cancelled
        """
        if self.selected_task is None:
            return None

        if self.selected_task == self.task1:
            return self.task2
        else:
            return self.task1

    def get_comparison_result(self) -> Optional[Tuple[Task, Task]]:
        """
        Get the comparison result as (winner, loser) tuple.

        Returns:
            Tuple of (winner_task, loser_task), or None if cancelled
        """
        winner = self.get_winner()
        loser = self.get_loser()

        if winner is None or loser is None:
            return None

        return (winner, loser)


class MultipleComparisonDialog(QDialog):
    """
    Dialog for handling multiple tied tasks (more than 2).

    Presents tasks pairwise until a clear winner emerges.
    """

    def __init__(self, tied_tasks: List[Task], parent=None):
        """
        Initialize the multiple comparison dialog.

        Args:
            tied_tasks: List of tasks tied for top priority
            parent: Parent widget
        """
        super().__init__(parent)
        self.tied_tasks = tied_tasks.copy()
        self.comparison_results: List[Tuple[Task, Task]] = []  # (winner, loser) pairs

        self.setWindowTitle("Resolve Priority Ties")
        self.setMinimumSize(850, 550)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Info label
        info_label = QLabel(
            f"You have {len(self.tied_tasks)} tasks with equal importance scores.\n"
            "Compare them pairwise to determine priority."
        )
        info_font = QFont()
        info_font.setPointSize(11)
        info_label.setFont(info_font)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("margin-bottom: 15px;")
        layout.addWidget(info_label)

        # Start button
        start_button = QPushButton("Start Comparisons")
        start_button.setMinimumHeight(50)
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-size: 12pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        start_button.clicked.connect(self._start_comparisons)
        layout.addWidget(start_button)

        layout.addStretch()

    def _start_comparisons(self):
        """Start the pairwise comparison process."""
        # Use a simple tournament-style comparison
        # Compare pairs and keep winners until one remains
        remaining = self.tied_tasks.copy()

        while len(remaining) > 1:
            # Take first two tasks
            task1 = remaining[0]
            task2 = remaining[1]

            # Show comparison dialog
            dialog = ComparisonDialog(task1, task2, self)
            if dialog.exec_():
                result = dialog.get_comparison_result()
                if result:
                    winner, loser = result
                    self.comparison_results.append((winner, loser))

                    # Remove loser from remaining
                    remaining.remove(loser)
                else:
                    # User cancelled
                    self.reject()
                    return
            else:
                # User cancelled
                self.reject()
                return

        # All comparisons complete
        self.accept()

    def get_comparison_results(self) -> List[Tuple[Task, Task]]:
        """
        Get all comparison results.

        Returns:
            List of (winner, loser) tuples from all comparisons
        """
        return self.comparison_results
