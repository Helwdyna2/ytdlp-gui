"""Tests for libmpv startup guards."""

import locale

from src.core.editor import mpv_binding


def test_ensure_c_numeric_locale_is_noop_when_already_c(monkeypatch):
    calls = []
    mpv_binding._MPV_LOCALE_CONFIGURED = False

    def fake_setlocale(category, value=None):
        calls.append((category, value))
        assert category == locale.LC_NUMERIC
        if value is None:
            return "C"
        raise AssertionError("Should not try to change locale when it is already 'C'")

    monkeypatch.setattr(mpv_binding.locale, "setlocale", fake_setlocale)

    assert mpv_binding.ensure_c_numeric_locale() is True
    assert calls == [(locale.LC_NUMERIC, None)]


def test_ensure_c_numeric_locale_switches_non_c_locale(monkeypatch):
    calls = []
    mpv_binding._MPV_LOCALE_CONFIGURED = False

    def fake_setlocale(category, value=None):
        calls.append((category, value))
        assert category == locale.LC_NUMERIC
        if value is None:
            return "nb_NO.UTF-8"
        assert value == "C"
        return "C"

    monkeypatch.setattr(mpv_binding.locale, "setlocale", fake_setlocale)

    assert mpv_binding.ensure_c_numeric_locale() is True
    assert calls == [
        (locale.LC_NUMERIC, None),
        (locale.LC_NUMERIC, "C"),
    ]


def test_ensure_c_numeric_locale_reports_failure(monkeypatch):
    calls = []
    mpv_binding._MPV_LOCALE_CONFIGURED = False

    def fake_setlocale(category, value=None):
        calls.append((category, value))
        assert category == locale.LC_NUMERIC
        if value is None:
            return "nb_NO.UTF-8"
        raise locale.Error("unsupported locale")

    monkeypatch.setattr(mpv_binding.locale, "setlocale", fake_setlocale)

    assert mpv_binding.ensure_c_numeric_locale() is False
    assert calls == [
        (locale.LC_NUMERIC, None),
        (locale.LC_NUMERIC, "C"),
    ]
