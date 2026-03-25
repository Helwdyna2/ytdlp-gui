"""Tests for URL redaction helpers and log integration."""

from collections import deque
from unittest.mock import Mock

import yt_dlp

from src.core.download_manager import DownloadManager
from src.core.download_worker import DownloadWorker
from src.data.models import OutputConfig
from src.utils.url_redaction import redact_url, redact_urls_in_text


def test_redact_url_strips_query_and_fragment():
    assert (
        redact_url("https://www.instagram.com/reel/abc123/?token=secret#frag")
        == "https://www.instagram.com/reel/abc123/"
    )


def test_redact_url_strips_userinfo_credentials():
    assert (
        redact_url("https://user:secret@example.com/path?query#frag")
        == "https://example.com/path"
    )


def test_redact_url_strips_userinfo_with_port():
    assert (
        redact_url("https://user:secret@example.com:8080/path")
        == "https://example.com:8080/path"
    )


def test_redact_urls_in_text_preserves_context():
    message = (
        "Retrying https://example.com/watch?v=123#frag after "
        "https://redgifs.com/watch/clip?utm_source=feed"
    )

    assert redact_urls_in_text(message) == (
        "Retrying https://example.com/watch after https://redgifs.com/watch/clip"
    )


def test_redact_urls_in_text_strips_userinfo():
    assert (
        redact_urls_in_text("See https://user:secret@example.com/path?x=1")
        == "See https://example.com/path"
    )


def test_download_manager_redacts_queue_log_messages():
    url = "https://example.com/watch?v=123#frag"
    manager = DownloadManager(Mock())
    emitted = []
    manager.log_message.connect(lambda level, message: emitted.append((level, message)))
    manager._queue = deque([url])
    manager._total_count = 1

    assert manager.cancel_download(url) is True
    assert emitted == [("info", "Removed from queue: https://example.com/watch")]


def test_download_worker_redacts_error_log_messages():
    worker = DownloadWorker(
        "https://example.com/watch?v=123#frag",
        OutputConfig(output_dir="/tmp"),
    )
    emitted = []
    worker.log.connect(lambda level, message: emitted.append((level, message)))

    worker._progress_hook(
        {
            "status": "error",
            "error": "HTTP 403 for https://example.com/watch?v=123#frag",
        }
    )

    assert emitted == [
        ("error", "Download error: HTTP 403 for https://example.com/watch")
    ]


def test_download_worker_redacts_completed_failure_messages(monkeypatch):
    url = "https://example.com/watch?v=123#frag"
    worker = DownloadWorker(url, OutputConfig(output_dir="/tmp"))
    completed = []

    class FailingYDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            return {"title": "Example"}

        def download(self, _urls):
            raise yt_dlp.utils.DownloadError(
                "Failed for https://example.com/watch?v=123#frag"
            )

    monkeypatch.setattr("src.core.download_worker.yt_dlp.YoutubeDL", FailingYDL)
    worker.completed.connect(
        lambda success, message, metadata: completed.append(
            (success, message, metadata)
        )
    )

    worker.run()

    assert completed == [
        (
            False,
            "Failed for https://example.com/watch",
            {"url": url},
        )
    ]
