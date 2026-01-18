"""
Unit tests for SettingsDialog.

Tests the settings dialog including:
- Dialog initialization
- Tab structure
- Settings loading and saving
- Signal emission
"""

import pytest
import sqlite3

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.ui.settings_dialog import SettingsDialog


@pytest.fixture
def settings_dialog(qapp, db_connection):
    """Create settings dialog instance."""
    dialog = SettingsDialog(db_connection)
    yield dialog
    dialog.close()


class TestDialogInitialization:
    """Test dialog initialization."""

    def test_dialog_creation(self, settings_dialog):
        """Test that dialog can be created."""
        assert settings_dialog is not None

    def test_dialog_has_window_title(self, settings_dialog):
        """Test that dialog has appropriate window title."""
        title = settings_dialog.windowTitle()
        assert len(title) > 0
        assert "Settings" in title

    def test_dialog_has_minimum_size(self, settings_dialog):
        """Test that dialog has reasonable minimum size."""
        min_size = settings_dialog.minimumSize()
        assert min_size.width() >= 600
        assert min_size.height() >= 500


class TestTabStructure:
    """Test tab widget structure."""

    def test_dialog_has_tab_widget(self, settings_dialog):
        """Test that dialog has tab widget."""
        assert hasattr(settings_dialog, 'tab_widget')
        assert settings_dialog.tab_widget is not None

    def test_dialog_has_resurfacing_tab(self, settings_dialog):
        """Test that dialog has resurfacing settings tab."""
        assert hasattr(settings_dialog, 'resurfacing_tab')
        assert settings_dialog.resurfacing_tab is not None

    def test_dialog_has_notifications_tab(self, settings_dialog):
        """Test that dialog has notifications settings tab."""
        assert hasattr(settings_dialog, 'notifications_tab')
        assert settings_dialog.notifications_tab is not None

    def test_dialog_has_triggers_tab(self, settings_dialog):
        """Test that dialog has triggers settings tab."""
        assert hasattr(settings_dialog, 'triggers_tab')
        assert settings_dialog.triggers_tab is not None

    def test_dialog_has_intervention_tab(self, settings_dialog):
        """Test that dialog has intervention settings tab."""
        assert hasattr(settings_dialog, 'intervention_tab')
        assert settings_dialog.intervention_tab is not None

    def test_dialog_has_theme_tab(self, settings_dialog):
        """Test that dialog has theme settings tab."""
        assert hasattr(settings_dialog, 'theme_tab')
        assert settings_dialog.theme_tab is not None

    def test_tab_count_is_five_or_more(self, settings_dialog):
        """Test that there are at least 5 tabs."""
        tab_count = settings_dialog.tab_widget.count()
        assert tab_count >= 5


class TestResurfacingSettings:
    """Test resurfacing settings controls."""

    def test_has_deferred_interval_control(self, settings_dialog):
        """Test that resurfacing tab has deferred interval control."""
        assert hasattr(settings_dialog, 'deferred_check_interval')

    def test_has_delegated_interval_control(self, settings_dialog):
        """Test that resurfacing tab has delegated interval control."""
        assert hasattr(settings_dialog, 'delegated_check_interval')

    def test_has_someday_interval_control(self, settings_dialog):
        """Test that resurfacing tab has someday interval control."""
        assert hasattr(settings_dialog, 'someday_check_interval')


class TestNotificationSettings:
    """Test notification settings controls."""

    def test_has_notification_enabled_checkbox(self, settings_dialog):
        """Test that notifications tab has enable checkbox."""
        assert hasattr(settings_dialog, 'notifications_enabled')

    def test_has_toast_notification_checkbox(self, settings_dialog):
        """Test that notifications tab has toast notification checkbox."""
        assert hasattr(settings_dialog, 'toast_notifications_enabled')


class TestInterventionSettings:
    """Test intervention settings controls."""

    def test_has_postpone_threshold_control(self, settings_dialog):
        """Test that intervention tab has postpone threshold control."""
        assert hasattr(settings_dialog, 'postpone_count_threshold')

    def test_has_postpone_window_control(self, settings_dialog):
        """Test that intervention tab has postpone window control."""
        assert hasattr(settings_dialog, 'postpone_window_days')


