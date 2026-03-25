"""Tests for LogFeed component."""

import pytest
import sys

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_log_feed_creates(qapp):
    from src.ui.components.log_feed import LogFeed

    feed = LogFeed()
    assert feed is not None


def test_log_feed_add_entry(qapp):
    from src.ui.components.log_feed import LogFeed

    feed = LogFeed()
    feed.add_entry("Starting download: video1.mp4", level="info")
    assert feed.entry_count() == 1


def test_log_feed_levels(qapp):
    from src.ui.components.log_feed import LogFeed

    feed = LogFeed()
    feed.add_entry("Info message", level="info")
    feed.add_entry("Warning message", level="warning")
    feed.add_entry("Error message", level="error")
    assert feed.entry_count() == 3


def test_log_feed_clear(qapp):
    from src.ui.components.log_feed import LogFeed

    feed = LogFeed()
    feed.add_entry("test", level="info")
    feed.add_entry("test2", level="info")
    feed.clear()
    assert feed.entry_count() == 0


def test_log_feed_max_entries(qapp):
    from src.ui.components.log_feed import LogFeed

    feed = LogFeed(max_entries=5)
    for i in range(10):
        feed.add_entry(f"Entry {i}", level="info")
    assert feed.entry_count() == 5
