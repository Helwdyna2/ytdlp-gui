"""Authentication result types."""

from enum import Enum


class AuthResult(Enum):
    """Result states for authentication attempts."""

    SUCCESS = "success"
    CANCELLED_NO_COOKIES = "cancelled_no_cookies"
    CANCELLED_USER = "cancelled_user"
    ERROR_PLAYWRIGHT_SETUP = "error_playwright_setup"
    ERROR_FATAL = "error_fatal"
