"""File parsing for URL extraction from text files."""

import logging
from pathlib import Path
from typing import List, Optional

from .url_parser import UrlParser

logger = logging.getLogger(__name__)


class FileParser:
    """
    Parse .txt and .md files to extract URLs.

    Handles encoding detection and file reading.
    """

    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.text', '.markdown'}

    # Common encodings to try
    ENCODINGS = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']

    def __init__(self):
        self.url_parser = UrlParser()

    def is_supported(self, file_path: str) -> bool:
        """
        Check if file extension is supported.

        Args:
            file_path: Path to file.

        Returns:
            True if file extension is supported.
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def parse_file(self, file_path: str) -> List[str]:
        """
        Parse a file and extract URLs.

        Args:
            file_path: Path to file to parse.

        Returns:
            List of unique, sorted URLs found in file.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If file type is not supported.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.is_supported(file_path):
            raise ValueError(f"Unsupported file type: {path.suffix}")

        # Read file content
        content = self._read_file(path)

        if content is None:
            logger.error(f"Failed to read file: {file_path}")
            return []

        # Extract and process URLs
        return self.url_parser.process_text(content)

    def _read_file(self, path: Path) -> Optional[str]:
        """
        Read file content with encoding detection.

        Tries multiple encodings until one works.

        Args:
            path: Path to file.

        Returns:
            File content as string, or None if reading failed.
        """
        for encoding in self.ENCODINGS:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading file {path}: {e}")
                return None

        logger.error(f"Could not decode file {path} with any known encoding")
        return None

    def parse_multiple_files(self, file_paths: List[str]) -> List[str]:
        """
        Parse multiple files and combine URLs.

        Args:
            file_paths: List of file paths to parse.

        Returns:
            Combined list of unique, sorted URLs from all files.
        """
        all_urls = []

        for file_path in file_paths:
            try:
                urls = self.parse_file(file_path)
                all_urls.extend(urls)
                logger.info(f"Extracted {len(urls)} URLs from {file_path}")
            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}")

        # Deduplicate and sort combined results
        return self.url_parser.deduplicate_and_sort(all_urls)

    def get_url_count(self, file_path: str) -> int:
        """
        Get count of URLs in file without fully parsing.

        Args:
            file_path: Path to file.

        Returns:
            Number of URLs found, or 0 on error.
        """
        try:
            urls = self.parse_file(file_path)
            return len(urls)
        except Exception:
            return 0
