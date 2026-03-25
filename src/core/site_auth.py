"""Site authentication handlers and registry."""

from dataclasses import dataclass, field
from typing import Optional, Protocol


class SiteAuthHandler(Protocol):
    """Protocol for site authentication handlers."""

    key: str
    display_name: str
    start_url: str
    cookie_domain_suffixes: list[str]

    def match(self, hostname: str) -> bool:
        """Return True if this handler applies to hostname."""

    def logged_in_heuristic(self, page) -> Optional[bool]:
        """Return True/False if known; None if not supported."""


@dataclass(frozen=True)
class InstagramAuthHandler:
    key: str = "instagram"
    display_name: str = "Instagram"
    start_url: str = "https://www.instagram.com/"
    cookie_domain_suffixes: list[str] = field(
        default_factory=lambda: ["instagram.com"]
    )

    def match(self, hostname: str) -> bool:
        return hostname.lower().endswith("instagram.com")

    def logged_in_heuristic(self, page) -> Optional[bool]:
        try:
            login_input = page.query_selector("input[name='username']")
            login_text = page.query_selector("text=Log in")
            return not (login_input or login_text)
        except Exception:
            return None


@dataclass(frozen=True)
class RedgifsAuthHandler:
    key: str = "redgifs"
    display_name: str = "Redgifs"
    start_url: str = "https://www.redgifs.com/"
    cookie_domain_suffixes: list[str] = field(
        default_factory=lambda: ["redgifs.com"]
    )

    def match(self, hostname: str) -> bool:
        return hostname.lower().endswith("redgifs.com")

    def logged_in_heuristic(self, page) -> Optional[bool]:
        try:
            login_button = page.query_selector(
                "a[href*='login'], button:has-text('Login'), a:has-text('Sign in')"
            )
            return not bool(login_button)
        except Exception:
            return None


KNOWN_AUTH_HANDLERS: list[SiteAuthHandler] = [
    InstagramAuthHandler(),
    RedgifsAuthHandler(),
]


def get_handler_for_host(hostname: str) -> Optional[SiteAuthHandler]:
    """Return the auth handler for hostname, if any."""
    for handler in KNOWN_AUTH_HANDLERS:
        if handler.match(hostname):
            return handler
    return None
