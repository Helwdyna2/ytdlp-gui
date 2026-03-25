"""Match worker using Playwright to search ThePornDB and StashDB."""

import logging
import time
import urllib.parse
from difflib import SequenceMatcher
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from ..data.models import (
    MatchConfig,
    MatchResult,
    MatchStatus,
    SceneMetadata,
    ParsedFilename,
)
from .playwright_setup import format_playwright_setup_error
from ..services.config_service import ConfigService

logger = logging.getLogger(__name__)


class MatchWorker(QThread):
    """
    Worker thread that uses Playwright to search ThePornDB and StashDB.

    Signals:
        progress: (file_index: int, status_message: str) Progress update
        match_found: (file_index: int, match_result: MatchResult) Match found
        login_required: (database_name: str, url: str) User needs to login
        login_completed: (database_name: str) Login confirmed
        error: (file_index: int, error_message: str) Error occurred
        completed: () All matching finished
    """

    progress = pyqtSignal(int, str)
    match_found = pyqtSignal(int, object)  # MatchResult
    login_required = pyqtSignal(str, str)  # db_name, url
    login_completed = pyqtSignal(str)
    error = pyqtSignal(int, str)
    completed = pyqtSignal()

    PORNDB_URL = "https://theporndb.net"
    STASHDB_URL = "https://stashdb.org"

    def __init__(
        self,
        files: List[MatchResult],
        config: MatchConfig,
        cookies_dir: str,
        parent=None,
    ):
        """
        Initialize match worker.

        Args:
            files: List of MatchResult objects to process
            config: MatchConfig with search settings
            cookies_dir: Directory to store browser cookies
            parent: Parent QObject
        """
        super().__init__(parent)
        self._files = files
        self._config = config
        self._cookies_dir = cookies_dir
        self._cancelled = False
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._login_confirmed = False
        self._config_service = ConfigService()

    def run(self) -> None:
        """Main worker loop."""
        try:
            # Import playwright here to avoid import errors if not installed
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                self.error.emit(
                    -1,
                    "Playwright not installed. Please install it with: pip install playwright && playwright install chromium",
                )
                return

            logger.info("Starting match worker")

            # Initialize browser
            self._init_browser()

            if self._cancelled:
                return

            # Check login status for each enabled database
            if self._config.search_porndb:
                if not self._check_logged_in_porndb():
                    self._request_login("ThePornDB", self.PORNDB_URL)
                    if self._cancelled:
                        self.completed.emit()
                        return

            if self._config.search_stashdb:
                if not self._check_logged_in_stashdb():
                    self._request_login("StashDB", self.STASHDB_URL)
                    if self._cancelled:
                        self.completed.emit()
                        return

            # Process each file
            for i, result in enumerate(self._files):
                if self._cancelled:
                    break

                # Skip files that are already skipped
                if result.status == MatchStatus.SKIPPED:
                    continue

                # Update status
                result.status = MatchStatus.SEARCHING
                self.progress.emit(i, f"Searching for: {result.original_filename}")

                # Search databases
                try:
                    matches = self._search_for_file(result)

                    if matches:
                        # Calculate confidence for each match
                        for match in matches:
                            confidence = self._calculate_confidence(
                                result.parsed, match
                            )
                            match.confidence = confidence

                        # Sort by confidence
                        matches.sort(
                            key=lambda m: m.confidence
                            if hasattr(m, "confidence")
                            else 0,
                            reverse=True,
                        )

                        result.matches = matches

                        if len(matches) == 1:
                            # Single match, auto-select
                            result.selected_match = matches[0]
                            result.confidence = (
                                matches[0].confidence
                                if hasattr(matches[0], "confidence")
                                else 0.0
                            )
                            result.status = MatchStatus.MATCHED
                        else:
                            # Multiple matches, user needs to select
                            result.confidence = (
                                matches[0].confidence
                                if hasattr(matches[0], "confidence")
                                else 0.0
                            )
                            result.status = MatchStatus.MULTIPLE_MATCHES
                    else:
                        # No matches found
                        result.status = MatchStatus.NO_MATCH

                    self.match_found.emit(i, result)

                except Exception as e:
                    logger.exception(
                        f"Error searching for {result.original_filename}: {e}"
                    )
                    result.status = MatchStatus.FAILED
                    result.error_message = str(e)
                    self.error.emit(i, str(e))

                # Small delay to avoid rate limiting
                time.sleep(0.5)

            logger.info("Match worker completed")
            self.completed.emit()

        except Exception as e:
            logger.exception(f"Fatal error in match worker: {e}")
            self.error.emit(-1, f"Fatal error: {e}")
        finally:
            self._cleanup()

    def cancel(self) -> None:
        """Cancel the matching process."""
        logger.info("Match worker cancelled")
        self._cancelled = True

    def confirm_login(self, database: str) -> None:
        """
        Called when user confirms they've logged in.

        Args:
            database: Name of database ('ThePornDB' or 'StashDB')
        """
        logger.info(f"Login confirmed for {database}")
        self._login_confirmed = True
        self.login_completed.emit(database)

    def _init_browser(self) -> None:
        """Initialize Playwright with persistent cookies."""
        try:
            from playwright.sync_api import sync_playwright

            logger.info("Initializing Playwright browser")
            self._playwright = sync_playwright().start()

            # Use persistent context to maintain cookies across sessions
            try:
                browser_name = self._config_service.get(
                    "playwright.browser", "chromium"
                )
                engine = getattr(
                    self._playwright, browser_name, self._playwright.chromium
                )
                self._browser = engine.launch_persistent_context(
                    user_data_dir=self._cookies_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                )
            except Exception as e:
                message = format_playwright_setup_error(e)
                if message:
                    self.error.emit(-1, message)
                    self._cancelled = True
                    return
                raise

            self._page = (
                self._browser.pages[0]
                if self._browser.pages
                else self._browser.new_page()
            )

            logger.info("Browser initialized")

        except Exception as e:
            logger.exception(f"Error initializing browser: {e}")
            raise

    def _check_logged_in_porndb(self) -> bool:
        """
        Check if user is logged into ThePornDB.

        Returns:
            True if logged in, False otherwise
        """
        try:
            logger.info("Checking ThePornDB login status")
            self._page.goto(self.PORNDB_URL, wait_until="networkidle", timeout=30000)

            # Look for login button or user profile element
            # If login button exists, user is not logged in
            # Note: Actual selectors may need adjustment based on site structure
            login_button = self._page.query_selector(
                "a[href*='login'], button:has-text('Login')"
            )

            if login_button:
                logger.info("Not logged into ThePornDB")
                return False

            logger.info("Logged into ThePornDB")
            return True

        except Exception as e:
            logger.warning(f"Error checking ThePornDB login: {e}")
            return False

    def _check_logged_in_stashdb(self) -> bool:
        """
        Check if user is logged into StashDB.

        Returns:
            True if logged in, False otherwise
        """
        try:
            logger.info("Checking StashDB login status")
            self._page.goto(self.STASHDB_URL, wait_until="networkidle", timeout=30000)

            # Look for login button or user profile element
            login_button = self._page.query_selector(
                "a[href*='login'], button:has-text('Login')"
            )

            if login_button:
                logger.info("Not logged into StashDB")
                return False

            logger.info("Logged into StashDB")
            return True

        except Exception as e:
            logger.warning(f"Error checking StashDB login: {e}")
            return False

    def _request_login(self, database_name: str, url: str) -> None:
        """
        Request user to login to database.

        Args:
            database_name: Name of database
            url: URL to navigate to
        """
        logger.info(f"Requesting login for {database_name}")

        # Navigate to site
        self._page.goto(url, wait_until="networkidle", timeout=30000)

        # Emit signal and stop processing; login handled via Download tab Auth Status panel
        self.login_required.emit(database_name, url)
        self._cancelled = True

    def _search_for_file(self, result: MatchResult) -> List[SceneMetadata]:
        """
        Search databases for matches to a file.

        Args:
            result: MatchResult with parsed filename

        Returns:
            List of SceneMetadata matches
        """
        all_matches = []

        if not result.parsed or not result.parsed.search_queries:
            logger.warning(f"No search queries for {result.original_filename}")
            return all_matches

        # Search ThePornDB first if enabled and configured
        if self._config.search_porndb and self._config.porndb_first:
            for query in result.parsed.search_queries:
                matches = self._search_porndb(query)
                all_matches.extend(matches)
                if matches:
                    break  # Found results, no need to try more queries

        # Search StashDB if enabled and no matches yet (or not porndb_first)
        if self._config.search_stashdb and not all_matches:
            for query in result.parsed.search_queries:
                matches = self._search_stashdb(query)
                all_matches.extend(matches)
                if matches:
                    break

        # Remove duplicates based on title + studio
        seen = set()
        unique_matches = []
        for match in all_matches:
            key = f"{match.studio.lower()}:{match.title.lower()}"
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        return unique_matches

    def _search_porndb(self, query: str) -> List[SceneMetadata]:
        """
        Search ThePornDB for scenes matching query.

        Args:
            query: Search query string

        Returns:
            List of SceneMetadata matches
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"{self.PORNDB_URL}/scenes?q={encoded_query}"

            logger.info(f"Searching ThePornDB: {query}")
            self._page.goto(url, wait_until="networkidle", timeout=30000)

            results = []

            # Parse scene cards
            # Note: Selectors may need adjustment based on actual site structure
            # This is a placeholder implementation
            cards = self._page.query_selector_all(
                ".scene-card, [class*='scene'], [class*='result']"
            )

            for card in cards[:5]:  # Limit to top 5 results
                try:
                    # Extract data - these selectors are placeholders
                    title_elem = card.query_selector(".title, h2, h3, [class*='title']")
                    studio_elem = card.query_selector(".studio, [class*='studio']")
                    performers_elems = card.query_selector_all(
                        ".performer, [class*='performer']"
                    )

                    if title_elem:
                        title = title_elem.inner_text().strip()
                        studio = (
                            studio_elem.inner_text().strip()
                            if studio_elem
                            else "Unknown"
                        )
                        performers = (
                            [p.inner_text().strip() for p in performers_elems]
                            if performers_elems
                            else []
                        )

                        # Get scene URL
                        link_elem = card.query_selector("a[href*='/scene']")
                        scene_url = (
                            f"{self.PORNDB_URL}{link_elem.get_attribute('href')}"
                            if link_elem
                            else None
                        )

                        # Get thumbnail
                        img_elem = card.query_selector("img")
                        thumbnail = img_elem.get_attribute("src") if img_elem else None

                        results.append(
                            SceneMetadata(
                                title=title,
                                studio=studio,
                                performers=performers,
                                source_database="porndb",
                                source_url=scene_url,
                                thumbnail_url=thumbnail,
                            )
                        )

                except Exception as e:
                    logger.warning(f"Error parsing PornDB card: {e}")
                    continue

            logger.info(f"Found {len(results)} result(s) on ThePornDB")
            return results

        except Exception as e:
            logger.exception(f"Error searching ThePornDB: {e}")
            return []

    def _search_stashdb(self, query: str) -> List[SceneMetadata]:
        """
        Search StashDB for scenes matching query.

        Args:
            query: Search query string

        Returns:
            List of SceneMetadata matches
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"{self.STASHDB_URL}/scenes?query={encoded_query}"

            logger.info(f"Searching StashDB: {query}")
            self._page.goto(url, wait_until="networkidle", timeout=30000)

            results = []

            # Parse scene cards - similar to PornDB
            # Note: Selectors may need adjustment based on actual site structure
            cards = self._page.query_selector_all(
                ".scene-card, [class*='scene'], [class*='result']"
            )

            for card in cards[:5]:  # Limit to top 5 results
                try:
                    title_elem = card.query_selector(".title, h2, h3, [class*='title']")
                    studio_elem = card.query_selector(".studio, [class*='studio']")
                    performers_elems = card.query_selector_all(
                        ".performer, [class*='performer']"
                    )

                    if title_elem:
                        title = title_elem.inner_text().strip()
                        studio = (
                            studio_elem.inner_text().strip()
                            if studio_elem
                            else "Unknown"
                        )
                        performers = (
                            [p.inner_text().strip() for p in performers_elems]
                            if performers_elems
                            else []
                        )

                        link_elem = card.query_selector("a[href*='/scene']")
                        scene_url = (
                            f"{self.STASHDB_URL}{link_elem.get_attribute('href')}"
                            if link_elem
                            else None
                        )

                        img_elem = card.query_selector("img")
                        thumbnail = img_elem.get_attribute("src") if img_elem else None

                        results.append(
                            SceneMetadata(
                                title=title,
                                studio=studio,
                                performers=performers,
                                source_database="stashdb",
                                source_url=scene_url,
                                thumbnail_url=thumbnail,
                            )
                        )

                except Exception as e:
                    logger.warning(f"Error parsing StashDB card: {e}")
                    continue

            logger.info(f"Found {len(results)} result(s) on StashDB")
            return results

        except Exception as e:
            logger.exception(f"Error searching StashDB: {e}")
            return []

    def _calculate_confidence(
        self, parsed: Optional[ParsedFilename], scene: SceneMetadata
    ) -> float:
        """
        Calculate confidence score (0.0-1.0) for a match.

        Factors:
        - Title similarity (Levenshtein distance or token overlap) - 50%
        - Studio match (exact or partial) - 25%
        - Performer name match - 25%

        Args:
            parsed: ParsedFilename from original file
            scene: SceneMetadata from database

        Returns:
            Confidence score from 0.0 to 1.0
        """
        if not parsed:
            return 0.0

        score = 0.0

        # Title similarity (50%)
        if parsed.title and scene.title:
            title_ratio = SequenceMatcher(
                None, parsed.title.lower(), scene.title.lower()
            ).ratio()
            score += title_ratio * 0.5

        # Studio match (25%)
        if parsed.studio and scene.studio:
            studio_parsed = parsed.studio.lower()
            studio_scene = scene.studio.lower()

            if studio_parsed == studio_scene:
                score += 0.25
            elif studio_parsed in studio_scene or studio_scene in studio_parsed:
                score += 0.15

        # Performer match (25%)
        if parsed.performers and scene.performers:
            parsed_performers = set(p.lower() for p in parsed.performers)
            scene_performers = set(p.lower() for p in scene.performers)

            if parsed_performers & scene_performers:
                overlap = len(parsed_performers & scene_performers)
                total = len(parsed_performers | scene_performers)
                score += (overlap / total) * 0.25

        return min(score, 1.0)

    def _cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self._browser:
                logger.info("Closing browser")
                self._browser.close()

            if self._playwright:
                self._playwright.stop()

        except Exception as e:
            logger.warning(f"Error cleaning up browser: {e}")
