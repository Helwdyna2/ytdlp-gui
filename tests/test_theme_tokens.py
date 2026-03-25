"""Tests for theme token system."""

import pytest


def test_dark_tokens_has_all_required_keys():
    from src.ui.theme.tokens import DARK_TOKENS, REQUIRED_TOKEN_KEYS

    for key in REQUIRED_TOKEN_KEYS:
        assert key in DARK_TOKENS, f"DARK_TOKENS missing key: {key}"


def test_light_tokens_has_all_required_keys():
    from src.ui.theme.tokens import LIGHT_TOKENS, REQUIRED_TOKEN_KEYS

    for key in REQUIRED_TOKEN_KEYS:
        assert key in LIGHT_TOKENS, f"LIGHT_TOKENS missing key: {key}"


def test_dark_and_light_have_same_keys():
    from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS

    assert set(DARK_TOKENS.keys()) == set(LIGHT_TOKENS.keys()), (
        f"Key mismatch. Dark-only: {set(DARK_TOKENS.keys()) - set(LIGHT_TOKENS.keys())}, "
        f"Light-only: {set(LIGHT_TOKENS.keys()) - set(DARK_TOKENS.keys())}"
    )


def test_tokens_values_are_strings():
    from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS

    for name, tokens in [("DARK", DARK_TOKENS), ("LIGHT", LIGHT_TOKENS)]:
        for key, val in tokens.items():
            assert isinstance(val, str), (
                f"{name}_TOKENS['{key}'] is {type(val)}, expected str"
            )


def test_font_stacks_defined():
    from src.ui.theme.tokens import FONT_DISPLAY, FONT_BODY

    assert "Segoe UI" in FONT_BODY
    assert "Helvetica" in FONT_BODY
    assert FONT_DISPLAY == FONT_BODY


def test_workspace_tokens_include_shell_keys():
    from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS

    required = {
        "surface-app",
        "surface-panel",
        "surface-canvas",
        "accent-primary",
        "accent-muted",
        "text-strong",
    }

    assert required.issubset(DARK_TOKENS)
    assert required.issubset(LIGHT_TOKENS)


# ------------------------------------------------------------------
# Spec-aligned dark token values
# ------------------------------------------------------------------

def test_dark_token_surfaces():
    from src.ui.theme.tokens import DARK_TOKENS

    assert DARK_TOKENS["bg-void"] == "#09090b"
    assert DARK_TOKENS["bg-surface"] == "#0f0f12"
    assert DARK_TOKENS["bg-panel"] == "#18181b"
    assert DARK_TOKENS["bg-cell"] == "#1c1c21"
    assert DARK_TOKENS["bg-hover"] == "#27272a"


def test_dark_token_text():
    from src.ui.theme.tokens import DARK_TOKENS

    assert DARK_TOKENS["text-primary"] == "#a1a1aa"
    assert DARK_TOKENS["text-muted"] == "#8a8a94"
    assert DARK_TOKENS["text-bright"] == "#fafafa"


def test_dark_token_status_colors():
    from src.ui.theme.tokens import DARK_TOKENS

    assert DARK_TOKENS["cyan"] == "#3b82f6"
    assert DARK_TOKENS["accent-primary"] == "#fafafa"


# ------------------------------------------------------------------
# Spec-aligned light token values
# ------------------------------------------------------------------

def test_light_token_surfaces():
    from src.ui.theme.tokens import LIGHT_TOKENS

    assert LIGHT_TOKENS["bg-void"] == "#fafafa"
    assert LIGHT_TOKENS["bg-surface"] == "#f4f4f5"
    assert LIGHT_TOKENS["bg-panel"] == "#ffffff"


def test_light_token_borders():
    from src.ui.theme.tokens import LIGHT_TOKENS

    assert LIGHT_TOKENS["border-hard"] == "#d4d4d8"


def test_light_token_text():
    from src.ui.theme.tokens import LIGHT_TOKENS

    assert LIGHT_TOKENS["text-primary"] == "#3f3f46"
    assert LIGHT_TOKENS["text-muted"] == "#71717a"


def test_light_token_status_colors():
    from src.ui.theme.tokens import LIGHT_TOKENS

    assert LIGHT_TOKENS["cyan"] == "#2563eb"
    assert LIGHT_TOKENS["red"] == "#dc2626"
    assert LIGHT_TOKENS["accent-primary"] == "#18181b"


# ------------------------------------------------------------------
# Radius contract
# ------------------------------------------------------------------

def test_radius_r_l_is_6px():
    from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS

    assert DARK_TOKENS["r-l"] == "6px"
    assert LIGHT_TOKENS["r-l"] == "6px"


# ------------------------------------------------------------------
# Typography contract
# ------------------------------------------------------------------

def test_typography_contract():
    from src.ui.theme.tokens import FONT_BODY

    # system body font stack
    assert "Segoe UI" in FONT_BODY
    assert "Helvetica Neue" in FONT_BODY
