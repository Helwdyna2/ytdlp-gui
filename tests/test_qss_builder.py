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


# ------------------------------------------------------------------
# Button-role property selectors
# ------------------------------------------------------------------

def test_build_qss_includes_button_role_selectors():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    assert 'QPushButton[button_role="primary"]' in qss
    assert 'QPushButton[button_role="secondary"]' in qss
    assert 'QPushButton[button_role="destructive"]' in qss


def test_build_qss_button_role_primary_styling():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO, FONT_HEADLINE

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO, font_headline=FONT_HEADLINE)
    # Primary has gradient with primary color and text-on-cyan text
    assert DARK_TOKENS["primary"] in qss
    assert DARK_TOKENS["text-on-cyan"] in qss
    # Primary uses 8px 24px padding
    assert "8px 24px" in qss


def test_build_qss_button_role_secondary_styling():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO, FONT_HEADLINE

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO, font_headline=FONT_HEADLINE)
    # Secondary uses 6px 16px padding
    assert "6px 16px" in qss


def test_build_qss_button_role_destructive_styling():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    # Destructive uses red text
    assert DARK_TOKENS["red"] in qss


# ------------------------------------------------------------------
# Focus-ring contract
# ------------------------------------------------------------------

def test_build_qss_focus_ring_matrix():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO, FONT_HEADLINE

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO, font_headline=FONT_HEADLINE)

    focus_selectors = [
        "QPushButton:focus",
        "QComboBox:focus",
        "QLineEdit:focus",
        "QTextEdit:focus",
        "QPlainTextEdit:focus",
        "QSpinBox:focus",
        "QDoubleSpinBox:focus",
    ]
    for sel in focus_selectors:
        assert sel in qss, f"Missing focus selector: {sel}"


def test_build_qss_focus_ring_treatment():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO, FONT_HEADLINE

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO, font_headline=FONT_HEADLINE)
    # Focus ring uses 1px border with border-focus color
    assert f'1px solid {DARK_TOKENS["border-focus"]}' in qss


# ------------------------------------------------------------------
# Typography selectors
# ------------------------------------------------------------------

def test_build_qss_typography_selectors():
    from src.ui.theme.qss_builder import build_qss
    from src.ui.theme.tokens import DARK_TOKENS, FONT_BODY, FONT_MONO

    qss = build_qss(DARK_TOKENS, FONT_BODY, FONT_MONO)
    # Page title: 18px, weight 600
    assert "18px" in qss
    assert "600" in qss
    # Body: 12px
    assert "12px" in qss
    # Section header: 9px uppercase
    assert "9px" in qss
    assert "uppercase" in qss
