"""Tests for URL hostname extraction."""

from src.core.url_domains import extract_hostnames


def test_extract_hostnames_dedupes_and_orders():
    urls = [
        "https://www.instagram.com/p/abc/",
        "https://redgifs.com/watch/xyz",
        "https://www.instagram.com/p/def/",
    ]

    hostnames = extract_hostnames(urls)
    assert hostnames == ["www.instagram.com", "redgifs.com"]