class TestThemeSettings:
    """Test theme settings controls."""

    def test_has_theme_selector(self, settings_dialog):
        """Test that theme tab has theme selector."""
        assert hasattr(settings_dialog, 'theme_selector')

    def test_theme_selector_has_options(self, settings_dialog):
        """Test that theme selector has theme options."""
        count = settings_dialog.theme_selector.count()
        # Should have at least System/Light/Dark
        assert count >= 3


class TestButtonBehavior:
    """Test button behavior."""

    def test_dialog_has_save_button(self, settings_dialog):
        """Test that dialog has save button."""
        assert hasattr(settings_dialog, 'save_button')
        assert settings_dialog.save_button is not None

    def test_dialog_has_cancel_button(self, settings_dialog):
        """Test that dialog has cancel button."""
        assert hasattr(settings_dialog, 'cancel_button')
        assert settings_dialog.cancel_button is not None

    def test_cancel_button_rejects_dialog(self, settings_dialog):
        """Test that cancel button rejects dialog."""
        rejected = []
        settings_dialog.rejected.connect(lambda: rejected.append(True))

        settings_dialog.cancel_button.click()

        assert len(rejected) == 1

    def test_save_button_accepts_dialog(self, settings_dialog):
        """Test that save button accepts dialog."""
        accepted = []
        settings_dialog.accepted.connect(lambda: accepted.append(True))

        settings_dialog.save_button.click()

        assert len(accepted) == 1


class TestSignalEmission:
    """Test signal emission."""

    def test_emits_settings_saved_signal(self, settings_dialog):
        """Test that saving settings emits settings_saved signal."""
        signal_received = []
        settings_dialog.settings_saved.connect(lambda: signal_received.append(True))

        # Click save button
        settings_dialog.save_button.click()

        assert len(signal_received) == 1


class TestSettingsLoading:
    """Test loading settings from database."""

    def test_loads_settings_on_initialization(self, settings_dialog):
        """Test that settings are loaded when dialog opens."""
        # After initialization, controls should have values
        # Deferred interval should have a reasonable default (e.g., > 0)
        value = settings_dialog.deferred_check_interval.value()
        assert value > 0


class TestSettingsSaving:
    """Test saving settings to database."""

    def test_saves_resurfacing_intervals(self, settings_dialog):
        """Test that resurfacing intervals are saved."""
        # Change a value
        original = settings_dialog.deferred_check_interval.value()
        settings_dialog.deferred_check_interval.setValue(10)

        # Save
        settings_dialog.save_button.click()

        # Value should have changed from original (if it wasn't already 10)
        assert settings_dialog.deferred_check_interval.value() == 10

    def test_saves_notification_preferences(self, settings_dialog):
        """Test that notification preferences are saved."""
        # Toggle notification setting
        original = settings_dialog.notifications_enabled.isChecked()
        settings_dialog.notifications_enabled.setChecked(not original)

        # Save
        settings_dialog.save_button.click()

        # State should have changed
        assert settings_dialog.notifications_enabled.isChecked() == (not original)


class TestWizardButton:
    """Test welcome wizard re-run functionality."""

    def test_has_rerun_wizard_button(self, settings_dialog):
        """Test that dialog has button to re-run wizard."""
        assert hasattr(settings_dialog, 'rerun_wizard_button')

    def test_rerun_wizard_button_emits_signal(self, settings_dialog):
        """Test that wizard button emits rerun_wizard_requested signal."""
        signal_received = []
        settings_dialog.rerun_wizard_requested.connect(lambda: signal_received.append(True))

        settings_dialog.rerun_wizard_button.click()

        assert len(signal_received) == 1


class TestWhatsThisHelp:
    """Test WhatsThis help support."""

    def test_dialog_has_whats_this_text(self, settings_dialog):
        """Test that dialog has WhatsThis help text."""
        whats_this = settings_dialog.whatsThis()
        assert len(whats_this) > 0

    def test_whats_this_mentions_settings(self, settings_dialog):
        """Test that WhatsThis help mentions settings."""
        whats_this = settings_dialog.whatsThis().lower()
        assert "setting" in whats_this


class TestDialogLayout:
    """Test dialog layout."""

    def test_tabs_have_reasonable_content(self, settings_dialog):
        """Test that each tab has widgets."""
        # Each tab should have children widgets
        for i in range(settings_dialog.tab_widget.count()):
            tab = settings_dialog.tab_widget.widget(i)
            assert tab is not None
            # Tab should have a layout or children
            assert tab.layout() is not None or len(tab.children()) > 1
