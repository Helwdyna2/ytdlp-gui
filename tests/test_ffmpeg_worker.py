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


def test_ffmpeg_worker_builds_vp9_webm_command():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.webm",
        ConversionConfig(output_codec="vp9", output_resolution="1920x1080"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert "libvpx-vp9" in command
    assert "libopus" in command
    assert "-b:v" in command


def test_ffmpeg_worker_builds_audio_only_command():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.mp3",
        ConversionConfig(output_codec="mp3", output_resolution="1920x1080"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert "-vn" in command
    assert "libmp3lame" in command
    assert "-c:v" not in command
