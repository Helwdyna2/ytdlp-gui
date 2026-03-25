"""Helpers for redacting sensitive URL details from logs."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

_URL_PATTERN = re.compile(r"https?://[^\s<>\"')]+")
_TRAILING_PUNCTUATION = ".,;:!?)"


def redact_url(url: str) -> str:
    """Strip query strings, fragments, and credentials while keeping useful host/path context."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return url

    if not parsed.scheme or not parsed.netloc:
        return url

    # Reconstruct netloc without userinfo (user:pass@)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def redact_urls_in_text(text: str) -> str:
    """Redact all HTTP(S) URLs embedded in free-form text."""

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        trimmed = token.rstrip(_TRAILING_PUNCTUATION)
        trailing = token[len(trimmed) :]
        return f"{redact_url(trimmed)}{trailing}"

    return _URL_PATTERN.sub(replace, text)
