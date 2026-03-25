"""Tests for queued config persistence."""

import threading
import time

import pytest

from src.services.config_service import ConfigService


@pytest.fixture(autouse=True)
def reset_config_service(tmp_path):
    """Reset singleton state and use a temp config path for each test."""
    ConfigService.reset_instance()
    service = ConfigService(config_path=str(tmp_path / "config.json"))
    yield service
    ConfigService.reset_instance()


def test_queue_save_coalesces_repeated_requests(reset_config_service, monkeypatch):
    """Repeated queued saves should collapse into a single eventual save."""
    service = reset_config_service
    called = []
    saved = threading.Event()

    def fake_save():
        called.append("save")
        saved.set()

    monkeypatch.setattr(service, "save", fake_save)

    service.queue_save(delay_ms=20)
    service.queue_save(delay_ms=20)
    service.queue_save(delay_ms=20)

    assert saved.wait(0.3)
    time.sleep(0.05)

    assert called == ["save"]
