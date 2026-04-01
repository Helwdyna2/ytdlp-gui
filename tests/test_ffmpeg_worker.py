"""Tests for FFmpegWorker command construction."""

import pytest

from src.core.ffmpeg_worker import FFmpegWorker
from src.data.models import ConversionConfig


def test_ffmpeg_worker_adds_auto_orientation_scale_filter_for_resolution():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.mp4",
        ConversionConfig(output_codec="h264", output_resolution="1080p"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    vf_index = command.index("-vf")
    assert command[vf_index + 1] == (
        "scale='if(gte(iw,ih),-2,1080)':'if(gte(iw,ih),1080,-2)'"
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
        ConversionConfig(output_codec="vp9", output_resolution="1080p"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert "libvpx-vp9" in command
    assert command[command.index("-c:a") + 1] == "copy"
    assert "-b:v" in command


def test_ffmpeg_worker_builds_audio_only_command():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.mp3",
        ConversionConfig(output_codec="mp3", output_resolution="1080p"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert "-vn" in command
    assert "libmp3lame" in command
    assert "-c:v" not in command


def test_ffmpeg_worker_disables_audio_for_video_outputs_when_requested():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.mp4",
        ConversionConfig(output_codec="h264", audio_mode="none"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert "-an" in command
    assert "-c:a" not in command


def test_ffmpeg_worker_adds_selected_output_frame_rate():
    worker = FFmpegWorker(
        "/tmp/input.mp4",
        "/tmp/output.mp4",
        ConversionConfig(output_codec="h264", frame_rate="29.97"),
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert command[command.index("-r") + 1] == "29.97"


def test_ffmpeg_worker_builds_same_as_source_video_command():
    worker = FFmpegWorker(
        "/tmp/input.mov",
        "/tmp/output.mov",
        ConversionConfig(output_codec="source"),
        source_codec="hevc",
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert command[command.index("-c:v") + 1] == "libx265"
    assert command[-1] == "/tmp/output.mov"


def test_ffmpeg_worker_builds_same_as_source_audio_command():
    worker = FFmpegWorker(
        "/tmp/input.m4a",
        "/tmp/output.m4a",
        ConversionConfig(output_codec="source"),
        source_codec="aac",
    )

    command = worker._build_command("/usr/local/bin/ffmpeg")

    assert "-vn" in command
    assert command[command.index("-c:a") + 1] == "aac"
    assert "-c:v" not in command


def test_ffmpeg_worker_rejects_unsupported_same_as_source_codec():
    worker = FFmpegWorker(
        "/tmp/input.mkv",
        "/tmp/output.mkv",
        ConversionConfig(output_codec="source"),
        source_codec="av1",
    )

    with pytest.raises(ValueError, match="Same as source"):
        worker._build_command("/usr/local/bin/ffmpeg")
