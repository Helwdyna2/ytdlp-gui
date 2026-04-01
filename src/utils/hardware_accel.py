"""Hardware acceleration detection for video encoding."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from .ffmpeg_utils import get_available_encoders, is_hardware_encoder_available
from .constants import HARDWARE_ENCODERS

logger = logging.getLogger(__name__)


@dataclass
class HardwareEncoder:
    """Represents an available hardware encoder."""
    name: str  # e.g., "nvenc"
    display_name: str  # e.g., "NVIDIA NVENC"
    h264_encoder: str  # e.g., "h264_nvenc"
    hevc_encoder: str  # e.g., "hevc_nvenc"
    h264_available: bool
    hevc_available: bool


# Display names for each hardware acceleration type
HARDWARE_DISPLAY_NAMES = {
    "nvenc": "NVIDIA NVENC",
    "amf": "AMD AMF",
    "qsv": "Intel Quick Sync",
    "videotoolbox": "Apple VideoToolbox",
}


def detect_hardware_encoders() -> List[HardwareEncoder]:
    """
    Detect all available hardware encoders on the system.
    
    Returns:
        List of available HardwareEncoder objects.
    """
    available_encoders = []
    all_encoders = get_available_encoders()
    
    for hw_name, codecs in HARDWARE_ENCODERS.items():
        h264_encoder = codecs.get("h264", "")
        hevc_encoder = codecs.get("hevc", "")
        
        # Check if encoders are listed
        h264_listed = h264_encoder in all_encoders
        hevc_listed = hevc_encoder in all_encoders
        
        if not h264_listed and not hevc_listed:
            continue
        
        # Test if they actually work (hardware might not be present)
        h264_works = False
        hevc_works = False
        
        if h264_listed:
            h264_works = is_hardware_encoder_available(h264_encoder)
            
        if hevc_listed:
            hevc_works = is_hardware_encoder_available(hevc_encoder)
        
        if h264_works or hevc_works:
            encoder = HardwareEncoder(
                name=hw_name,
                display_name=HARDWARE_DISPLAY_NAMES.get(hw_name, hw_name.upper()),
                h264_encoder=h264_encoder,
                hevc_encoder=hevc_encoder,
                h264_available=h264_works,
                hevc_available=hevc_works,
            )
            available_encoders.append(encoder)
            logger.info(f"Hardware encoder detected: {encoder.display_name} "
                       f"(H.264: {h264_works}, HEVC: {hevc_works})")
    
    return available_encoders


def get_best_hardware_encoder(codec: str = "h264") -> Optional[HardwareEncoder]:
    """
    Get the best available hardware encoder for the given codec.
    
    Priority order: NVENC > AMF > QSV > VideoToolbox
    
    Args:
        codec: Either "h264" or "hevc"
        
    Returns:
        Best available HardwareEncoder, or None if none available.
    """
    priority_order = ["nvenc", "amf", "qsv", "videotoolbox"]
    available = detect_hardware_encoders()
    
    for hw_name in priority_order:
        for encoder in available:
            if encoder.name == hw_name:
                if codec == "h264" and encoder.h264_available:
                    return encoder
                elif codec == "hevc" and encoder.hevc_available:
                    return encoder
    
    return None


def get_compatible_hardware_encoders(
    codec: str, encoders: Optional[List[HardwareEncoder]] = None
) -> List[HardwareEncoder]:
    """
    Get hardware encoders compatible with the requested output codec.

    Args:
        codec: Output codec name such as "h264" or "hevc"
        encoders: Optional pre-detected encoders to filter

    Returns:
        List of compatible hardware encoders.
    """
    available_encoders = encoders if encoders is not None else get_cached_hardware_encoders()

    if codec == "h264":
        return [encoder for encoder in available_encoders if encoder.h264_available]
    if codec == "hevc":
        return [encoder for encoder in available_encoders if encoder.hevc_available]
    return []


def get_encoder_for_codec(hardware_encoder: Optional[HardwareEncoder], 
                          codec: str, 
                          use_hardware: bool = True) -> str:
    """
    Get the FFmpeg encoder name for a codec.
    
    Args:
        hardware_encoder: HardwareEncoder to use, or None for software
        codec: "h264" or "hevc"
        use_hardware: Whether to use hardware acceleration
        
    Returns:
        FFmpeg encoder name (e.g., "libx264", "h264_nvenc")
    """
    if use_hardware and hardware_encoder:
        if codec == "h264" and hardware_encoder.h264_available:
            return hardware_encoder.h264_encoder
        elif codec == "hevc" and hardware_encoder.hevc_available:
            return hardware_encoder.hevc_encoder
    
    # Fall back to software encoders
    if codec == "hevc":
        return "libx265"
    else:
        return "libx264"


# Cached result to avoid repeated detection
_cached_encoders: Optional[List[HardwareEncoder]] = None


def get_cached_hardware_encoders() -> List[HardwareEncoder]:
    """
    Get hardware encoders with caching (detection is expensive).
    
    Returns:
        List of available hardware encoders.
    """
    global _cached_encoders
    if _cached_encoders is None:
        _cached_encoders = detect_hardware_encoders()
    return _cached_encoders


def clear_encoder_cache() -> None:
    """Clear the cached encoder detection results."""
    global _cached_encoders
    _cached_encoders = None
