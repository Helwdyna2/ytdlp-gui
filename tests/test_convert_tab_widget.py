"""Tests for convert settings persistence behavior."""

import sys

import pytest

pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtCore import Qt


@pytest.fixture(autouse=True)
def reset_singletons(tmp_path):
    from src.services.config_service import ConfigService

    ConfigService.reset_instance()
    ConfigService(config_path=str(tmp_path / "config.json"))
    yield
    ConfigService.reset_instance()


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_conversion_settings_browse_button_has_single_connection(
    qapp, monkeypatch, qtbot
):
    """Repeated saves must not multiply the output browse-button connection."""
    from src.ui.widgets.convert_tab_widget import ConversionSettingsWidget

    monkeypatch.setattr(
        "src.ui.widgets.convert_tab_widget.get_cached_hardware_encoders",
        lambda: [],
    )

    widget = ConversionSettingsWidget()
    qtbot.addWidget(widget)

    for _ in range(3):
        widget._save_settings()

    dialog_calls = []

    def fake_get_existing_directory(*_args, **_kwargs):
        dialog_calls.append("called")
        return ""

    monkeypatch.setattr(
        "src.ui.widgets.convert_tab_widget.QFileDialog.getExistingDirectory",
        fake_get_existing_directory,
    )

    qtbot.mouseClick(
        widget._output_browse_btn,
        Qt.MouseButton.LeftButton,
    )

    assert dialog_calls == ["called"]
