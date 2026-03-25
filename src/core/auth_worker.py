"""Playwright worker for authentication and cookie export."""

import logging
import subprocess
import sys
from typing import Optional, List
from urllib.parse import urlparse

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .auth_types import AuthResult
from .netscape_cookies import (
    write_netscape_cookiefile,
    cookiefile_has_domain_suffix,
    parse_netscape_cookiefile,
)
from .site_auth import get_handler_for_host, SiteAuthHandler
from .playwright_setup import format_playwright_setup_error
from ..utils.url_redaction import redact_urls_in_text

logger = logging.getLogger(__name__)

COOKIE_EXPORT_RETRY_ATTEMPTS = 5
COOKIE_EXPORT_RETRY_DELAY_MS = 250


class AuthWorker(QThread):
    """Worker for login and cookie export tasks."""

    progress = pyqtSignal(str)
    output_received = pyqtSignal(str)  # For streaming install output line by line
    login_finished = pyqtSignal(str, str, str)
    cookies_exported = pyqtSignal(str)
    install_completed = pyqtSignal()
    install_failed = pyqtSignal(str)  # For install failure with full output
    error = pyqtSignal(str)

    def __init__(
        self,
        profile_dir: str,
        cookies_file_path: str,
        task: str,
        start_url: str = "",
        target_cookie_suffixes: Optional[List[str]] = None,
        wait_until: str = "domcontentloaded",
        browser: str = "chromium",
        install_browsers: Optional[List[str]] = None,
        install_force: bool = False,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._profile_dir = profile_dir
        self._cookies_file_path = cookies_file_path
        self._task = task
        self._start_url = start_url
        self._target_cookie_suffixes = target_cookie_suffixes or []
        self._wait_until = wait_until
        self._browser = browser
        self._install_browsers = install_browsers or []
        self._install_force = install_force
        self._cancelled = False
        self._playwright = None

    def cancel(self) -> None:
        """Request cancellation."""
        self._cancelled = True

    def run(self) -> None:
        """Run the worker task."""
        try:
            if self._task in {"login", "export_cookies"}:
                try:
                    from playwright.sync_api import sync_playwright  # noqa: F401
                except ImportError:
                    message = (
                        "Playwright not installed. Please install it with: "
                        "pip install playwright && playwright install chromium"
                    )
                    if self._task == "login":
                        self.login_finished.emit(
                            AuthResult.ERROR_FATAL.value,
                            message,
                            self._cookies_file_path,
                        )
                    else:
                        self.error.emit(message)
                    return

            if self._task == "login":
                self._run_login()
            elif self._task == "export_cookies":
                self._run_export_cookies()
            elif self._task == "install_chromium":
                self._run_install_chromium()
            elif self._task == "install_browsers":
                self._run_install_browsers()
            else:
                self.error.emit(f"Unknown auth task: {self._task}")
        except Exception as e:
            redacted_message = redact_urls_in_text(str(e))
            logger.exception("AuthWorker error: %s", redacted_message)
            if self._task == "login":
                self.login_finished.emit(
                    AuthResult.ERROR_FATAL.value,
                    redacted_message,
                    self._cookies_file_path,
                )
            else:
                self.error.emit(redacted_message)
        finally:
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None

    def _run_login(self) -> None:
        """Open a visible browser for manual login."""
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        try:
            context = getattr(
                self._playwright, self._browser, self._playwright.chromium
            ).launch_persistent_context(
                user_data_dir=self._profile_dir,
                headless=False,
                viewport={"width": 1280, "height": 720},
            )
        except Exception as e:
            message = format_playwright_setup_error(e)
            if message:
                self.login_finished.emit(
                    AuthResult.ERROR_PLAYWRIGHT_SETUP.value,
                    message,
                    self._cookies_file_path,
                )
                return
            raise

        page = context.pages[0] if context.pages else context.new_page()
        if self._start_url:
            try:
                page.goto(self._start_url, wait_until=self._wait_until, timeout=30000)
            except Exception as e:
                if self._is_target_closed_error(e):
                    try:
                        context.close()
                    except Exception:
                        pass
                    self._finalize_login()
                    return
                raise

        self.progress.emit("Browser opened for login. Close it when finished.")

        # Wait until all pages are closed
        while not self._cancelled:
            if not context.pages:
                break
            self.msleep(500)

        try:
            context.close()
        except Exception:
            pass

        if self._cancelled:
            self.login_finished.emit(
                AuthResult.CANCELLED_USER.value,
                "Login cancelled.",
                self._cookies_file_path,
            )
            return

        self._finalize_login()

    def _run_export_cookies(self) -> None:
        """Export cookies from the persistent profile to a cookies.txt file."""
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        try:
            self._export_cookies_to_file()
        except Exception as e:
            message = format_playwright_setup_error(e)
            if message:
                self.error.emit(message)
                return
            raise

        self.cookies_exported.emit(self._cookies_file_path)

    def _run_install_chromium(self) -> None:
        """Install Playwright Chromium browser binaries."""
        self._install_browsers = ["chromium"]
        self._install_force = False
        self._run_install_browsers()

    def _run_install_browsers(self) -> None:
        """Install Playwright browsers with streaming output."""
        browsers = self._install_browsers or []
        browser_label = ", ".join(browsers) if browsers else "default"
        self.progress.emit(
            f"Installing Playwright browsers ({browser_label})..."
        )

        cmd = [sys.executable, "-m", "playwright", "install"]
        if self._install_force:
            cmd.append("--force")
        cmd.extend(browsers)

        # Use Popen for streaming output
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
            )

            output_lines = []
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    output_lines.append(line)
                    self.output_received.emit(line)

            process.wait()

            if process.returncode != 0:
                full_output = "\n".join(output_lines)
                error_message = (
                    "Failed to install Playwright browsers. "
                    "Try running: python -m playwright install chromium firefox webkit\n\n"
                    f"{full_output}"
                )
                self.install_failed.emit(error_message)
                return

            self.progress.emit("Playwright browsers installed.")
            self.install_completed.emit()

        except Exception as e:
            logger.exception(f"Playwright install error: {e}")
            self.install_failed.emit(f"Installation failed with error: {str(e)}")

    def _is_target_closed_error(self, error: Exception) -> bool:
        """Check if error indicates a closed target/page/context/browser."""
        if error.__class__.__name__ == "TargetClosedError":
            return True
        return "Target page, context or browser has been closed" in str(error)

    def _resolve_target_cookie_suffixes(self) -> List[str]:
        """Resolve cookie suffixes for validation."""
        if self._target_cookie_suffixes:
            return self._target_cookie_suffixes

        if self._start_url:
            parsed = urlparse(self._start_url)
            if parsed.hostname:
                return [parsed.hostname]

        return []

    def _resolve_handler(self) -> Optional[SiteAuthHandler]:
        """Resolve a site auth handler for the start URL."""
        if not self._start_url:
            return None
        parsed = urlparse(self._start_url)
        if not parsed.hostname:
            return None
        return get_handler_for_host(parsed.hostname)

    def _export_cookies_to_file(self) -> None:
        """Export cookies to the configured cookies.txt file."""
        context = getattr(
            self._playwright, self._browser, self._playwright.chromium
        ).launch_persistent_context(
            user_data_dir=self._profile_dir,
            headless=True,
            viewport={"width": 1280, "height": 720},
        )
        cookies = context.cookies()
        write_netscape_cookiefile(self._cookies_file_path, cookies)

        try:
            context.close()
        except Exception:
            pass

    def _cookies_match_targets(self, suffixes: List[str]) -> bool:
        """Return True when the exported cookie file satisfies the target domains."""
        if suffixes:
            return any(
                cookiefile_has_domain_suffix(self._cookies_file_path, suffix)
                for suffix in suffixes
            )
        return bool(parse_netscape_cookiefile(self._cookies_file_path))

    def _export_and_validate_cookies(self, suffixes: List[str]) -> bool:
        """Retry cookie export briefly to absorb profile-write timing delays."""
        for attempt in range(COOKIE_EXPORT_RETRY_ATTEMPTS):
            self._export_cookies_to_file()
            if self._cookies_match_targets(suffixes):
                return True
            if attempt < COOKIE_EXPORT_RETRY_ATTEMPTS - 1:
                self.msleep(COOKIE_EXPORT_RETRY_DELAY_MS)
        return False

    def _finalize_login(self) -> None:
        """Export cookies and emit login result based on validation."""
        suffixes = self._resolve_target_cookie_suffixes()
        try:
            has_cookies = self._export_and_validate_cookies(suffixes)
        except Exception as e:
            message = format_playwright_setup_error(e)
            if message:
                self.login_finished.emit(
                    AuthResult.ERROR_PLAYWRIGHT_SETUP.value,
                    message,
                    self._cookies_file_path,
                )
                return
            raise

        if has_cookies:
            self.login_finished.emit(
                AuthResult.SUCCESS.value,
                "Authentication complete. Cookies saved.",
                self._cookies_file_path,
            )
        else:
            message = "No cookies were saved. Please try again."
            handler = self._resolve_handler()
            if handler:
                heuristic = self._check_logged_in(handler)
                if heuristic is True:
                    message = (
                        "Login detected, but cookies were not saved. Please try again."
                    )
                elif heuristic is False:
                    message = "Not logged in. Please try again."
            self.login_finished.emit(
                AuthResult.CANCELLED_NO_COOKIES.value,
                message,
                self._cookies_file_path,
            )

    def _check_logged_in(self, handler: SiteAuthHandler) -> Optional[bool]:
        """Perform a lightweight login heuristic check."""
        try:
            context = getattr(
                self._playwright, self._browser, self._playwright.chromium
            ).launch_persistent_context(
                user_data_dir=self._profile_dir,
                headless=True,
                viewport={"width": 1280, "height": 720},
            )
        except Exception:
            return None

        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(handler.start_url, wait_until="domcontentloaded", timeout=30000)
            return handler.logged_in_heuristic(page)
        except Exception:
            return None
        finally:
            try:
                context.close()
            except Exception:
                pass
