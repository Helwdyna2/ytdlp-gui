"""Auth status widget for the Download tab."""

import logging
import os
from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from ...core.site_auth import get_handler_for_host, SiteAuthHandler
from ...core.url_domains import extract_hostnames
from ...core.netscape_cookies import (
    get_cookie_domains,
    domain_suffix_matches_cookie_domains,
)
from ...services.config_service import ConfigService
from ...utils.platform_utils import get_data_dir
from ..theme.style_utils import set_status_color

logger = logging.getLogger(__name__)

# User-friendly status labels
AUTH_STATUS_LABELS = {
    "authenticated": "Logged in",
    "not_authenticated": "Not logged in",
    "unknown": "Unknown site",
    "skipped": "Skipped",
}

# Button text
AUTH_BUTTON_TEXT = "Log In"
SKIP_BUTTON_TEXT = "Skip"

# Tooltips
AUTH_BUTTON_TOOLTIP = "Open browser to log in to {domain}"
AUTH_BUTTON_TOOLTIP_LOGGED_IN = "Click to re-authenticate with {domain}"
SKIP_BUTTON_TOOLTIP = "Skip authentication and proceed without login"
STATUS_TOOLTIP_AUTHENTICATED = "You are authenticated and can download from this site"
STATUS_TOOLTIP_NOT_AUTHENTICATED = "Authentication required - click 'Log In' to proceed"
STATUS_TOOLTIP_UNKNOWN = "This site may or may not require login"
STATUS_TOOLTIP_SKIPPED = (
    "Authentication skipped - downloads may fail if login is required"
)


def _format_path_for_display(path: str) -> str:
    """Format a file path for user-friendly display.

    Replaces the home directory portion with '~' if applicable.

    Args:
        path: The absolute file path

    Returns:
        A user-friendly path string (e.g., ~/data/cookies/playwright_cookies.txt)
    """
    if not path:
        return path

    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home) :]
    return path


