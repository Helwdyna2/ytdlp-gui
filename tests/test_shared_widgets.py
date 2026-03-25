"""Tests for shared widget copy and button semantics."""
import pytest
import sys

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ------------------------------------------------------------------
# UrlInputWidget
# ------------------------------------------------------------------

def test_url_input_placeholder(qapp):
    from src.ui.widgets.url_input_widget import UrlInputWidget
    w = UrlInputWidget()
    placeholder = w.text_edit.placeholderText()
    assert "Paste video links here" in placeholder
    assert "one per line, or mixed with other text" in placeholder


def test_url_input_helper_copy(qapp):
    from src.ui.widgets.url_input_widget import UrlInputWidget
    w = UrlInputWidget()
    placeholder = w.text_edit.placeholderText()
    assert "Links are automatically extracted, validated, sorted, and deduplicated." in placeholder


def test_url_input_zero_state_label(qapp):
    from src.ui.widgets.url_input_widget import UrlInputWidget
    w = UrlInputWidget()
    assert w.url_count_label.text() == "No links added yet"


def test_url_input_clear_is_secondary(qapp):
    from src.ui.widgets.url_input_widget import UrlInputWidget
    w = UrlInputWidget()
    assert w.clear_btn.property("button_role") == "secondary"


# ------------------------------------------------------------------
# AuthStatusWidget
# ------------------------------------------------------------------

def test_auth_helper_text(qapp):
    from src.ui.widgets.auth_status_widget import AuthStatusWidget
    from PyQt6.QtWidgets import QLabel
    w = AuthStatusWidget()
    labels = [lbl for lbl in w.findChildren(QLabel) if lbl.objectName() == "dimLabel"]
    texts = [lbl.text() for lbl in labels]
    assert any("Sign in using Add URLs first to access private content." in t for t in texts), (
        f"Expected auth helper text, found: {texts}"
    )


# ------------------------------------------------------------------
# FilePickerWidget
# ------------------------------------------------------------------

def test_file_picker_browse_is_secondary(qapp):
    from src.ui.widgets.file_picker_widget import FilePickerWidget
    w = FilePickerWidget()
    assert w.url_file_browse_btn.property("button_role") == "secondary"


def test_file_picker_load_is_primary(qapp):
    from src.ui.widgets.file_picker_widget import FilePickerWidget
    w = FilePickerWidget()
    assert w.url_file_load_btn.property("button_role") == "primary"


# ------------------------------------------------------------------
# OutputConfigWidget
# ------------------------------------------------------------------

def test_output_config_browse_is_secondary(qapp):
    from src.ui.widgets.output_config_widget import OutputConfigWidget
    w = OutputConfigWidget()
    assert w.browse_btn.property("button_role") == "secondary"


# ------------------------------------------------------------------
# DownloadLogWidget
# ------------------------------------------------------------------

def test_download_log_clear_is_secondary(qapp):
    from src.ui.widgets.download_log_widget import DownloadLogWidget
    w = DownloadLogWidget()
    assert w.clear_btn.property("button_role") == "secondary"
