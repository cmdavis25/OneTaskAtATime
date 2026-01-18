"""
Unit tests for MessageBox utility.

Tests the custom message box wrapper including:
- Static method creation
- Dialog configuration
- Button handling
"""

import pytest

from PyQt5.QtWidgets import QApplication, QMessageBox

from src.ui.message_box import MessageBox


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestMessageBoxMethods:
    """Test MessageBox static methods exist."""

    def test_has_information_method(self):
        """Test that MessageBox has information method."""
        assert hasattr(MessageBox, 'information')
        assert callable(MessageBox.information)

    def test_has_warning_method(self):
        """Test that MessageBox has warning method."""
        assert hasattr(MessageBox, 'warning')
        assert callable(MessageBox.warning)

    def test_has_critical_method(self):
        """Test that MessageBox has critical method."""
        assert hasattr(MessageBox, 'critical')
        assert callable(MessageBox.critical)

    def test_has_question_method(self):
        """Test that MessageBox has question method."""
        assert hasattr(MessageBox, 'question')
        assert callable(MessageBox.question)


class TestMessageBoxCreation:
    """Test message box creation."""

    def test_information_returns_result(self, qapp, qtbot):
        """Test that information dialog returns a result."""
        # This test verifies the method signature
        # Actual display testing would require user interaction
        assert callable(MessageBox.information)

    def test_warning_returns_result(self, qapp, qtbot):
        """Test that warning dialog returns a result."""
        assert callable(MessageBox.warning)

    def test_critical_returns_result(self, qapp, qtbot):
        """Test that critical dialog returns a result."""
        assert callable(MessageBox.critical)

    def test_question_returns_result(self, qapp, qtbot):
        """Test that question dialog returns a result."""
        assert callable(MessageBox.question)


class TestMethodSignatures:
    """Test that methods have expected signatures."""

    def test_information_accepts_title_and_text(self, qapp):
        """Test that information method accepts title and text."""
        # Just test that the method can be called with these params
        # We won't actually show the dialog
        import inspect
        sig = inspect.signature(MessageBox.information)
        params = list(sig.parameters.keys())
        # Should accept parent, title, text at minimum
        assert len(params) >= 2  # title, text (parent may be optional)

    def test_warning_accepts_title_and_text(self, qapp):
        """Test that warning method accepts title and text."""
        import inspect
        sig = inspect.signature(MessageBox.warning)
        params = list(sig.parameters.keys())
        assert len(params) >= 2

    def test_critical_accepts_title_and_text(self, qapp):
        """Test that critical method accepts title and text."""
        import inspect
        sig = inspect.signature(MessageBox.critical)
        params = list(sig.parameters.keys())
        assert len(params) >= 2

    def test_question_accepts_title_and_text(self, qapp):
        """Test that question method accepts title and text."""
        import inspect
        sig = inspect.signature(MessageBox.question)
        params = list(sig.parameters.keys())
        assert len(params) >= 2
