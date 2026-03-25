"""URL extraction, validation, and processing."""

import re
from typing import List
from urllib.parse import urlparse


class UrlParser:
    """
    URL extraction and validation.

    Extracts URLs from raw text, validates format, sorts alphabetically,
    and removes duplicates.
    """

    # Regex pattern to match URLs
    # Matches http:// or https:// followed by valid URL characters
    URL_PATTERN = re.compile(
        r'https?://'  # Protocol
        r'(?:[\w-]+\.)+[\w-]+'  # Domain
        r'(?::\d+)?'  # Optional port
        r'(?:/[^\s<>"\'`\[\]{}|\\^]*)?',  # Path
        re.IGNORECASE
    )

    def parse_text(self, text: str) -> List[str]:
        """
        Extract all URLs from raw text.

        Args:
            text: Raw text that may contain URLs mixed with other content.

        Returns:
            List of extracted URLs (may contain duplicates).
        """
        if not text:
            return []

        # Find all URL matches
        matches = self.URL_PATTERN.findall(text)

        # Clean up URLs (remove trailing punctuation that might have been captured)
        cleaned = []
        for url in matches:
            # Remove common trailing punctuation that shouldn't be part of URL
            url = url.rstrip('.,;:!?\'")>]}')
            if url:
                cleaned.append(url)

        return cleaned

    def validate_url(self, url: str) -> bool:
        """
        Validate that a string is a proper URL.

        Args:
            url: URL string to validate.

        Returns:
            True if valid URL, False otherwise.
        """
        if not url:
            return False

        try:
            result = urlparse(url)
            # Must have scheme (http/https) and netloc (domain)
            return all([
                result.scheme in ('http', 'https'),
                result.netloc,
                '.' in result.netloc  # Basic domain validation
            ])
        except Exception:
            return False

    def deduplicate_and_sort(self, urls: List[str]) -> List[str]:
        """
        Remove duplicates and sort URLs alphabetically.

        Args:
            urls: List of URLs (may contain duplicates).

        Returns:
            Sorted list of unique URLs.
        """
        if not urls:
            return []

        # Use dict to preserve insertion order while deduplicating
        # (in Python 3.7+, dicts maintain insertion order)
        unique = list(dict.fromkeys(urls))

        # Sort alphabetically (case-insensitive)
        return sorted(unique, key=str.lower)

    def process_text(self, text: str) -> List[str]:
        """
        Full processing: extract, validate, deduplicate, and sort URLs.

        Args:
            text: Raw text containing URLs.

        Returns:
            Sorted list of unique, valid URLs.
        """
        # Extract URLs
        urls = self.parse_text(text)

        # Filter to valid URLs only
        valid_urls = [url for url in urls if self.validate_url(url)]

        # Deduplicate and sort
        return self.deduplicate_and_sort(valid_urls)

    def get_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: URL string.

        Returns:
            Domain name or empty string if invalid.
        """
        try:
            result = urlparse(url)
            return result.netloc
        except Exception:
            return ""

    def normalize_url(self, url: str) -> str:
        """
        Normalize URL for comparison.

        Removes trailing slashes, normalizes case for domain, etc.

        Args:
            url: URL to normalize.

        Returns:
            Normalized URL string.
        """
        if not url:
            return ""

        try:
            result = urlparse(url)
            # Lowercase the domain
            netloc = result.netloc.lower()
            # Keep path as-is but remove trailing slash for root paths
            path = result.path
            if path == '/':
                path = ''

            # Reconstruct URL
            normalized = f"{result.scheme}://{netloc}{path}"
            if result.query:
                normalized += f"?{result.query}"

            return normalized
        except Exception:
            return url
