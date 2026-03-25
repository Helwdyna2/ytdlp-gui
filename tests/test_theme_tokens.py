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
