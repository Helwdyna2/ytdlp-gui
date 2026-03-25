"""Playwright worker for extracting URLs from pages."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ..data.models import ExtractUrlsConfig
from .extract_url_patterns import extract_canonical_urls, get_domain_key
from .playwright_setup import format_playwright_setup_error
from ..services.config_service import ConfigService

logger = logging.getLogger(__name__)


class ExtractUrlsWorker(QThread):
    """
    Worker thread for URL extraction using Playwright.
    """

    progress = pyqtSignal(int, int, str)
    result = pyqtSignal(int, list)
    completed = pyqtSignal(list, str)
    error = pyqtSignal(str)

    INSTAGRAM_URL = "https://www.instagram.com/"
    REDGIFS_URL = "https://www.redgifs.com/"

    def __init__(
        self,
        config: ExtractUrlsConfig,
        seed_urls: List[str],
        parent: Optional[QObject] = None,
    ) -> None:
        """
        Initialize worker.

        Args:
            config: ExtractUrlsConfig with options and profile dir
            seed_urls: List of seed URLs
            parent: Parent QObject
        """
        super().__init__(parent)
        self._config = config
        self._seed_urls = seed_urls
        self._cancelled = False
        self._playwright = None
        self._context = None
        self._page = None
        self._login_checked: Set[str] = set()
        self._config_service = ConfigService()

    def cancel(self) -> None:
        """Request cancellation."""
        self._cancelled = True

    def run(self) -> None:
        """Run the worker task."""
        try:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                self.error.emit(
                    "Playwright not installed. Please install it with: pip install playwright && playwright install chromium"
                )
                return

            self._run_extract()
        except Exception as e:
            logger.exception(f"Fatal error in ExtractUrlsWorker: {e}")
            self.error.emit(f"Fatal error: {e}")
        finally:
            self._cleanup()

    def _run_extract(self) -> None:
        """Run extraction workflow."""
        if not self._seed_urls:
            self.error.emit("No URLs to extract")
            return

        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            try:
                browser_name = self._config_service.get(
                    "playwright.browser", "chromium"
                )
                engine = getattr(
                    self._playwright, browser_name, self._playwright.chromium
                )
                self._context = engine.launch_persistent_context(
                    user_data_dir=self._config.profile_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                )
            except Exception as e:
                message = format_playwright_setup_error(e)
                if message:
                    self.error.emit(message)
                    return
                raise
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

            found_urls: Set[str] = set()
            total = len(self._seed_urls)

            for idx, url in enumerate(self._seed_urls):
                if self._cancelled:
                    self.error.emit("Extraction cancelled")
                    return

                domain_key = get_domain_key(url)
                page = self._page

                if domain_key in {"instagram", "redgifs"}:
                    if domain_key not in self._login_checked:
                        if not self._check_logged_in(domain_key, page):
                            self.error.emit(
                                "Authentication required for "
                                f"{domain_key.title()}. Authenticate in the Download tab (Auth Status panel), then try again."
                            )
                            return
                        self._login_checked.add(domain_key)

                self.progress.emit(
                    idx + 1, total, f"Loading ({idx + 1}/{total}): {url}"
                )

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page_found = set(self._collect_target_urls(page))

                    if self._config.auto_scroll_enabled:
                        page_found |= self._auto_scroll_extract(
                            page, idx + 1, total
                        )

                    new_urls = page_found - found_urls
                    if new_urls:
                        found_urls.update(new_urls)
                        self.result.emit(idx, sorted(new_urls, key=str.lower))

                except Exception as e:
                    logger.warning(f"Error processing {url}: {e}")
                    self.progress.emit(
                        idx + 1, total, f"Error loading {url}: {e}"
                    )

            if self._cancelled:
                self.error.emit("Extraction cancelled")
                return

            output_path = self._write_output(sorted(found_urls, key=str.lower))
            self.completed.emit(sorted(found_urls, key=str.lower), output_path)

        except Exception as e:
            logger.exception(f"Extraction error: {e}")
            self.error.emit(f"Extraction error: {e}")

    def _check_logged_in(self, domain: str, page) -> bool:
        """Check login state for a domain."""
        try:
            page.goto(self._get_login_url(domain), wait_until="networkidle", timeout=30000)
            return self._is_logged_in(domain, page)
        except Exception as e:
            logger.warning(f"Login check failed for {domain}: {e}")
            return False

    def _is_logged_in(self, domain: str, page) -> bool:
        """Detect login state using simple selectors."""
        if domain == "instagram":
            login_input = page.query_selector("input[name='username']")
            login_text = page.query_selector("text=Log in")
            return not (login_input or login_text)

        login_button = page.query_selector(
            "a[href*='login'], button:has-text('Login'), a:has-text('Sign in')"
        )
        return not bool(login_button)

    def _collect_target_urls(self, page) -> List[str]:
        """Collect canonical target URLs from a page."""
        urls = [page.url] if page.url else []
        try:
            hrefs = page.evaluate(
                "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
            )
            if isinstance(hrefs, list):
                urls.extend([u for u in hrefs if isinstance(u, str)])
        except Exception as e:
            logger.debug(f"Failed to collect hrefs: {e}")

        return extract_canonical_urls(urls)

    def _auto_scroll_extract(self, page, index: int, total: int) -> Set[str]:
        """Auto-scroll the page to collect more URLs."""
        collected: Set[str] = set()
        total_scrolls = 0
        idle_count = 0
        bounce_attempts = 0

        while (
            total_scrolls < self._config.max_scrolls
            and bounce_attempts < self._config.max_bounce_attempts
            and not self._cancelled
        ):
            current_urls = set(self._collect_target_urls(page))
            new_urls = current_urls - collected
            if new_urls:
                collected.update(new_urls)
                idle_count = 0
            else:
                idle_count += 1

            self.progress.emit(
                index,
                total,
                f"Auto-scroll {total_scrolls + 1}/{self._config.max_scrolls}",
            )

            metrics = page.evaluate(
                "() => ({scrollY: window.scrollY, innerHeight: window.innerHeight, scrollHeight: document.documentElement.scrollHeight})"
            )
            at_bottom = (
                metrics["scrollY"] + metrics["innerHeight"]
                >= metrics["scrollHeight"] - 500
            )

            if at_bottom and idle_count >= self._config.idle_limit:
                bounce_attempts += 1
                idle_count = 0
                page.evaluate("() => window.scrollBy(0, -800)")
                page.wait_for_timeout(max(int(self._config.delay_ms / 2), 100))
                page.evaluate(
                    "() => window.scrollTo(0, document.documentElement.scrollHeight)"
                )
            else:
                page.evaluate("() => window.scrollBy(0, 600)")

            total_scrolls += 1
            page.wait_for_timeout(self._config.delay_ms)

        return collected

    def _write_output(self, urls: List[str]) -> str:
        """Write extracted URLs to a text file."""
        output_dir = Path(self._config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"extract_urls_{timestamp}.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(urls))

        return str(output_path)

    def _cleanup(self) -> None:
        """Clean up Playwright resources."""
        try:
            if self._page:
                try:
                    self._page.close()
                except Exception:
                    pass

            if self._context:
                try:
                    self._context.close()
                except Exception:
                    pass

            if self._playwright:
                self._playwright.stop()

        except Exception as e:
            logger.warning(f"Error cleaning up Playwright: {e}")

    def _get_login_url(self, domain: str) -> str:
        """Get base login URL for a domain."""
        return self.INSTAGRAM_URL if domain == "instagram" else self.REDGIFS_URL
