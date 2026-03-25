"""Tests for shared FFmpeg utility functions."""

from src.utils.ffmpeg_utils import calculate_ffmpeg_eta, extract_ffmpeg_error


class TestCalculateEta:
    """Tests for calculate_ffmpeg_eta."""

    def test_normal_speed(self):
        result = calculate_ffmpeg_eta(
            duration=100.0, current_time=50.0, speed_str="1.0x"
        )
        assert result == "50s"

    def test_fast_speed(self):
        result = calculate_ffmpeg_eta(
            duration=100.0, current_time=50.0, speed_str="2.0x"
        )
        assert result == "25s"

    def test_na_speed(self):
        result = calculate_ffmpeg_eta(
            duration=100.0, current_time=50.0, speed_str="N/A"
        )
        assert result == "N/A"

    def test_empty_speed(self):
        result = calculate_ffmpeg_eta(duration=100.0, current_time=50.0, speed_str="")
        assert result == "N/A"

    def test_zero_speed(self):
        result = calculate_ffmpeg_eta(duration=100.0, current_time=50.0, speed_str="0x")
        assert result == "N/A"

    def test_minutes_format(self):
        result = calculate_ffmpeg_eta(
            duration=600.0, current_time=0.0, speed_str="1.0x"
        )
        assert result == "10m 0s"

    def test_hours_format(self):
        result = calculate_ffmpeg_eta(
            duration=7200.0, current_time=0.0, speed_str="1.0x"
        )
        assert result == "2h 0m"


class TestExtractError:
    """Tests for extract_ffmpeg_error."""

    def test_finds_error_line(self):
        output = "line1\nSome Error occurred\nline3"
        assert "Error" in extract_ffmpeg_error(output)

    def test_empty_returns_fallback(self):
        assert extract_ffmpeg_error("") == "Unknown error"
        assert extract_ffmpeg_error("", fallback="Custom") == "Custom"

    def test_no_error_returns_last_line(self):
        output = "line1\nline2\nlast line"
        assert extract_ffmpeg_error(output) == "last line"

    def test_truncates_long_lines(self):
        output = "x" * 300
        result = extract_ffmpeg_error(output)
        assert len(result) <= 200
