"""
Settings Dialog for OneTaskAtATime application.

Provides comprehensive settings management with tabbed interface for:
- Resurfacing intervals and timing
- Notification preferences
- Intervention thresholds
"""

import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QFormLayout, QSpinBox, QTimeEdit,
    QCheckBox, QGroupBox, QMessageBox, QComboBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QTime, pyqtSignal
from PyQt5.QtGui import QFont

from ..database.settings_dao import SettingsDAO
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class SettingsDialog(QDialog, GeometryMixin):
    """
    Dialog for application settings configuration.

    Provides tabbed interface for organizing settings into logical groups:
    - Resurfacing: Task resurfacing intervals and timing
    - Notifications: Notification channel preferences
    - Triggers: Which events generate notifications
    - Intervention: Postponement pattern detection thresholds
    """

    # Signal emitted when settings are saved
    settings_saved = pyqtSignal()
    # Signal emitted when user wants to re-run the welcome wizard
    rerun_wizard_requested = pyqtSignal()

    def __init__(self, db_connection: sqlite3.Connection, parent=None):
        """
        Initialize settings dialog.

        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.settings_dao = SettingsDAO(db_connection)

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=600, default_height=500)

        self._init_ui()
        self._load_settings()
        self._create_test_aliases()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Application Settings")
        self.setMinimumSize(600, 500)

        # Enable WhatsThis help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # Set WhatsThis text for the dialog
        self.setWhatsThis(
            "This dialog allows you to configure application settings across multiple categories. "
            "Click the ? button and then any field for specific help about that setting."
        )

        # Remove hardcoded inline styles - let theme handle it
        # Just ensure padding-right for dropdown arrow
        self.setStyleSheet("""
            QComboBox {
                padding-right: 25px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Settings")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Tab widget
        self.tab_widget = QTabWidget()

        self.resurfacing_tab = self._create_resurfacing_tab()
        self.notifications_tab = self._create_notifications_tab()
        self.triggers_tab = self._create_triggers_tab()
        self.intervention_tab = self._create_intervention_tab()
        self.theme_tab = self._create_theme_tab()
        self.advanced_tab = self._create_advanced_tab()

        self.tab_widget.addTab(self.resurfacing_tab, "Resurfacing")
        self.tab_widget.addTab(self.notifications_tab, "Notifications")
        self.tab_widget.addTab(self.triggers_tab, "Notification Triggers")
        self.tab_widget.addTab(self.intervention_tab, "Intervention")
        self.tab_widget.addTab(self.theme_tab, "Theme")
        self.tab_widget.addTab(self.advanced_tab, "Advanced")

        layout.addWidget(self.tab_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_settings)
        self.save_button.setWhatsThis(
            "Save all settings changes and apply them immediately. Theme changes will take effect right away."
        )
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setWhatsThis(
            "Discard all changes and close the settings dialog without saving."
        )
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _create_resurfacing_tab(self) -> QWidget:
        """Create the resurfacing settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        # Deferred tasks group
        deferred_group = QGroupBox("Deferred Tasks")
        deferred_form = QFormLayout()

        self.deferred_check_hours_spin = QSpinBox()
        self.deferred_check_hours_spin.setRange(1, 24)
        self.deferred_check_hours_spin.setSuffix(" hours")
        self.deferred_check_hours_spin.setToolTip("How often to check for deferred tasks becoming active")
        self.deferred_check_hours_spin.setWhatsThis(
            "How often to check for deferred tasks becoming active. The system checks at this interval "
            "to see if any deferred tasks have reached their start date and should be resurfaced."
        )
        deferred_form.addRow("Check Interval:", self.deferred_check_hours_spin)

        deferred_group.setLayout(deferred_form)
        layout.addWidget(deferred_group)

        # Delegated tasks group
        delegated_group = QGroupBox("Delegated Tasks")
        delegated_form = QFormLayout()

        self.delegated_check_time_edit = QTimeEdit()
        self.delegated_check_time_edit.setDisplayFormat("HH:mm")
        self.delegated_check_time_edit.setToolTip("Time of day to check for delegated tasks needing follow-up")
        self.delegated_check_time_edit.setWhatsThis(
            "Time of day to check for delegated tasks that need follow-up. The system will check daily "
            "at this time to see if any delegated tasks have reached their follow-up date."
        )
        delegated_form.addRow("Check Time:", self.delegated_check_time_edit)

        delegated_group.setLayout(delegated_form)
        layout.addWidget(delegated_group)

        # Someday tasks group
        someday_group = QGroupBox("Someday/Maybe Tasks")
        someday_form = QFormLayout()

        self.someday_review_days_spin = QSpinBox()
        self.someday_review_days_spin.setRange(1, 90)
        self.someday_review_days_spin.setSuffix(" days")
        self.someday_review_days_spin.setToolTip("How often to prompt for Someday/Maybe review")
        self.someday_review_days_spin.setWhatsThis(
            "How often to prompt you to review Someday/Maybe tasks. These tasks are not currently actionable "
            "but should be reviewed periodically to see if they've become relevant."
        )
        someday_form.addRow("Review Interval:", self.someday_review_days_spin)

        self.someday_review_time_edit = QTimeEdit()
        self.someday_review_time_edit.setDisplayFormat("HH:mm")
        self.someday_review_time_edit.setToolTip("Preferred time for someday review trigger")
        self.someday_review_time_edit.setWhatsThis(
            "Preferred time of day for someday task review reminders. The system will notify you "
            "at this time when it's time to review your Someday/Maybe list."
        )
        someday_form.addRow("Review Time:", self.someday_review_time_edit)

        someday_group.setLayout(someday_form)
        layout.addWidget(someday_group)

        # Postponement analysis group
        postpone_group = QGroupBox("Postponement Analysis")
        postpone_form = QFormLayout()

        self.postpone_analysis_time_edit = QTimeEdit()
        self.postpone_analysis_time_edit.setDisplayFormat("HH:mm")
        self.postpone_analysis_time_edit.setToolTip("Time of day to analyze postponement patterns")
        self.postpone_analysis_time_edit.setWhatsThis(
            "Time of day when the system analyzes postponement patterns to detect tasks you're repeatedly delaying. "
            "This helps identify blockers and tasks that might need to be broken down."
        )
        postpone_form.addRow("Analysis Time:", self.postpone_analysis_time_edit)

        postpone_group.setLayout(postpone_form)
        layout.addWidget(postpone_group)

        layout.addStretch()
        return tab

    def _create_notifications_tab(self) -> QWidget:
        """Create the notifications preferences tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        # Notification channels group
        channels_group = QGroupBox("Notification Channels")
        channels_layout = QVBoxLayout()

        self.enable_toast_check = QCheckBox("Enable Windows Toast Notifications")
        self.enable_toast_check.setToolTip("Show popup toast notifications (Windows only)")
        self.enable_toast_check.setWhatsThis(
            "Enable Windows toast notifications (popup notifications that appear in the system tray area). "
            "These provide immediate visibility when tasks need attention, even when the app is minimized."
        )
        channels_layout.addWidget(self.enable_toast_check)

        self.enable_inapp_check = QCheckBox("Enable In-App Notification Panel")
        self.enable_inapp_check.setToolTip("Show notifications in the in-app notification panel")
        self.enable_inapp_check.setWhatsThis(
            "Enable the in-app notification panel. This provides a persistent list of notifications "
            "within the application that you can review at any time."
        )
        channels_layout.addWidget(self.enable_inapp_check)

        channels_group.setLayout(channels_layout)
        layout.addWidget(channels_group)

        # Retention group
        retention_group = QGroupBox("Notification Retention")
        retention_form = QFormLayout()

        self.notification_retention_spin = QSpinBox()
        self.notification_retention_spin.setRange(7, 365)
        self.notification_retention_spin.setSuffix(" days")
        self.notification_retention_spin.setToolTip("How long to keep old notifications before deletion")
        self.notification_retention_spin.setWhatsThis(
            "How long to keep old notifications before automatic deletion. Notifications older than "
            "this period will be permanently removed. Range: 7-365 days."
        )
        retention_form.addRow("Retention Period:", self.notification_retention_spin)

        retention_group.setLayout(retention_form)
        layout.addWidget(retention_group)

        layout.addStretch()
        return tab

    def _create_triggers_tab(self) -> QWidget:
        """Create the notification triggers tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        triggers_group = QGroupBox("Event Notifications")
        triggers_layout = QVBoxLayout()

        description = QLabel(
            "Choose which events should generate notifications:"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; margin-bottom: 10px;")
        triggers_layout.addWidget(description)

        self.notify_deferred_check = QCheckBox("Deferred tasks activated")
        self.notify_deferred_check.setToolTip("Notify when deferred tasks become active")
        self.notify_deferred_check.setWhatsThis(
            "When enabled, you'll receive a notification when a deferred task reaches its start date "
            "and becomes active again. This helps ensure you don't forget about postponed tasks."
        )
        triggers_layout.addWidget(self.notify_deferred_check)

        self.notify_delegated_check = QCheckBox("Delegated tasks need follow-up")
        self.notify_delegated_check.setToolTip("Notify for delegated tasks reaching follow-up date")
        self.notify_delegated_check.setWhatsThis(
            "When enabled, you'll be notified when delegated tasks reach their follow-up date, "
            "reminding you to check on progress with the person you delegated to."
        )
        triggers_layout.addWidget(self.notify_delegated_check)

        self.notify_someday_check = QCheckBox("Someday/Maybe review time")
        self.notify_someday_check.setToolTip("Notify when it's time to review Someday tasks")
        self.notify_someday_check.setWhatsThis(
            "When enabled, you'll receive periodic reminders to review your Someday/Maybe tasks "
            "to see if any have become actionable or should be promoted to active tasks."
        )
        triggers_layout.addWidget(self.notify_someday_check)

        self.notify_postpone_check = QCheckBox("Postponement patterns detected")
        self.notify_postpone_check.setToolTip("Notify when postponement patterns are detected")
        self.notify_postpone_check.setWhatsThis(
            "When enabled, you'll be notified if the system detects you're repeatedly postponing "
            "the same task. This helps identify blockers or tasks that should be broken down."
        )
        triggers_layout.addWidget(self.notify_postpone_check)

        triggers_group.setLayout(triggers_layout)
        layout.addWidget(triggers_group)

        layout.addStretch()
        return tab

    def _create_intervention_tab(self) -> QWidget:
        """Create the intervention thresholds tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        intervention_group = QGroupBox("Postponement Intervention")
        intervention_form = QFormLayout()

        description = QLabel(
            "Configure when to intervene on repeatedly postponed tasks:"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; margin-bottom: 10px;")
        intervention_form.addRow(description)

        self.postpone_threshold_spin = QSpinBox()
        self.postpone_threshold_spin.setRange(2, 10)
        self.postpone_threshold_spin.setSuffix(" postponements")
        self.postpone_threshold_spin.setToolTip("Number of postponements before intervention is triggered")
        self.postpone_threshold_spin.setWhatsThis(
            "How many times you can postpone the same task before the system suggests an intervention. "
            "When this threshold is reached, you'll be prompted to identify blockers or break down the task. "
            "Range: 2-10 postponements."
        )
        intervention_form.addRow("Intervention Threshold:", self.postpone_threshold_spin)

        self.postpone_pattern_days_spin = QSpinBox()
        self.postpone_pattern_days_spin.setRange(3, 14)
        self.postpone_pattern_days_spin.setSuffix(" days")
        self.postpone_pattern_days_spin.setToolTip("Time window for detecting postponement patterns")
        self.postpone_pattern_days_spin.setWhatsThis(
            "The time window for detecting postponement patterns. Postponements within this many days "
            "are counted together. Shorter windows detect patterns faster. Range: 3-14 days."
        )
        intervention_form.addRow("Pattern Detection Window:", self.postpone_pattern_days_spin)

        intervention_group.setLayout(intervention_form)
        layout.addWidget(intervention_group)

        layout.addStretch()
        return tab

    def _create_theme_tab(self) -> QWidget:
        """Create the theme settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        # Theme selection group
        theme_group = QGroupBox("Appearance")
        theme_form = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System Default"])
        self.theme_combo.setToolTip("Select application theme")
        self.theme_combo.setWhatsThis(
            "Select the visual theme for the application. Choose Light, Dark, or System Default "
            "(which follows your operating system theme setting)."
        )
        theme_form.addRow("Theme:", self.theme_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 16)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setToolTip("Base font size for the application")
        self.font_size_spin.setWhatsThis(
            "Set the base font size for the application interface. This affects the readability "
            "of all text in the application. Range: 8-16 points."
        )
        theme_form.addRow("Font Size:", self.font_size_spin)

        theme_group.setLayout(theme_form)
        layout.addWidget(theme_group)

        # Info label
        info_label = QLabel(
            "Theme changes will be applied immediately when you save settings."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-top: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return tab

    def _create_advanced_tab(self) -> QWidget:
        """Create the advanced settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        # Warning label
        warning_label = QLabel(
            "⚠️ Only change these settings if you understand the Elo comparison system."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #ff6600; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(warning_label)

        # Elo system parameters
        elo_group = QGroupBox("Elo System Parameters")
        elo_form = QFormLayout()

        self.k_factor_new_spin = QSpinBox()
        self.k_factor_new_spin.setRange(16, 64)
        self.k_factor_new_spin.setToolTip(
            "Sensitivity for first 10 comparisons (higher = larger rating changes)"
        )
        self.k_factor_new_spin.setWhatsThis(
            "The K-factor controls how much a task's Elo rating changes after each comparison. "
            "For new tasks (fewer than 10 comparisons), a higher K-factor means faster learning "
            "of the task's true priority. Default: 32. Range: 16-64."
        )
        elo_form.addRow("K-factor (new tasks):", self.k_factor_new_spin)

        self.k_factor_spin = QSpinBox()
        self.k_factor_spin.setRange(8, 32)
        self.k_factor_spin.setToolTip(
            "Sensitivity after 10 comparisons (lower = more stable ratings)"
        )
        self.k_factor_spin.setWhatsThis(
            "The K-factor for established tasks (10+ comparisons). A lower value makes ratings "
            "more stable and less affected by individual comparisons. Default: 16. Range: 8-32."
        )
        elo_form.addRow("K-factor (established):", self.k_factor_spin)

        self.new_task_threshold_spin = QSpinBox()
        self.new_task_threshold_spin.setRange(5, 20)
        self.new_task_threshold_spin.setToolTip(
            "Number of comparisons before switching to base K-factor"
        )
        self.new_task_threshold_spin.setWhatsThis(
            "How many comparisons a task needs before it's considered 'established' and uses "
            "the lower K-factor. More comparisons mean more data before stabilizing. "
            "Default: 10. Range: 5-20."
        )
        elo_form.addRow("New task threshold:", self.new_task_threshold_spin)

        self.score_epsilon_spin = QDoubleSpinBox()
        self.score_epsilon_spin.setRange(0.001, 0.1)
        self.score_epsilon_spin.setDecimals(3)
        self.score_epsilon_spin.setSingleStep(0.001)
        self.score_epsilon_spin.setToolTip(
            "Threshold for tie detection (smaller = stricter equality)"
        )
        self.score_epsilon_spin.setWhatsThis(
            "The threshold for detecting tied importance scores. Tasks within this difference "
            "are considered tied and require comparison. Smaller values mean stricter equality. "
            "Default: 0.01. Range: 0.001-0.1."
        )
        elo_form.addRow("Score epsilon:", self.score_epsilon_spin)

        elo_group.setLayout(elo_form)
        layout.addWidget(elo_group)

        # Elo band ranges (read-only)
        band_group = QGroupBox("Elo Band Ranges")
        band_layout = QVBoxLayout()

        band_label = QLabel(
            "High Priority   (base=3): [2.0, 3.0]\n"
            "Medium Priority (base=2): [1.0, 2.0]\n"
            "Low Priority    (base=1): [0.0, 1.0]"
        )
        band_label.setStyleSheet("font-family: monospace; color: #666;")
        band_layout.addWidget(band_label)

        band_group.setLayout(band_layout)
        layout.addWidget(band_group)

        # Reset defaults button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_advanced_defaults)
        layout.addWidget(reset_button)

        # Onboarding group
        onboarding_group = QGroupBox("Onboarding")
        onboarding_layout = QVBoxLayout()

        onboarding_description = QLabel(
            "Re-run the welcome wizard to see the introduction and create your first task again."
        )
        onboarding_description.setWordWrap(True)
        onboarding_description.setStyleSheet("color: #666; margin-bottom: 10px;")
        onboarding_layout.addWidget(onboarding_description)

        self.rerun_wizard_button = QPushButton("Re-run Welcome Wizard")
        self.rerun_wizard_button.clicked.connect(self._rerun_welcome_wizard)
        onboarding_layout.addWidget(self.rerun_wizard_button)

        onboarding_group.setLayout(onboarding_layout)
        layout.addWidget(onboarding_group)

        layout.addStretch()
        return tab

    def _load_settings(self):
        """Load current settings from database."""
        # Resurfacing tab
        self.deferred_check_hours_spin.setValue(
            self.settings_dao.get_int('deferred_check_hours', default=1)
        )

        delegated_time_str = self.settings_dao.get_str('delegated_check_time', default='09:00')
        self.delegated_check_time_edit.setTime(self._parse_time_string(delegated_time_str))

        self.someday_review_days_spin.setValue(
            self.settings_dao.get_int('someday_review_days', default=7)
        )

        someday_time_str = self.settings_dao.get_str('someday_review_time', default='18:00')
        self.someday_review_time_edit.setTime(self._parse_time_string(someday_time_str))

        postpone_time_str = self.settings_dao.get_str('postpone_analysis_time', default='18:00')
        self.postpone_analysis_time_edit.setTime(self._parse_time_string(postpone_time_str))

        # Notifications tab
        self.enable_toast_check.setChecked(
            self.settings_dao.get_bool('enable_toast_notifications', default=True)
        )

        self.enable_inapp_check.setChecked(
            self.settings_dao.get_bool('enable_inapp_notifications', default=True)
        )

        self.notification_retention_spin.setValue(
            self.settings_dao.get_int('notification_retention_days', default=30)
        )

        # Triggers tab
        self.notify_deferred_check.setChecked(
            self.settings_dao.get_bool('notify_deferred_activation', default=True)
        )

        self.notify_delegated_check.setChecked(
            self.settings_dao.get_bool('notify_delegated_followup', default=True)
        )

        self.notify_someday_check.setChecked(
            self.settings_dao.get_bool('notify_someday_review', default=True)
        )

        self.notify_postpone_check.setChecked(
            self.settings_dao.get_bool('notify_postpone_intervention', default=True)
        )

        # Intervention tab
        self.postpone_threshold_spin.setValue(
            self.settings_dao.get_int('postpone_intervention_threshold', default=3)
        )

        self.postpone_pattern_days_spin.setValue(
            self.settings_dao.get_int('postpone_pattern_days', default=7)
        )

        # Theme tab
        theme = self.settings_dao.get_str('theme', default='light')
        theme_index = {"light": 0, "dark": 1, "system": 2}.get(theme, 0)
        self.theme_combo.setCurrentIndex(theme_index)

        self.font_size_spin.setValue(
            self.settings_dao.get_int('font_size', default=10)
        )

        # Advanced tab
        self.k_factor_new_spin.setValue(
            self.settings_dao.get_int('elo_k_factor_new', default=32)
        )

        self.k_factor_spin.setValue(
            self.settings_dao.get_int('elo_k_factor', default=16)
        )

        self.new_task_threshold_spin.setValue(
            self.settings_dao.get_int('elo_new_task_threshold', default=10)
        )

        self.score_epsilon_spin.setValue(
            self.settings_dao.get_float('score_epsilon', default=0.01)
        )

    def _save_settings_internal(self):
        """Internal method to save settings to database without UI feedback."""
        # Resurfacing settings
        self.settings_dao.set(
            'deferred_check_hours',
            self.deferred_check_hours_spin.value(),
            'integer',
            'Hours between deferred task checks'
        )

        self.settings_dao.set(
            'delegated_check_time',
            self.delegated_check_time_edit.time().toString("HH:mm"),
            'string',
            'Time of day to check delegated tasks'
        )

        self.settings_dao.set(
            'someday_review_days',
            self.someday_review_days_spin.value(),
            'integer',
            'Days between Someday/Maybe reviews'
        )

        self.settings_dao.set(
            'someday_review_time',
            self.someday_review_time_edit.time().toString("HH:mm"),
            'string',
            'Preferred time for someday review'
        )

        self.settings_dao.set(
            'postpone_analysis_time',
            self.postpone_analysis_time_edit.time().toString("HH:mm"),
            'string',
            'Time of day to analyze postponement patterns'
        )

        # Notification settings
        self.settings_dao.set(
            'enable_toast_notifications',
            self.enable_toast_check.isChecked(),
            'boolean',
            'Enable Windows toast notifications'
        )

        self.settings_dao.set(
            'enable_inapp_notifications',
            self.enable_inapp_check.isChecked(),
            'boolean',
            'Enable in-app notification panel'
        )

        self.settings_dao.set(
            'notification_retention_days',
            self.notification_retention_spin.value(),
            'integer',
            'Days to keep old notifications'
        )

        # Trigger settings
        self.settings_dao.set(
            'notify_deferred_activation',
            self.notify_deferred_check.isChecked(),
            'boolean',
            'Notify when deferred tasks activate'
        )

        self.settings_dao.set(
            'notify_delegated_followup',
            self.notify_delegated_check.isChecked(),
            'boolean',
            'Notify for delegated follow-ups'
        )

        self.settings_dao.set(
            'notify_someday_review',
            self.notify_someday_check.isChecked(),
            'boolean',
            'Notify for someday reviews'
        )

        self.settings_dao.set(
            'notify_postpone_intervention',
            self.notify_postpone_check.isChecked(),
            'boolean',
            'Notify for postponement patterns'
        )

        # Intervention settings
        self.settings_dao.set(
            'postpone_intervention_threshold',
            self.postpone_threshold_spin.value(),
            'integer',
            'Postponements before intervention'
        )

        self.settings_dao.set(
            'postpone_pattern_days',
            self.postpone_pattern_days_spin.value(),
            'integer',
            'Days window for pattern detection'
        )

        # Theme settings
        theme_map = {0: 'light', 1: 'dark', 2: 'system'}
        theme_value = theme_map.get(self.theme_combo.currentIndex(), 'light')
        self.settings_dao.set(
            'theme',
            theme_value,
            'string',
            'UI theme (light/dark/system)'
        )

        self.settings_dao.set(
            'font_size',
            self.font_size_spin.value(),
            'integer',
            'Base font size in points'
        )

        # Advanced settings
        self.settings_dao.set(
            'elo_k_factor_new',
            self.k_factor_new_spin.value(),
            'integer',
            'K-factor for new tasks'
        )

        self.settings_dao.set(
            'elo_k_factor',
            self.k_factor_spin.value(),
            'integer',
            'K-factor for established tasks'
        )

        self.settings_dao.set(
            'elo_new_task_threshold',
            self.new_task_threshold_spin.value(),
            'integer',
            'Comparisons before base K-factor'
        )

        self.settings_dao.set(
            'score_epsilon',
            self.score_epsilon_spin.value(),
            'float',
            'Threshold for tie detection'
        )

    def _save_settings(self):
        """Save settings to database."""
        try:
            self._save_settings_internal()

            # Emit signal and close
            self.settings_saved.emit()

            MessageBox.information(
                self,
                self.db_connection,
                "Settings Saved",
                "Settings have been saved successfully.\n\n"
                "Changes to resurfacing intervals will take effect on the next scheduled run."
            )

            self.accept()

        except Exception as e:
            MessageBox.critical(
                self,
                self.db_connection,
                "Error Saving Settings",
                f"An error occurred while saving settings:\n\n{str(e)}"
            )

    def _parse_time_string(self, time_str: str) -> QTime:
        """Parse time string to QTime object."""
        try:
            parts = time_str.split(':')
            return QTime(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return QTime(9, 0)  # Default to 9:00 AM

    def _reset_advanced_defaults(self):
        """Reset advanced settings to default values."""
        self.k_factor_new_spin.setValue(32)
        self.k_factor_spin.setValue(16)
        self.new_task_threshold_spin.setValue(10)
        self.score_epsilon_spin.setValue(0.01)

    def _rerun_welcome_wizard(self):
        """Handle re-running the welcome wizard."""
        # Ask for confirmation
        reply = MessageBox.question(
            self,
            self.db_connection,
            "Re-run Welcome Wizard",
            "This will save your current settings, reset your onboarding status, "
            "and show the welcome wizard again.\n\n"
            "Are you sure you want to continue?"
        )

        if reply == QMessageBox.Yes:
            # Save current settings first (without showing confirmation message)
            try:
                self._save_settings_internal()
            except Exception as e:
                MessageBox.critical(
                    self,
                    self.db_connection,
                    "Error Saving Settings",
                    f"An error occurred while saving settings:\n\n{str(e)}"
                )
                return

            # Reset onboarding status
            from ..services.first_run_detector import FirstRunDetector
            first_run_detector = FirstRunDetector(self.db_connection)
            first_run_detector.reset_onboarding()

            # Emit signals to main window
            self.settings_saved.emit()
            self.rerun_wizard_requested.emit()

            # Close the settings dialog
            self.accept()

    def _create_test_aliases(self):
        """Create alias attributes for test compatibility."""
        # Resurfacing tab aliases
        self.deferred_check_interval = self.deferred_check_hours_spin
        self.delegated_check_interval = self.delegated_check_time_edit
        self.someday_check_interval = self.someday_review_days_spin

        # Notifications tab aliases
        self.notifications_enabled = self.enable_toast_check
        self.toast_notifications_enabled = self.enable_toast_check

        # Intervention tab aliases
        self.postpone_count_threshold = self.postpone_threshold_spin
        self.postpone_window_days = self.postpone_pattern_days_spin

        # Theme tab aliases
        self.theme_selector = self.theme_combo
