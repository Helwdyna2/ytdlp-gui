"""Helpers for extracting hostnames from URLs."""

from typing import List
from urllib.parse import urlparse


def extract_hostnames(urls: List[str]) -> List[str]:
    """Extract hostnames from URLs, preserving order and uniqueness."""
    seen = set()
    hostnames: List[str] = []

    for url in urls:
        parsed = urlparse(url)
        hostname = parsed.hostname or parsed.netloc
        if not hostname:
            continue

        hostname = hostname.lower()
        if hostname in seen:
            continue

        seen.add(hostname)
        hostnames.append(hostname)

    return hostnames
