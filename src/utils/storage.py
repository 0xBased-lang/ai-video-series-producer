"""
Storage Utilities
=================

Helper functions for file and metadata storage.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


def save_video(
    video_data: bytes,
    output_path: Union[str, Path],
) -> str:
    """
    Save video data to a file.

    Args:
        video_data: Raw video bytes
        output_path: Path to save the video

    Returns:
        Path to saved video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(video_data)

    logger.info(f"Video saved to {output_path}")
    return str(output_path)


def save_metadata(
    metadata: Dict[str, Any],
    output_path: Union[str, Path],
    format: str = "json",
) -> str:
    """
    Save metadata to a file.

    Args:
        metadata: Metadata dictionary
        output_path: Path to save the metadata
        format: Output format (json or yaml)

    Returns:
        Path to saved metadata
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Add timestamp
    metadata["saved_at"] = datetime.now().isoformat()

    if format == "yaml":
        import yaml
        with open(output_path, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False)
    else:
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

    logger.debug(f"Metadata saved to {output_path}")
    return str(output_path)


def load_metadata(
    path: Union[str, Path],
) -> Optional[Dict[str, Any]]:
    """
    Load metadata from a file.

    Args:
        path: Path to metadata file

    Returns:
        Metadata dictionary, or None if failed
    """
    path = Path(path)

    if not path.exists():
        return None

    try:
        if path.suffix in (".yml", ".yaml"):
            import yaml
            with open(path, "r") as f:
                return yaml.safe_load(f)
        else:
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load metadata from {path}: {e}")
        return None


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_filename(
    prefix: str = "video",
    suffix: str = ".mp4",
    include_timestamp: bool = True,
) -> str:
    """
    Generate a unique filename.

    Args:
        prefix: Filename prefix
        suffix: File extension
        include_timestamp: Whether to include timestamp

    Returns:
        Generated filename
    """
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}{suffix}"
    else:
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"


def get_file_size(path: Union[str, Path]) -> Optional[int]:
    """
    Get the size of a file in bytes.

    Args:
        path: File path

    Returns:
        File size in bytes, or None if file doesn't exist
    """
    path = Path(path)
    if path.exists():
        return path.stat().st_size
    return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
