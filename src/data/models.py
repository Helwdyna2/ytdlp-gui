"""Data models for the application."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict


# =============================================================================
# Download Models
# =============================================================================


class DownloadStatus(Enum):
    """Status of a download."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class Download:
    """Download history record."""

    url: str
    id: Optional[int] = None
    title: Optional[str] = None
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    status: DownloadStatus = DownloadStatus.COMPLETED
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row) -> "Download":
        """Create Download from database row."""
        return cls(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            output_path=row["output_path"],
            file_size=row["file_size"],
            status=DownloadStatus(row["status"]),
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
        )


@dataclass
class OutputConfig:
    """Download configuration settings."""

    output_dir: str
    concurrent_limit: int = 3
    force_overwrite: bool = False
    video_only: bool = False
    cookies_path: Optional[str] = None
    filename_templates: Dict[str, str] = field(default_factory=dict)
    default_template: str = "%(title)s"


@dataclass
class Session:
    """Session state for recovery."""

    pending_urls: List[str]
    output_dir: str
    concurrent_limit: int = 3
    force_overwrite: bool = False
    video_only: bool = False
    cookies_path: Optional[str] = None
    id: Optional[int] = None
    completed_urls: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_row(cls, row) -> "Session":
        """Create Session from database row."""
        import json

        return cls(
            id=row["id"],
            pending_urls=json.loads(row["pending_urls"]),
            completed_urls=json.loads(row["completed_urls"])
            if row["completed_urls"]
            else [],
            output_dir=row["output_dir"],
            concurrent_limit=row["concurrent_limit"],
            force_overwrite=bool(row["force_overwrite"]),
            video_only=bool(row["video_only"]),
            cookies_path=row["cookies_path"],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"])
            if row["updated_at"]
            else datetime.now(),
        )

    def to_output_config(self) -> OutputConfig:
        """Convert session to OutputConfig."""
        return OutputConfig(
            output_dir=self.output_dir,
            concurrent_limit=self.concurrent_limit,
            force_overwrite=self.force_overwrite,
            video_only=self.video_only,
            cookies_path=self.cookies_path,
        )


@dataclass
class ProgressInfo:
    """Progress information for a download."""

    url: str
    status: str = "downloading"
    percent: float = 0.0
    speed: float = 0.0
    downloaded: int = 0
    total: int = 0
    eta: int = 0
    filename: str = ""
    title: Optional[str] = None

    @property
    def speed_str(self) -> str:
        """Get formatted speed string."""
        from ..utils.formatters import format_speed

        return format_speed(self.speed)

    @property
    def eta_str(self) -> str:
        """Get formatted ETA string."""
        from ..utils.formatters import format_eta

        return format_eta(self.eta)

    @property
    def size_str(self) -> str:
        """Get formatted size string (downloaded / total)."""
        from ..utils.formatters import format_size

        return f"{format_size(self.downloaded)} / {format_size(self.total)}"


# =============================================================================
# Sort & Convert Models
# =============================================================================


class SortCriterion(Enum):
    """Criteria for sorting video files into folders."""

    FPS = "fps"
    RESOLUTION = "resolution"
    ORIENTATION = "orientation"
    CODEC = "codec"
    BITRATE = "bitrate"


class RenameToken(Enum):
    """Tokens available for batch file renaming."""

    ORIGINAL = "original"  # Original filename (without extension)
    INDEX = "index"  # Sequential index number
    DATE_MODIFIED = "date_modified"  # File modification date
    RESOLUTION = "resolution"  # Video resolution (e.g., 1920x1080)
    FPS = "fps"  # Frame rate
    CODEC = "codec"  # Video codec
    DURATION = "duration"  # Video duration
    BITRATE = "bitrate"  # Video bitrate
    CUSTOM_TEXT = "custom_text"  # User-defined text


@dataclass
class RenameConfig:
    """Configuration for batch file renaming."""

    token_order: List[RenameToken] = field(default_factory=list)
    token_enabled: Dict[str, bool] = field(default_factory=dict)
    separator: str = "_"  # Separator between tokens
    custom_text: str = ""  # Value for CUSTOM_TEXT token
    index_start: int = 1  # Starting index for INDEX token
    index_padding: int = 2  # Zero-padding for index (e.g., 01, 001)
    date_format: str = "%Y-%m-%d"  # Format for DATE_MODIFIED token
    find_text: str = ""  # Text to find (for find/replace)
    replace_text: str = ""  # Text to replace with
    case_sensitive: bool = False  # Case-sensitive find/replace
    use_regex: bool = False  # Use regex for find/replace


