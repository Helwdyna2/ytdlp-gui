"""Tests for QSS stylesheet builder."""

import pytest


def test_build_qss_returns_string():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    result = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    assert isinstance(result, str)
    assert len(result) > 100


def test_build_qss_contains_widget_rules():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    assert "QWidget" in qss
    assert "QPushButton" in qss
    assert "QLineEdit" in qss
    assert "QProgressBar" in qss
    assert "QTableWidget" in qss or "QTableView" in qss
    assert "QGroupBox" in qss
    assert "QScrollBar" in qss
    assert "QComboBox" in qss
    assert "QCheckBox" in qss


def test_build_qss_uses_token_colors():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    assert DARK_TOKENS["bg-void"] in qss
    assert DARK_TOKENS["bg-panel"] in qss
    assert DARK_TOKENS["text-primary"] in qss
    assert DARK_TOKENS["cyan"] in qss


def test_build_qss_light_theme():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import LIGHT_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(LIGHT_TOKENS, FONT_BODY, FONT_MONO)
    assert LIGHT_TOKENS["bg-void"] in qss
    assert LIGHT_TOKENS["text-primary"] in qss


def test_build_qss_includes_object_name_rules():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    assert "btnPrimary" in qss
    assert "btnSecondary" in qss
    assert "btnDestructive" in qss


def test_build_qss_includes_sidebar_selectors():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    assert "QWidget#sidebar" in qss
    assert "QPushButton#sidebarItem" in qss
    assert "QWidget#activityDrawer" in qss
    assert "QWidget#dpanel" in qss
