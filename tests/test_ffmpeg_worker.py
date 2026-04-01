"""Tests for FFmpegWorker command construction."""

from src.core.ffmpeg_worker import FFmpegWorker
from src.data.models import ConversionConfig


def test_ffmpeg_worker_adds_scale_and_pad_filter_for_resolution():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.mp4",
        ConversionConfig(output_codec="h264", output_resolution="1920x1080"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    vf_index = command.index("-vf")
    assert command[vf_index + 1] == (
        "scale=1920:1080:force_original_aspect_ratio=decrease:"
        "force_divisible_by=2,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )


def test_ffmpeg_worker_skips_scale_filter_when_resolution_not_selected():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.mp4",
        ConversionConfig(output_codec="h264", output_resolution=None),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert "-vf" not in command