class ConversionStatus(Enum):
    """Status of a conversion job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VideoMetadata:
    """Metadata extracted from a video file via ffprobe."""

    file_path: str
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    audio_codec: str = ""
    bitrate: int = 0
    duration: float = 0.0
    file_size: int = 0
    original_subfolder: str = ""  # Relative path from scan root

    @property
    def resolution(self) -> str:
        """
        Get exact resolution label (e.g., '1920x1080').

        Uses exact dimensions to ensure precise sorting for tools like Topaz
        that are sensitive to mixed resolutions in batch processing.
        """
        return f"{self.width}x{self.height}"

    @property
    def resolution_category(self) -> str:
        """Get resolution category label (e.g., '1080p', '4K') for display purposes."""
        if self.height >= 2160:
            return "4K"
        elif self.height >= 1440:
            return "1440p"
        elif self.height >= 1080:
            return "1080p"
        elif self.height >= 720:
            return "720p"
        elif self.height >= 480:
            return "480p"
        elif self.height >= 360:
            return "360p"
        else:
            return f"{self.height}p"

    @property
    def orientation(self) -> str:
        """Get orientation (horizontal, vertical, square)."""
        if self.width > self.height:
            return "horizontal"
        elif self.height > self.width:
            return "vertical"
        else:
            return "square"

    @property
    def fps_label(self) -> str:
        """
        Get exact FPS label for sorting (e.g., '29.970fps', '30.000fps').

        Uses 3 decimal places to distinguish between frame rates like:
        - 29.970 fps (NTSC drop-frame)
        - 30.000 fps (true 30fps)
        - 23.976 fps (film)
        - 24.000 fps (true 24fps)
        - 59.940 fps (NTSC 60i field rate)
        - 60.000 fps (true 60fps)

        This precision is critical for batch processing in tools like Topaz
        that are sensitive to mixed frame rates.
        """
        return f"{self.fps:.3f}fps"

    @property
    def fps_category(self) -> str:
        """Get rounded FPS category (e.g., '30fps', '60fps') for display purposes."""
        rounded = round(self.fps)
        return f"{rounded}fps"

    @property
    def bitrate_label(self) -> str:
        """Get bitrate label (e.g., '5Mbps')."""
        mbps = self.bitrate / 1_000_000
        if mbps >= 1:
            return f"{mbps:.1f}Mbps"
        else:
            kbps = self.bitrate / 1000
            return f"{kbps:.0f}kbps"


@dataclass
class ConversionConfig:
    """Configuration for video conversion."""

    output_codec: str = "h264"  # h264 or hevc
    crf_value: int = 23  # 0-51, lower = better quality
    preset: str = "medium"  # ultrafast to veryslow
    use_hardware_accel: bool = False
    hardware_encoder: Optional[str] = None  # nvenc, amf, qsv
    output_resolution: Optional[str] = None  # e.g. "1080p" or "vertical:1080p"
    audio_mode: str = "copy"  # copy or none
    frame_rate: Optional[str] = None  # e.g. "29.97"
    output_dir: Optional[str] = None


@dataclass
class ConversionJob:
    """A video conversion job record."""

    input_path: str
    output_path: str
    id: Optional[int] = None
    status: ConversionStatus = ConversionStatus.PENDING
    output_codec: str = "h264"
    crf_value: int = 23
    preset: str = "medium"
    hardware_encoder: Optional[str] = None
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    input_size: int = 0
    output_size: int = 0
    duration: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    source_codec: Optional[str] = None
    ffmpeg_command: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "ConversionJob":
        """Create ConversionJob from database row."""
        return cls(
            id=row["id"],
            input_path=row["input_path"],
            output_path=row["output_path"],
            status=ConversionStatus(row["status"]),
            output_codec=row["output_codec"],
            crf_value=row["crf_value"],
            preset=row["preset"],
            hardware_encoder=row["hardware_encoder"],
            progress_percent=row["progress_percent"],
            error_message=row["error_message"],
            input_size=row["input_size"] or 0,
            output_size=row["output_size"] or 0,
            duration=row["duration"] or 0.0,
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
            source_codec=row["source_codec"] if "source_codec" in row.keys() else None,
            ffmpeg_command=row["ffmpeg_command"] if "ffmpeg_command" in row.keys() else None,
        )


# =============================================================================
# Match Videos Models
# =============================================================================


class MatchStatus(Enum):
    """Status of a video file match attempt."""

    PENDING = "pending"
    SEARCHING = "searching"
    MATCHED = "matched"
    MULTIPLE_MATCHES = "multiple_matches"
    NO_MATCH = "no_match"
    RENAMED = "renamed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class SceneMetadata:
    """Metadata for a matched scene from ThePornDB or StashDB."""

    title: str
    studio: str
    performers: List[str]
    date: Optional[str] = None
    duration: Optional[int] = None  # seconds
    stashdb_id: Optional[str] = None
    porndb_id: Optional[str] = None
    source_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    source_database: str = ""  # "stashdb" or "porndb"


@dataclass
class ParsedFilename:
    """Result of parsing a video filename."""

    original: str
    studio: Optional[str] = None
    performers: List[str] = field(default_factory=list)
    title: Optional[str] = None
    preserved_tags: List[str] = field(default_factory=list)  # Missionary, BJ, etc.
    quality_indicators: List[str] = field(default_factory=list)  # 1080p, 4K, etc.
    search_queries: List[str] = field(default_factory=list)  # Generated search terms


@dataclass
class MatchResult:
    """Result of matching a local file to online databases."""

    file_path: str
    original_filename: str
    status: MatchStatus = MatchStatus.PENDING
    # Parsed from filename
    parsed: Optional[ParsedFilename] = None
    # Search results
    matches: List[SceneMetadata] = field(default_factory=list)
    selected_match: Optional[SceneMetadata] = None
    confidence: float = 0.0  # 0.0 to 1.0
    # Output
    new_filename: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class MatchConfig:
    """Configuration for the matching process."""

    source_dir: str = ""
    output_format: str = "{studio} - {performer} - {title}"
    search_porndb: bool = True
    search_stashdb: bool = True
    porndb_first: bool = True  # ThePornDB prioritized per user preference
    preserve_tags: bool = True  # Keep position tags in filename
    include_already_named: bool = False  # User option for already-named files
    custom_studios: List[str] = field(default_factory=list)  # User-added studios
    skip_keywords: List[str] = field(default_factory=list)  # Ignore in search parsing


# =============================================================================
# Extract URLs Models
# =============================================================================


@dataclass
class ExtractUrlsConfig:
    """Configuration for URL extraction."""

    output_dir: str
    profile_dir: str
    auto_scroll_enabled: bool = True
    max_scrolls: int = 200
    idle_limit: int = 5
    delay_ms: int = 800
    max_bounce_attempts: int = 3


# =============================================================================
# Trim Videos Models
# =============================================================================


class TrimStatus(Enum):
    """Status of a trim job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrimConfig:
    """Configuration for video trimming."""

    start_time: float = 0.0  # Start time in seconds
    end_time: Optional[float] = None  # End time in seconds (None = to end of video)
    lossless: bool = True  # Use -c copy (no re-encode) - fast but keyframe-limited
    output_dir: Optional[str] = None  # Custom output directory
    suffix: str = "_trimmed"  # Suffix for output filename


@dataclass
class TrimJob:
    """A video trim job record."""

    input_path: str
    output_path: str
    start_time: float  # Start time in seconds
    end_time: float  # End time in seconds
    original_duration: float  # Original video duration in seconds
    id: Optional[int] = None
    status: TrimStatus = TrimStatus.PENDING
    lossless: bool = True
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def trim_duration(self) -> float:
        """Get the duration of the trimmed segment."""
        return self.end_time - self.start_time

    @classmethod
    def from_row(cls, row) -> "TrimJob":
        """Create TrimJob from database row."""
        return cls(
            id=row["id"],
            input_path=row["input_path"],
            output_path=row["output_path"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            original_duration=row["original_duration"],
            status=TrimStatus(row["status"]),
            lossless=bool(row["lossless"]),
            progress_percent=row["progress_percent"],
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
        )
