"""URL pattern helpers for Extract URLs feature."""

import re
from typing import Iterable, List, Optional, Set
from urllib.parse import urlparse

INSTAGRAM_REEL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/reel/([^/?#]+)/?",
    re.IGNORECASE,
)
REDGIFS_WATCH_PATTERN = re.compile(
    r"https?://(?:www\.)?redgifs\.com/watch/([^/?#]+)/?",
    re.IGNORECASE,
)


def canonicalize_instagram_reel(url: str) -> Optional[str]:
    """
    Canonicalize an Instagram reel URL.

    Args:
        url: URL to canonicalize.

    Returns:
        Canonical reel URL or None if not a match.
    """
    match = INSTAGRAM_REEL_PATTERN.search(url or "")
    if not match:
        return None
    reel_id = match.group(1)
    return f"https://www.instagram.com/reel/{reel_id}/"


def canonicalize_redgifs_watch(url: str) -> Optional[str]:
    """
    Canonicalize a RedGifs watch URL.

    Args:
        url: URL to canonicalize.

    Returns:
        Canonical watch URL or None if not a match.
    """
    match = REDGIFS_WATCH_PATTERN.search(url or "")
    if not match:
        return None
    watch_id = match.group(1)
    return f"https://www.redgifs.com/watch/{watch_id}"


def canonicalize_target_url(url: str) -> Optional[str]:
    """
    Canonicalize a URL if it matches a supported target pattern.

    Args:
        url: URL to canonicalize.

    Returns:
        Canonical URL or None if not supported.
    """
    instagram_url = canonicalize_instagram_reel(url)
    if instagram_url:
        return instagram_url
    return canonicalize_redgifs_watch(url)


def extract_canonical_urls(urls: Iterable[str]) -> List[str]:
    """
    Extract canonical target URLs from an iterable of URLs.

    Args:
        urls: Iterable of URL strings.

    Returns:
        Sorted list of unique canonical URLs.
    """
    found: Set[str] = set()
    for url in urls:
        canonical = canonicalize_target_url(url)
        if canonical:
            found.add(canonical)
    return sorted(found, key=str.lower)


def get_domain_key(url: str) -> str:
    """
    Get domain key for a URL.

    Args:
        url: URL string.

    Returns:
        "instagram", "redgifs", or "other".
    """
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return "other"

    if "instagram.com" in netloc:
        return "instagram"
    if "redgifs.com" in netloc:
        return "redgifs"
    return "other"