class _AuthStatusRow(QWidget):
    """Row widget for a single domain auth status."""

    authenticate_clicked = pyqtSignal(str)
    skip_clicked = pyqtSignal(str)

    def __init__(
        self,
        hostname: str,
        display_name: str,
        show_skip: bool,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.hostname = hostname
        self.display_name = display_name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.name_label = QLabel(display_name)
        self.name_label.setMinimumWidth(140)
        self.name_label.setAccessibleName(f"{display_name} Domain")
        layout.addWidget(self.name_label)

        self.status_label = QLabel(AUTH_STATUS_LABELS["unknown"])
        self.status_label.setMinimumWidth(120)
        self.status_label.setAccessibleName(f"{display_name} Auth Status")
        self.status_label.setAccessibleDescription(
            f"Authentication status for {display_name}: {AUTH_STATUS_LABELS['unknown']}"
        )
        self.status_label.setToolTip(STATUS_TOOLTIP_UNKNOWN)
        layout.addWidget(self.status_label)

        self.authenticate_button = QPushButton(AUTH_BUTTON_TEXT)
        self.authenticate_button.setAccessibleName(f"Log in to {display_name}")
        self.authenticate_button.setAccessibleDescription(
            f"Open browser window to log in to {display_name}. "
            f"After logging in, close the browser to export cookies."
        )
        self.authenticate_button.setToolTip(
            AUTH_BUTTON_TOOLTIP.format(domain=display_name)
        )
        self.authenticate_button.clicked.connect(
            lambda: self.authenticate_clicked.emit(self.hostname)
        )
        layout.addWidget(self.authenticate_button)

        self.skip_button: Optional[QPushButton] = None
        if show_skip:
            self.skip_button = QPushButton(SKIP_BUTTON_TEXT)
            self.skip_button.setAccessibleName(f"Skip {display_name} authentication")
            self.skip_button.setAccessibleDescription(
                f"Skip authentication for {display_name} and proceed without login. "
                f"Downloads may fail if this site requires authentication."
            )
            self.skip_button.setToolTip(SKIP_BUTTON_TOOLTIP)
            self.skip_button.clicked.connect(
                lambda: self.skip_clicked.emit(self.hostname)
            )
            layout.addWidget(self.skip_button)

        layout.addStretch()

    def set_status(self, status: str, is_authenticated: bool = False) -> None:
        """Update the status label text, tooltips, and dataColor.

        Args:
            status: The status text to display
            is_authenticated: Whether the user is authenticated for this domain
        """
        self.status_label.setText(status)
        self.status_label.setAccessibleDescription(
            f"Authentication status for {self.display_name}: {status}"
        )

        # Set dataColor for QSS styling
        if is_authenticated:
            status_type = "success"
        elif status == AUTH_STATUS_LABELS["not_authenticated"]:
            status_type = "warning"
        else:
            # unknown, skipped
            status_type = "muted"

        set_status_color(self.status_label, status_type)

        # Update tooltips based on authentication state
        if is_authenticated:
            self.status_label.setToolTip(STATUS_TOOLTIP_AUTHENTICATED)
            self.authenticate_button.setToolTip(
                AUTH_BUTTON_TOOLTIP_LOGGED_IN.format(domain=self.display_name)
            )
        elif status == AUTH_STATUS_LABELS["skipped"]:
            self.status_label.setToolTip(STATUS_TOOLTIP_SKIPPED)
        elif status == AUTH_STATUS_LABELS["unknown"]:
            self.status_label.setToolTip(STATUS_TOOLTIP_UNKNOWN)
        else:
            self.status_label.setToolTip(STATUS_TOOLTIP_NOT_AUTHENTICATED)
            self.authenticate_button.setToolTip(
                AUTH_BUTTON_TOOLTIP.format(domain=self.display_name)
            )


class AuthStatusWidget(QWidget):
    """Displays per-domain authentication status for the Download tab."""

    authenticate_requested = pyqtSignal(str)
    status_changed = pyqtSignal(dict)

    DEBOUNCE_MS = 200
    """Milliseconds to debounce status refresh after URL changes."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = ConfigService()
        self._hostnames: List[str] = []
        self._rows: Dict[str, _AuthStatusRow] = {}
        self._skipped_unknown: set[str] = set()
        self._cached_cookie_domains: Optional[set[str]] = None

        self._status_refresh_timer = QTimer(self)
        self._status_refresh_timer.setSingleShot(True)
        self._status_refresh_timer.timeout.connect(self._on_debounced_refresh)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Login Status")
        header.setObjectName("boldLabel")
        header.setAccessibleName("Site Login Status")
        header.setToolTip(
            "Shows whether you are logged in to sites that require authentication"
        )
        layout.addWidget(header)

        self._rows_container = QVBoxLayout()
        layout.addLayout(self._rows_container)

        # Get the actual cookies file path from config
        cookies_path = self._config.get("auth.cookies_file_path", "")
        display_path = _format_path_for_display(cookies_path)

        note = QLabel(
            "Sign in using the Download tab first to access private content."
        )
        note.setWordWrap(True)
        note.setObjectName("dimLabel")
        note.setAccessibleName("Login instructions")
        note.setAccessibleDescription(
            "Instructions for logging in to sites that require authentication"
        )
        layout.addWidget(note)

        # Add cookies file path info
        if display_path:
            path_note = QLabel(f"Cookies saved to: {display_path}")
            path_note.setWordWrap(True)
            path_note.setObjectName("dimLabel")
            path_note.setAccessibleName("Cookies file location")
            path_note.setAccessibleDescription(
                f"Path to the cookies file: {display_path}"
            )
            path_note.setToolTip(f"Cookies are stored in: {cookies_path}")
            layout.addWidget(path_note)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

    def set_urls(self, urls: List[str]) -> None:
        """Update domains based on the current URL list.

        Debounces the status refresh so rapid URL edits don't
        trigger repeated cookie file parsing.
        """
        hostnames = extract_hostnames(urls)
        self._hostnames = hostnames
        self._skipped_unknown = {h for h in self._skipped_unknown if h in hostnames}
        self._rebuild_rows()

    def refresh_status(self) -> None:
        """Refresh statuses for existing domains (invalidates cookie cache)."""
        self._cached_cookie_domains = None
        self._update_statuses()

    def invalidate_cookie_cache(self) -> None:
        """Invalidate the cached cookie domains.

        Call after cookie file changes (e.g., after authentication).
        """
        self._cached_cookie_domains = None

    def _rebuild_rows(self) -> None:
        while self._rows_container.count():
            item = self._rows_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._rows.clear()

        for hostname in self._hostnames:
            handler = get_handler_for_host(hostname)
            display_name = handler.display_name if handler else hostname
            show_skip = handler is None
            row = _AuthStatusRow(hostname, display_name, show_skip)
            row.authenticate_clicked.connect(self.authenticate_requested.emit)
            row.skip_clicked.connect(self._on_skip_clicked)
            self._rows_container.addWidget(row)
            self._rows[hostname] = row

        self._schedule_status_refresh()

    def _on_skip_clicked(self, hostname: str) -> None:
        self._skipped_unknown.add(hostname)
        self._update_statuses()

    def _schedule_status_refresh(self) -> None:
        """Schedule a debounced status refresh."""
        self._status_refresh_timer.start(self.DEBOUNCE_MS)

    def _on_debounced_refresh(self) -> None:
        """Handle debounced timer timeout - parse cookies once and update."""
        self._cached_cookie_domains = None
        self._update_statuses()

    def _get_cookie_domains(self, cookies_path: str) -> set[str]:
        """Return cached cookie domains, parsing the file only if needed."""
        if self._cached_cookie_domains is None:
            self._cached_cookie_domains = get_cookie_domains(cookies_path)
            logger.debug(
                "Parsed cookie file: %d domains found",
                len(self._cached_cookie_domains),
            )
        return self._cached_cookie_domains

    def _update_statuses(self) -> None:
        cookies_path = self._config.get("auth.cookies_file_path", "")
        cookie_domains = self._get_cookie_domains(cookies_path)
        statuses: Dict[str, str] = {}

        for hostname, row in self._rows.items():
            handler = get_handler_for_host(hostname)
            status, is_authenticated = self._compute_status(
                handler, hostname, cookie_domains
            )
            row.set_status(status, is_authenticated)
            statuses[hostname] = status

        self.status_changed.emit(statuses)

    def _compute_status(
        self,
        handler: Optional[SiteAuthHandler],
        hostname: str,
        cookie_domains: set[str],
    ) -> tuple[str, bool]:
        """Compute authentication status for a domain.

        Returns:
            Tuple of (status_text, is_authenticated)
        """
        if handler is None:
            if hostname in self._skipped_unknown:
                return AUTH_STATUS_LABELS["skipped"], False
            return AUTH_STATUS_LABELS["unknown"], False

        for suffix in handler.cookie_domain_suffixes:
            if domain_suffix_matches_cookie_domains(suffix, cookie_domains):
                return AUTH_STATUS_LABELS["authenticated"], True
        return AUTH_STATUS_LABELS["not_authenticated"], False
