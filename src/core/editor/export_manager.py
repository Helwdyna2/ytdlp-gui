"""Feature-local export runner for Trim editor workflows."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ...utils.ffmpeg_utils import extract_ffmpeg_error, find_ffmpeg
from ...utils.platform_utils import get_subprocess_kwargs
from .export_planner import ExportMode, ExportPlan, PlannedExportSegment


class _ExportWorker(QThread):
    progress = pyqtSignal(float, str, str)
    log = pyqtSignal(str, str)
    completed = pyqtSignal(bool, object, str)

    def __init__(self, plan: ExportPlan, parent=None):
        super().__init__(parent)
        self._plan = plan
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
        self._recent_output_lines: list[str] = []

    def cancel(self) -> None:
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    def run(self) -> None:
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self.completed.emit(False, [], "FFmpeg not found")
            return

        output_paths: list[str] = []
        temp_dir: Optional[tempfile.TemporaryDirectory] = None

        try:
            if self._plan.mode == ExportMode.SEPARATE:
                stage_count = len(self._plan.segments)
                for stage_index, segment in enumerate(self._plan.segments):
                    if self._cancelled:
                        raise RuntimeError("Cancelled")
                    self._export_segment(
                        ffmpeg_path,
                        segment,
                        segment.output_path,
                        stage_index,
                        stage_count,
                    )
                    output_paths.append(segment.output_path)
            else:
                if len(self._plan.segments) == 1:
                    segment = self._plan.segments[0]
                    self._export_segment(
                        ffmpeg_path,
                        segment,
                        self._plan.merged_output_path or segment.output_path,
                        0,
                        1,
                    )
                    output_paths.append(self._plan.merged_output_path or segment.output_path)
                else:
                    temp_dir = tempfile.TemporaryDirectory(prefix="trim-merge-")
                    temp_paths: list[str] = []
                    stage_count = len(self._plan.segments) + 1
                    for stage_index, segment in enumerate(self._plan.segments):
                        temp_output = str(
                            Path(temp_dir.name)
                            / f"segment_{stage_index + 1:03d}{Path(self._plan.source_path).suffix}"
                        )
                        self._export_segment(
                            ffmpeg_path,
                            segment,
                            temp_output,
                            stage_index,
                            stage_count,
                        )
                        temp_paths.append(temp_output)

                    merged_output = self._plan.merged_output_path or self._plan.segments[0].output_path
                    self._merge_segments(
                        ffmpeg_path,
                        temp_dir.name,
                        temp_paths,
                        merged_output,
                        len(self._plan.segments),
                        stage_count,
                    )
                    output_paths.append(merged_output)

            self.completed.emit(True, output_paths, "")
        except Exception as exc:
            message = str(exc)
            if message == "Cancelled":
                self.completed.emit(False, output_paths, "Cancelled")
            else:
                self.completed.emit(False, output_paths, message)
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()

    def _export_segment(
        self,
        ffmpeg_path: str,
        segment: PlannedExportSegment,
        output_path: str,
        stage_index: int,
        stage_count: int,
    ) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.001, segment.duration)
        cmd = self._build_trim_command(
            ffmpeg_path,
            self._plan.source_path,
            output_path,
            segment.start_time,
            segment.end_time,
            self._plan.lossless,
        )
        self.log.emit("info", f"Exporting {segment.label}")
        self._run_command(cmd, duration, stage_index, stage_count)

    def _merge_segments(
        self,
        ffmpeg_path: str,
        temp_dir: str,
        temp_paths: list[str],
        output_path: str,
        stage_index: int,
        stage_count: int,
    ) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        list_file = Path(temp_dir) / "concat.txt"
        list_file.write_text(
            "\n".join(f"file '{Path(path).as_posix()}'" for path in temp_paths),
            encoding="utf-8",
        )

        total_duration = sum(segment.duration for segment in self._plan.segments) or 0.001
        cmd = [
            ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            "-progress",
            "pipe:1",
            output_path,
        ]
        self.log.emit("info", f"Merging {len(temp_paths)} segment(s)")
        self._run_command(cmd, total_duration, stage_index, stage_count)

    def _run_command(
        self,
        cmd: list[str],
        duration: float,
        stage_index: int,
        stage_count: int,
    ) -> None:
        self._recent_output_lines.clear()
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            **get_subprocess_kwargs(),
        )

        current_time = 0.0
        if self._process.stdout:
            for line in self._process.stdout:
                if self._cancelled:
                    break
                stripped = line.strip()
                if stripped:
                    self._recent_output_lines.append(stripped)
                    if len(self._recent_output_lines) > 200:
                        self._recent_output_lines = self._recent_output_lines[-200:]

                if stripped.startswith("out_time_ms="):
                    try:
                        current_time = int(stripped.split("=", 1)[1]) / 1_000_000.0
                    except (TypeError, ValueError):
                        current_time = current_time
                elif stripped.startswith("speed="):
                    speed = stripped.split("=", 1)[1].strip()
                    stage_fraction = min(max(current_time / duration, 0.0), 0.999)
                    overall = ((stage_index + stage_fraction) / stage_count) * 100.0
                    self.progress.emit(overall, speed, "")

        self._process.wait()
        if self._cancelled:
            raise RuntimeError("Cancelled")
        if self._process.returncode != 0:
            raise RuntimeError(extract_ffmpeg_error("\n".join(self._recent_output_lines), "Export failed"))

    def _build_trim_command(
        self,
        ffmpeg_path: str,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        lossless: bool,
    ) -> list[str]:
        duration = max(0.001, end_time - start_time)
        if lossless:
            return [
                ffmpeg_path,
                "-y",
                "-ss",
                str(start_time),
                "-i",
                input_path,
                "-t",
                str(duration),
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                "-progress",
                "pipe:1",
                output_path,
            ]
        return [
            ffmpeg_path,
            "-y",
            "-i",
            input_path,
            "-ss",
            str(start_time),
            "-to",
            str(end_time),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-progress",
            "pipe:1",
            output_path,
        ]


class ExportManager(QObject):
    """Manager facade around the feature-local editor export worker."""

    started = pyqtSignal()
    progress = pyqtSignal(float, str, str)
    log = pyqtSignal(str, str)
    completed = pyqtSignal(bool, object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[_ExportWorker] = None

    def start(self, plan: ExportPlan) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self._worker = _ExportWorker(plan, self)
        self._worker.progress.connect(self.progress)
        self._worker.log.connect(self.log)
        self._worker.completed.connect(self._on_completed)
        self._worker.start()
        self.started.emit()

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _on_completed(self, success: bool, outputs: object, error: str) -> None:
        self.completed.emit(success, outputs, error)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
