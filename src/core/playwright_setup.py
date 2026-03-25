"""Helpers for Playwright setup and error messaging."""

from typing import Optional


def format_playwright_setup_error(error: Exception) -> Optional[str]:
    """Return a user-friendly message for missing Playwright browsers."""
    message = str(error)
    tokens = [
        "Executable doesn't exist",
        "Looks like Playwright was just installed or updated",
        "playwright install",
    ]
    if any(token in message for token in tokens):
        return (
            "Playwright browsers are not installed. "
            "In the Settings tab, click “Install Playwright Browsers…”, "
            "or run: python -m playwright install chromium firefox webkit"
        )
    return None
