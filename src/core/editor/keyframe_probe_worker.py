"""Background ffprobe worker for keyframe timestamps."""

from __future__ import annotations

import json
import subprocess

from PyQt6.QtCore import QThread, pyqtSignal

from ...utils.ffmpeg_utils import find_ffprobe
from ...utils.platform_utils import get_subprocess_kwargs


class KeyframeProbeWorker(QThread):
    """Probe a video's keyframe positions without blocking the UI."""

    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self._file_path = file_path

    def run(self) -> None:
        ffprobe_path = find_ffprobe()
        if not ffprobe_path:
            self.failed.emit("ffprobe not found")
            return

        cmd = [
            ffprobe_path,
            "-v",
            "quiet",
            "-select_streams",
            "v:0",
            "-skip_frame",
            "nokey",
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time,pkt_dts_time",
            "-print_format",
            "json",
            self._file_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                **get_subprocess_kwargs(),
            )
            if result.returncode != 0:
                self.failed.emit(result.stderr.strip() or "ffprobe keyframe scan failed")
                return

            payload = json.loads(result.stdout or "{}")
            frames = payload.get("frames", [])
            timestamps: list[float] = []
            for frame in frames:
                raw_value = frame.get("best_effort_timestamp_time") or frame.get("pkt_dts_time")
                if raw_value in (None, "N/A", ""):
                    continue
                try:
                    timestamps.append(float(raw_value))
                except (TypeError, ValueError):
                    continue

            self.completed.emit(sorted(set(timestamps)))
        except Exception as exc:
            self.failed.emit(str(exc))
