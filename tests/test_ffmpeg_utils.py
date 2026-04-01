"""Tests for shared FFmpeg utility functions."""

from types import SimpleNamespace

from src.utils.ffmpeg_utils import (
    HARDWARE_PROBE_SOURCE,
    calculate_ffmpeg_eta,
    extract_ffmpeg_error,
    find_ffmpeg,
    probe_hardware_encoder,
)


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


class TestProbeHardwareEncoder:
    """Tests for hardware encoder probing."""

    def test_probe_uses_supported_test_source(self, monkeypatch):
        calls = []

        monkeypatch.setattr("src.utils.ffmpeg_utils.find_ffmpeg", lambda: "ffmpeg")
        monkeypatch.setattr(
            "src.utils.ffmpeg_utils.get_available_encoders",
            lambda: ["h264_nvenc"],
        )

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("src.utils.ffmpeg_utils.subprocess.run", fake_run)

        available, error = probe_hardware_encoder("h264_nvenc")

        assert available is True
        assert error is None
        assert calls
        cmd = calls[0][0]
        assert HARDWARE_PROBE_SOURCE in cmd
        assert "-frames:v" in cmd
        assert "1" in cmd

    def test_probe_returns_ffmpeg_failure_summary(self, monkeypatch):
        monkeypatch.setattr("src.utils.ffmpeg_utils.find_ffmpeg", lambda: "ffmpeg")
        monkeypatch.setattr(
            "src.utils.ffmpeg_utils.get_available_encoders",
            lambda: ["h264_nvenc"],
        )
        monkeypatch.setattr(
            "src.utils.ffmpeg_utils.subprocess.run",
            lambda cmd, **kwargs: SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="InitializeEncoder failed: invalid param (8)",
            ),
        )

        available, error = probe_hardware_encoder("h264_nvenc")

        assert available is False
        assert error == "InitializeEncoder failed: invalid param (8)"


class TestFindFfmpeg:
    """Tests for FFmpeg binary discovery."""

    def test_find_ffmpeg_checks_winget_paths_on_windows(self, monkeypatch, tmp_path):
        winget_bin = (
            tmp_path
            / "Microsoft"
            / "WinGet"
            / "Packages"
            / "BtbN.FFmpeg.GPL_test"
            / "ffmpeg-build"
            / "bin"
        )
        winget_bin.mkdir(parents=True)
        ffmpeg_path = winget_bin / "ffmpeg.exe"
        ffmpeg_path.write_text("")

        monkeypatch.setattr("src.utils.ffmpeg_utils.sys.platform", "win32")
        monkeypatch.setattr("src.utils.ffmpeg_utils.shutil.which", lambda name: None)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

        assert find_ffmpeg() == str(ffmpeg_path)
