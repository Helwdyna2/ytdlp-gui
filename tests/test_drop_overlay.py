"""Tests for the drag-and-drop overlay widget."""

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QWidget

from src.ui.widgets.drop_overlay import DropOverlay


def test_overlay_starts_hidden(qapp, qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    overlay = DropOverlay(parent)
    assert not overlay.isVisible()


def test_overlay_stores_accepted_extensions(qapp, qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    overlay = DropOverlay(parent, accepted_extensions=[".mp4", ".mkv"])
    assert overlay.accepted_extensions == [".mp4", ".mkv"]


def test_overlay_default_extensions_empty(qapp, qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    overlay = DropOverlay(parent)
    assert overlay.accepted_extensions == []


def test_set_hint_updates_label(qapp, qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    overlay = DropOverlay(parent)
    overlay.set_hint("Video files only")
    assert overlay._hint.text() == "Video files only"


def test_set_text_updates_label(qapp, qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    overlay = DropOverlay(parent)
    overlay.set_text("Drop video here")
    assert overlay._text.text() == "Drop video here"


def test_resize_to_parent_matches_geometry(qapp, qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    parent.resize(800, 600)
    overlay = DropOverlay(parent)
    overlay.resize_to_parent()
    assert overlay.geometry() == QRect(0, 0, 800, 600)


def test_overlay_object_name(qapp, qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    overlay = DropOverlay(parent)
    assert overlay.objectName() == "dropOverlay"
