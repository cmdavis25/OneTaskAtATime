"""
UI tests for WelcomeWizard.

Tests onboarding wizard flow.
"""

import pytest
import sqlite3
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QDate

from src.ui.welcome_wizard import WelcomeWizard


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app



@pytest.fixture
def wizard(qapp, db_connection):
    """Create WelcomeWizard instance."""
    wizard = WelcomeWizard(db_connection)
    yield wizard
    wizard.close()


def test_wizard_creation(wizard):
    """Test that wizard is created successfully."""
    assert wizard is not None
    assert wizard.windowTitle() == "Welcome to OneTaskAtATime"


def test_wizard_has_four_pages(wizard):
    """Test that wizard has 4 pages."""
    # Count pages by trying to navigate through them
    page_count = 0
    page_ids = wizard.pageIds()
    assert len(page_ids) == 4


def test_wizard_style(wizard):
    """Test that wizard uses modern style."""
    from PyQt5.QtWidgets import QWizard
    assert wizard.wizardStyle() == QWizard.ModernStyle


def test_wizard_minimum_size(wizard):
    """Test that wizard has minimum size."""
    assert wizard.minimumWidth() == 600
    assert wizard.minimumHeight() == 450


def test_final_page_has_tutorial_checkbox(wizard):
    """Test that final page has tutorial checkbox."""
    final_page = wizard.page(wizard.pageIds()[-1])

    assert hasattr(final_page, 'show_tutorial_checkbox')
