"""Export planning and warning policy for Trim editor exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .models import EditorSegment, EditorSession


class ExportMode(str, Enum):
    """Supported editor export modes."""

    SEPARATE = "separate"
    MERGED = "merged"


@dataclass(slots=True)
class ExportWarning:
    """Policy warning shown before risky exports."""

    code: str
    message: str


@dataclass(slots=True)
class PlannedExportSegment:
    """Concrete segment export instruction."""

    segment_id: str
    label: str
    start_time: float
    end_time: float
    output_path: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)


@dataclass(slots=True)
class ExportPlan:
    """Resolved editor export plan."""

    source_path: str
    mode: ExportMode
    lossless: bool
    segments: list[PlannedExportSegment]
    warnings: list[ExportWarning] = field(default_factory=list)
    merged_output_path: Optional[str] = None

    @property
    def requires_confirmation(self) -> bool:
        return bool(self.warnings)


class ExportPlanner:
    """Build export plans from the current editor session."""

    _INTRAFRAME_CODECS = {
        "prores",
        "dnxhd",
        "dnxhr",
        "mjpeg",
        "ffv1",
        "utvideo",
        "rawvideo",
        "huffyuv",
    }

    def build_plan(
        self,
        session: EditorSession,
        *,
        mode: ExportMode,
        lossless: bool,
        output_target: Optional[str],
        keyframe_times: Optional[list[float]] = None,
        source_metadata: Optional[dict] = None,
    ) -> ExportPlan:
        if not session.source_path:
            raise ValueError("No source is loaded")

        enabled_segments = session.enabled_segments()
        if not enabled_segments:
            raise ValueError("No enabled segments available for export")

        source_path = Path(session.source_path)
        warnings = self._build_warnings(
            session=session,
            enabled_segments=enabled_segments,
            lossless=lossless,
            keyframe_times=keyframe_times or [],
            source_metadata=source_metadata or {},
            mode=mode,
        )

        if mode == ExportMode.SEPARATE:
            base_dir = Path(output_target) if output_target else source_path.parent
            segments = self._build_separate_paths(enabled_segments, source_path, base_dir)
            return ExportPlan(
                source_path=session.source_path,
                mode=mode,
                lossless=lossless,
                segments=segments,
                warnings=warnings,
            )

        merged_output_path = self._resolve_merged_output_path(source_path, output_target)
        segments = [
            PlannedExportSegment(
                segment_id=segment.id,
                label=segment.display_label(index),
                start_time=segment.start_time,
                end_time=segment.end_time,
                output_path=merged_output_path,
            )
            for index, segment in enumerate(enabled_segments)
        ]
        return ExportPlan(
            source_path=session.source_path,
            mode=mode,
            lossless=lossless,
            segments=segments,
            warnings=warnings,
            merged_output_path=merged_output_path,
        )

    def _build_separate_paths(
        self,
        enabled_segments: list[EditorSegment],
        source_path: Path,
        base_dir: Path,
    ) -> list[PlannedExportSegment]:
        paths: list[PlannedExportSegment] = []
        for index, segment in enumerate(enabled_segments):
            label = segment.display_label(index)
            slug = self._slugify_label(label)
            suffix = f"_{index + 1:03d}"
            output_path = base_dir / f"{source_path.stem}_trimmed{suffix}_{slug}{source_path.suffix}"
            paths.append(
                PlannedExportSegment(
                    segment_id=segment.id,
                    label=label,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    output_path=str(output_path),
                )
            )
        return paths

    def _resolve_merged_output_path(
        self, source_path: Path, output_target: Optional[str]
    ) -> str:
        if output_target:
            target_path = Path(output_target)
            if target_path.suffix:
                return str(target_path)
            return str(target_path / f"{source_path.stem}_merged{source_path.suffix}")
        return str(source_path.parent / f"{source_path.stem}_merged{source_path.suffix}")

    def _build_warnings(
        self,
        *,
        session: EditorSession,
        enabled_segments: list[EditorSegment],
        lossless: bool,
        keyframe_times: list[float],
        source_metadata: dict,
        mode: ExportMode,
    ) -> list[ExportWarning]:
        warnings: list[ExportWarning] = []
        if not lossless:
            return warnings

        codec = str(
            source_metadata.get("codec")
            or source_metadata.get("codec_name")
            or ""
        ).lower()
        is_intraframe = codec in self._INTRAFRAME_CODECS

        off_keyframe_segments = []
        if keyframe_times:
            for segment in enabled_segments:
                if self._segment_has_off_keyframe_boundary(
                    session.duration, segment, keyframe_times
                ):
                    off_keyframe_segments.append(segment)
        elif not is_intraframe:
            warnings.append(
                ExportWarning(
                    code="copy-boundary-unknown",
                    message=(
                        "Lossless copy boundaries were not checked against keyframes yet. "
                        "Start/end positions may shift slightly on export."
                    ),
                )
            )

        if off_keyframe_segments:
            warnings.append(
                ExportWarning(
                    code="copy-boundary-risk",
                    message=(
                        f"{len(off_keyframe_segments)} segment(s) do not start/end on a nearby keyframe. "
                        "Lossless export may include extra frames around those cuts."
                    ),
                )
            )

        if mode == ExportMode.MERGED and len(enabled_segments) > 1 and lossless:
            warnings.append(
                ExportWarning(
                    code="merge-copy-risk",
                    message=(
                        "Merged lossless export uses temporary segments plus concat. "
                        "If boundaries drift at keyframes, the merged result will preserve that drift."
                    ),
                )
            )

        return warnings

    def _segment_has_off_keyframe_boundary(
        self,
        duration: float,
        segment: EditorSegment,
        keyframe_times: list[float],
        tolerance: float = 0.12,
    ) -> bool:
        boundary_times = []
        if segment.start_time > tolerance:
            boundary_times.append(segment.start_time)
        if duration - segment.end_time > tolerance:
            boundary_times.append(segment.end_time)

        for boundary in boundary_times:
            if not any(abs(boundary - keyframe) <= tolerance for keyframe in keyframe_times):
                return True
        return False

    def _slugify_label(self, label: str) -> str:
        cleaned = "".join(
            character.lower() if character.isalnum() else "_"
            for character in label.strip()
        )
        collapsed = "_".join(part for part in cleaned.split("_") if part)
        return collapsed or "segment"
