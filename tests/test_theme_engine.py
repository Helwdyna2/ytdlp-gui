"""Tests for ThemeEngine singleton."""

import pytest
import sys

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset ThemeEngine singleton between tests."""
    from src.ui.theme.theme_engine import ThemeEngine

    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_theme_engine_singleton(qapp):
    from src.ui.theme.theme_engine import ThemeEngine

    engine1 = ThemeEngine.instance()
    engine2 = ThemeEngine.instance()
    assert engine1 is engine2


def test_theme_engine_default_is_dark(qapp):
    from src.ui.theme.theme_engine import ThemeEngine

    engine = ThemeEngine.instance()
    assert engine.current_theme == "dark"


def test_theme_engine_toggle(qapp):
    from src.ui.theme.theme_engine import ThemeEngine

    engine = ThemeEngine.instance()
    engine.toggle_theme()
    assert engine.current_theme == "light"
    engine.toggle_theme()
    assert engine.current_theme == "dark"


def test_theme_engine_apply_produces_qss(qapp):
    from src.ui.theme.theme_engine import ThemeEngine
    from src.ui.theme.tokens import DARK_TOKENS

    engine = ThemeEngine.instance()
    engine.apply_theme(qapp)
    qss = qapp.styleSheet()
    assert len(qss) > 100
    assert DARK_TOKENS["bg-void"] in qss


def test_theme_engine_emits_signal(qapp):
    from src.ui.theme.theme_engine import ThemeEngine

    engine = ThemeEngine.instance()
    received = []
    engine.theme_changed.connect(lambda t: received.append(t))
    engine.set_theme("light")
    assert received == ["light"]


def test_theme_engine_no_signal_if_same_theme(qapp):
    from src.ui.theme.theme_engine import ThemeEngine

    engine = ThemeEngine.instance()
    received = []
    engine.theme_changed.connect(lambda t: received.append(t))
    engine.set_theme("dark")  # Already dark, should not emit
    assert received == []


def test_theme_engine_get_color(qapp):
    from src.ui.theme.theme_engine import ThemeEngine
    from src.ui.theme.tokens import DARK_TOKENS

    engine = ThemeEngine.instance()
    assert engine.get_color("cyan") == DARK_TOKENS["cyan"]
    assert engine.get_color("bg-void") == DARK_TOKENS["bg-void"]


def test_theme_engine_get_color_light(qapp):
    from src.ui.theme.theme_engine import ThemeEngine
    from src.ui.theme.tokens import LIGHT_TOKENS

    engine = ThemeEngine.instance()
    engine.set_theme("light")
    assert engine.get_color("bg-void") == LIGHT_TOKENS["bg-void"]


def test_theme_engine_invalid_theme(qapp):
    from src.ui.theme.theme_engine import ThemeEngine

    engine = ThemeEngine.instance()
    with pytest.raises(ValueError):
        engine.set_theme("blue")
