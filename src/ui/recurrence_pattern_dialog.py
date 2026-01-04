"""
Recurrence Pattern Dialog - Advanced pattern configuration

Provides a tabbed interface for configuring complex recurrence patterns:
- Weekly: Select specific days of the week
- Monthly: Choose day of month or Nth weekday patterns
- Preview: Show next 5 occurrence dates
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QCheckBox, QRadioButton, QSpinBox,
    QButtonGroup, QGroupBox, QFormLayout, QTextEdit, QComboBox
)
from PyQt5.QtCore import Qt
from datetime import date, timedelta
from typing import Optional
from ..models.recurrence_pattern import RecurrencePattern, RecurrenceType
from .geometry_mixin import GeometryMixin


class RecurrencePatternDialog(QDialog, GeometryMixin):
    """
    Dialog for configuring advanced recurrence patterns.

    Provides tabbed interface for:
    - Weekly patterns with day-of-week selection
    - Monthly patterns with day-of-month or Nth-weekday options
    - Preview of next occurrence dates
    """

    def __init__(self, pattern: Optional[RecurrencePattern] = None,
                 current_due_date: Optional[date] = None,
                 parent=None):
        """
        Initialize the recurrence pattern dialog.

        Args:
            pattern: Existing pattern to edit, or None for new
            current_due_date: Task due date for preview calculation
            parent: Parent widget
        """
        super().__init__(parent)
        self.pattern = pattern
        self.current_due_date = current_due_date or date.today()

        # Initialize geometry persistence (get db_connection from parent if available)
        if parent and hasattr(parent, 'db_connection'):
            self._init_geometry_persistence(parent.db_connection, default_width=500, default_height=400)

        self._init_ui()

        if pattern:
            self._load_pattern(pattern)

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Advanced Recurrence Pattern")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Apply stylesheet for QComboBox to show clear dropdown arrows
        self.setStyleSheet("""
            QComboBox {
                padding: 5px;
                padding-right: 25px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #495057;
                width: 0;
                height: 0;
                margin-right: 5px;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Configure Advanced Recurrence Pattern")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)

        # Tab widget
        self.tabs = QTabWidget()

        # Weekly tab
        self.weekly_tab = self._create_weekly_tab()
        self.tabs.addTab(self.weekly_tab, "Weekly")

        # Monthly tab
        self.monthly_tab = self._create_monthly_tab()
        self.tabs.addTab(self.monthly_tab, "Monthly")

        layout.addWidget(self.tabs)

        # Preview section
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()

        preview_label = QLabel("Next 5 occurrences:")
        preview_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(preview_label)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(120)
        preview_layout.addWidget(self.preview_text)

        preview_btn = QPushButton("Update Preview")
        preview_btn.clicked.connect(self._update_preview)
        preview_layout.addWidget(preview_btn)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Pattern")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_weekly_tab(self) -> QWidget:
        """Create the weekly pattern configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)

        # Interval
        interval_layout = QFormLayout()
        self.weekly_interval_spin = QSpinBox()
        self.weekly_interval_spin.setMinimum(1)
        self.weekly_interval_spin.setMaximum(52)
        self.weekly_interval_spin.setValue(1)
        interval_layout.addRow("Repeat every", self.weekly_interval_spin)
        interval_layout.addRow("", QLabel("week(s) on:"))
        layout.addLayout(interval_layout)

        # Day checkboxes
        days_group = QGroupBox("Days of Week")
        days_layout = QVBoxLayout()
        days_layout.setSpacing(8)

        self.day_checkboxes = {}
        day_names = [
            ("Monday", 0),
            ("Tuesday", 1),
            ("Wednesday", 2),
            ("Thursday", 3),
            ("Friday", 4),
            ("Saturday", 5),
            ("Sunday", 6)
        ]

        for day_name, day_index in day_names:
            checkbox = QCheckBox(day_name)
            self.day_checkboxes[day_index] = checkbox
            days_layout.addWidget(checkbox)

        days_group.setLayout(days_layout)
        layout.addWidget(days_group)

        # Quick select buttons
        quick_select_layout = QHBoxLayout()

        weekdays_btn = QPushButton("Weekdays")
        weekdays_btn.clicked.connect(self._select_weekdays)
        quick_select_layout.addWidget(weekdays_btn)

        weekend_btn = QPushButton("Weekend")
        weekend_btn.clicked.connect(self._select_weekend)
        quick_select_layout.addWidget(weekend_btn)

        all_days_btn = QPushButton("All Days")
        all_days_btn.clicked.connect(self._select_all_days)
        quick_select_layout.addWidget(all_days_btn)

        clear_days_btn = QPushButton("Clear")
        clear_days_btn.clicked.connect(self._clear_days)
        quick_select_layout.addWidget(clear_days_btn)

        quick_select_layout.addStretch()
        layout.addLayout(quick_select_layout)

        layout.addStretch()
        return tab

    def _create_monthly_tab(self) -> QWidget:
        """Create the monthly pattern configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)

        # Interval
        interval_layout = QFormLayout()
        self.monthly_interval_spin = QSpinBox()
        self.monthly_interval_spin.setMinimum(1)
        self.monthly_interval_spin.setMaximum(12)
        self.monthly_interval_spin.setValue(1)
        interval_layout.addRow("Repeat every", self.monthly_interval_spin)
        interval_layout.addRow("", QLabel("month(s)"))
        layout.addLayout(interval_layout)

        # Pattern type selection
        pattern_group = QGroupBox("Monthly Pattern")
        pattern_layout = QVBoxLayout()
        pattern_layout.setSpacing(10)

        self.monthly_pattern_group = QButtonGroup(self)

        # Day of month option
        day_of_month_container = QWidget()
        day_of_month_layout = QHBoxLayout()
        day_of_month_layout.setContentsMargins(0, 0, 0, 0)

        self.day_of_month_radio = QRadioButton("On day")
        self.day_of_month_radio.setChecked(True)
        self.monthly_pattern_group.addButton(self.day_of_month_radio, 0)
        day_of_month_layout.addWidget(self.day_of_month_radio)

        self.day_of_month_spin = QSpinBox()
        self.day_of_month_spin.setMinimum(1)
        self.day_of_month_spin.setMaximum(31)
        self.day_of_month_spin.setValue(1)
        day_of_month_layout.addWidget(self.day_of_month_spin)

        day_of_month_layout.addWidget(QLabel("of each month"))
        day_of_month_layout.addStretch()
        day_of_month_container.setLayout(day_of_month_layout)
        pattern_layout.addWidget(day_of_month_container)

        # Nth weekday option
        nth_weekday_container = QWidget()
        nth_weekday_layout = QHBoxLayout()
        nth_weekday_layout.setContentsMargins(0, 0, 0, 0)

        self.nth_weekday_radio = QRadioButton("On the")
        self.monthly_pattern_group.addButton(self.nth_weekday_radio, 1)
        nth_weekday_layout.addWidget(self.nth_weekday_radio)

        self.week_of_month_combo = QComboBox()
        self.week_of_month_combo.addItem("1st", 1)
        self.week_of_month_combo.addItem("2nd", 2)
        self.week_of_month_combo.addItem("3rd", 3)
        self.week_of_month_combo.addItem("4th", 4)
        self.week_of_month_combo.addItem("Last", -1)
        nth_weekday_layout.addWidget(self.week_of_month_combo)

        self.weekday_of_month_combo = QComboBox()
        self.weekday_of_month_combo.addItem("Monday", 0)
        self.weekday_of_month_combo.addItem("Tuesday", 1)
        self.weekday_of_month_combo.addItem("Wednesday", 2)
        self.weekday_of_month_combo.addItem("Thursday", 3)
        self.weekday_of_month_combo.addItem("Friday", 4)
        self.weekday_of_month_combo.addItem("Saturday", 5)
        self.weekday_of_month_combo.addItem("Sunday", 6)
        nth_weekday_layout.addWidget(self.weekday_of_month_combo)

        nth_weekday_layout.addWidget(QLabel("of each month"))
        nth_weekday_layout.addStretch()
        nth_weekday_container.setLayout(nth_weekday_layout)
        pattern_layout.addWidget(nth_weekday_container)

        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)

        layout.addStretch()
        return tab

    def _select_weekdays(self):
        """Select Monday through Friday."""
        for day_index in range(5):  # 0-4 (Mon-Fri)
            self.day_checkboxes[day_index].setChecked(True)
        for day_index in range(5, 7):  # 5-6 (Sat-Sun)
            self.day_checkboxes[day_index].setChecked(False)

    def _select_weekend(self):
        """Select Saturday and Sunday."""
        for day_index in range(5):  # 0-4 (Mon-Fri)
            self.day_checkboxes[day_index].setChecked(False)
        for day_index in range(5, 7):  # 5-6 (Sat-Sun)
            self.day_checkboxes[day_index].setChecked(True)

    def _select_all_days(self):
        """Select all days of the week."""
        for checkbox in self.day_checkboxes.values():
            checkbox.setChecked(True)

    def _clear_days(self):
        """Clear all day selections."""
        for checkbox in self.day_checkboxes.values():
            checkbox.setChecked(False)

    def _load_pattern(self, pattern: RecurrencePattern):
        """
        Load an existing pattern into the dialog.

        Args:
            pattern: Pattern to load
        """
        if pattern.type == RecurrenceType.WEEKLY:
            self.tabs.setCurrentIndex(0)  # Weekly tab
            self.weekly_interval_spin.setValue(pattern.interval)

            # Set day checkboxes
            if pattern.days_of_week:
                for day_index in pattern.days_of_week:
                    if day_index in self.day_checkboxes:
                        self.day_checkboxes[day_index].setChecked(True)

        elif pattern.type == RecurrenceType.MONTHLY:
            self.tabs.setCurrentIndex(1)  # Monthly tab
            self.monthly_interval_spin.setValue(pattern.interval)

            if pattern.day_of_month is not None:
                self.day_of_month_radio.setChecked(True)
                self.day_of_month_spin.setValue(pattern.day_of_month)
            elif pattern.week_of_month is not None and pattern.weekday_of_month is not None:
                self.nth_weekday_radio.setChecked(True)

                # Set week of month
                for i in range(self.week_of_month_combo.count()):
                    if self.week_of_month_combo.itemData(i) == pattern.week_of_month:
                        self.week_of_month_combo.setCurrentIndex(i)
                        break

                # Set weekday
                for i in range(self.weekday_of_month_combo.count()):
                    if self.weekday_of_month_combo.itemData(i) == pattern.weekday_of_month:
                        self.weekday_of_month_combo.setCurrentIndex(i)
                        break

        self._update_preview()

    def _update_preview(self):
        """Calculate and display the next 5 occurrence dates."""
        pattern = self.get_pattern()
        if not pattern:
            self.preview_text.setText("Invalid pattern configuration")
            return

        try:
            preview_lines = []
            current_date = self.current_due_date

            for i in range(5):
                next_date = pattern.calculate_next_date(current_date)
                preview_lines.append(f"{i + 1}. {next_date.strftime('%A, %B %d, %Y')}")
                current_date = next_date

            self.preview_text.setText("\n".join(preview_lines))
        except Exception as e:
            self.preview_text.setText(f"Error calculating dates: {str(e)}")

    def get_pattern(self) -> Optional[RecurrencePattern]:
        """
        Build and return the configured pattern.

        Returns:
            RecurrencePattern object, or None if invalid
        """
        current_tab = self.tabs.currentIndex()

        if current_tab == 0:  # Weekly
            interval = self.weekly_interval_spin.value()

            # Get selected days
            selected_days = [
                day_index for day_index, checkbox in self.day_checkboxes.items()
                if checkbox.isChecked()
            ]

            if not selected_days:
                return None  # Must select at least one day

            return RecurrencePattern(
                type=RecurrenceType.WEEKLY,
                interval=interval,
                days_of_week=selected_days
            )

        elif current_tab == 1:  # Monthly
            interval = self.monthly_interval_spin.value()

            if self.day_of_month_radio.isChecked():
                # Day of month pattern
                return RecurrencePattern(
                    type=RecurrenceType.MONTHLY,
                    interval=interval,
                    day_of_month=self.day_of_month_spin.value()
                )
            else:
                # Nth weekday pattern
                return RecurrencePattern(
                    type=RecurrenceType.MONTHLY,
                    interval=interval,
                    week_of_month=self.week_of_month_combo.currentData(),
                    weekday_of_month=self.weekday_of_month_combo.currentData()
                )

        return None
