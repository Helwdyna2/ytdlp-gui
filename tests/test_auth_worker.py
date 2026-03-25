"""Tests for auth worker login finalization."""

from src.core.auth_types import AuthResult
from src.core.auth_worker import AuthWorker


def test_finalize_login_retries_cookie_validation_until_success(monkeypatch):
    worker = AuthWorker(
        profile_dir="/tmp/profile",
        cookies_file_path="/tmp/cookies.txt",
        task="login",
        start_url="https://www.instagram.com/",
        target_cookie_suffixes=["instagram.com"],
    )
    emitted = []
    export_attempts = []
    cookie_checks = iter([False, True])

    worker.login_finished.connect(
        lambda result, message, path: emitted.append((result, message, path))
    )
    monkeypatch.setattr(worker, "_export_cookies_to_file", lambda: export_attempts.append(1))
    monkeypatch.setattr(worker, "msleep", lambda _delay: None)
    monkeypatch.setattr(
        "src.core.auth_worker.cookiefile_has_domain_suffix",
        lambda _path, _suffix: next(cookie_checks),
    )

    worker._finalize_login()

    assert export_attempts == [1, 1]
    assert emitted == [
        (
            AuthResult.SUCCESS.value,
            "Authentication complete. Cookies saved.",
            "/tmp/cookies.txt",
        )
    ]


def test_run_redacts_urls_in_error_messages(monkeypatch):
    worker = AuthWorker(
        profile_dir="/tmp/profile",
        cookies_file_path="/tmp/cookies.txt",
        task="export_cookies",
    )
    emitted = []

    worker.error.connect(emitted.append)

    def raise_error():
        raise RuntimeError(
            "Export failed for https://www.instagram.com/reel/abc123/?token=secret#frag"
        )

    monkeypatch.setattr(worker, "_run_export_cookies", raise_error)

    worker.run()

    assert emitted == ["Export failed for https://www.instagram.com/reel/abc123/"]
