"""Tests for stable preview feedback during scrubbing."""

from src.ui.widgets.video_preview_widget import VideoPreviewWidget


def test_preview_starts_dormant_until_backend_init(qapp, qtbot):
    widget = VideoPreviewWidget()
    qtbot.addWidget(widget)

    assert widget._availability_label.text() == (
        "Load a video to initialize preview playback and scrub controls."
    )


def test_late_position_updates_do_not_rewrite_drag_label(qapp, qtbot):
    widget = VideoPreviewWidget()
    qtbot.addWidget(widget)

    widget._duration = 100.0
    widget._set_controls_enabled(True)
    widget._position_slider.setSliderDown(True)

    widget._on_slider_pressed()
    widget._on_slider_moved(widget._POSITION_SLIDER_STEPS // 2)
    widget._on_position_changed(12.0)

    assert widget._time_label.text() == "00:00:50.000 / 00:01:40.000"
