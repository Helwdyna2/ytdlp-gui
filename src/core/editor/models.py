"""Editor session models for Trim's multi-segment workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4


@dataclass(slots=True)
class EditorSegment:
    """Editable time range within a single source."""

    start_time: float
    end_time: float
    id: str = field(default_factory=lambda: uuid4().hex)
    enabled: bool = True
    label: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Return the segment duration in seconds."""
        return max(0.0, self.end_time - self.start_time)

    def display_label(self, index: int) -> str:
        """Return a stable fallback label for UI display."""
        return self.label.strip() or f"Segment {index + 1}"


@dataclass(slots=True)
class EditorSession:
    """In-memory editor state for the current trim source."""

    source_path: Optional[str] = None
    duration: float = 0.0
    segments: list[EditorSegment] = field(default_factory=list)
    selected_segment_id: Optional[str] = None

    def clear(self) -> None:
        """Reset the session to an empty state."""
        self.source_path = None
        self.duration = 0.0
        self.segments.clear()
        self.selected_segment_id = None

    def load_source(self, source_path: str, duration: float) -> None:
        """Initialize the session with a single keep-segment."""
        clean_duration = max(0.0, duration)
        self.source_path = source_path
        self.duration = clean_duration
        self.segments = [EditorSegment(start_time=0.0, end_time=clean_duration)]
        self.selected_segment_id = self.segments[0].id if self.segments else None

    @property
    def has_source(self) -> bool:
        """Return True when a source is loaded."""
        return bool(self.source_path) and self.duration > 0

    def get_segment(self, segment_id: Optional[str]) -> Optional[EditorSegment]:
        """Return a segment by ID."""
        if not segment_id:
            return None
        for segment in self.segments:
            if segment.id == segment_id:
                return segment
        return None

    @property
    def selected_segment(self) -> Optional[EditorSegment]:
        """Return the currently selected segment."""
        return self.get_segment(self.selected_segment_id)

    def select_segment(self, segment_id: Optional[str]) -> Optional[EditorSegment]:
        """Select a segment by ID and return it."""
        segment = self.get_segment(segment_id)
        if segment is not None:
            self.selected_segment_id = segment.id
            return segment

        if self.segments:
            self.selected_segment_id = self.segments[0].id
            return self.segments[0]

        self.selected_segment_id = None
        return None

    def find_segment_at(self, position: float) -> Optional[EditorSegment]:
        """Return the segment containing the given time."""
        for segment in self.segments:
            if segment.start_time <= position <= segment.end_time:
                return segment
        return None

    def update_selected_range(self, start: float, end: float) -> Optional[EditorSegment]:
        """Update the selected segment boundaries within safe limits."""
        segment = self.selected_segment
        if segment is None:
            return None

        index = self.segments.index(segment)
        prev_end = self.segments[index - 1].end_time if index > 0 else 0.0
        next_start = (
            self.segments[index + 1].start_time
            if index + 1 < len(self.segments)
            else self.duration
        )

        clamped_start = max(prev_end, min(start, self.duration))
        clamped_end = min(next_start, max(end, clamped_start))

        if clamped_end <= clamped_start:
            clamped_end = min(next_start, clamped_start + 0.001)
            clamped_start = max(prev_end, min(clamped_start, clamped_end - 0.001))

        segment.start_time = clamped_start
        segment.end_time = clamped_end
        return segment

    def split_at(self, position: float) -> Optional[tuple[EditorSegment, EditorSegment]]:
        """Split the selected segment at the given position."""
        segment = self.selected_segment or self.find_segment_at(position)
        if segment is None:
            return None

        if position <= segment.start_time + 0.001:
            return None
        if position >= segment.end_time - 0.001:
            return None

        index = self.segments.index(segment)
        trailing = EditorSegment(
            start_time=position,
            end_time=segment.end_time,
            enabled=segment.enabled,
        )
        segment.end_time = position
        self.segments.insert(index + 1, trailing)
        self.selected_segment_id = trailing.id
        return segment, trailing

    def toggle_segment_enabled(self, segment_id: Optional[str] = None) -> Optional[EditorSegment]:
        """Flip enabled state for the requested or selected segment."""
        segment = self.get_segment(segment_id) or self.selected_segment
        if segment is None:
            return None
        segment.enabled = not segment.enabled
        return segment

    def set_segment_enabled(self, segment_id: str, enabled: bool) -> Optional[EditorSegment]:
        """Set enabled state directly."""
        segment = self.get_segment(segment_id)
        if segment is None:
            return None
        segment.enabled = enabled
        return segment

    def set_segment_label(self, segment_id: str, label: str) -> Optional[EditorSegment]:
        """Update the user-visible label for a segment."""
        segment = self.get_segment(segment_id)
        if segment is None:
            return None
        segment.label = label.strip()
        return segment

    def enabled_segments(self) -> list[EditorSegment]:
        """Return enabled segments in timeline order."""
        return [segment for segment in self.segments if segment.enabled]
