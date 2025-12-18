"""
Image Utilities
===============

Helper functions for image processing.
"""

import base64
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)


def encode_image(
    image_path: Union[str, Path],
    format: str = "auto",
) -> Tuple[str, str]:
    """
    Encode an image to base64.

    Args:
        image_path: Path to the image file
        format: Output format (auto, jpeg, png, webp)

    Returns:
        Tuple of (base64_data, mime_type)
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Determine MIME type
    ext = path.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime_type = mime_types.get(ext, "image/jpeg")

    # Read and encode
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return data, mime_type


def to_data_uri(image_path: Union[str, Path]) -> str:
    """
    Convert an image to a data URI.

    Args:
        image_path: Path to the image file

    Returns:
        Data URI string (data:image/jpeg;base64,...)
    """
    data, mime_type = encode_image(image_path)
    return f"data:{mime_type};base64,{data}"


def resize_image(
    image_path: Union[str, Path],
    output_path: Union[str, Path],
    max_size: int = 1024,
    quality: int = 90,
) -> str:
    """
    Resize an image while maintaining aspect ratio.

    Args:
        image_path: Path to input image
        output_path: Path for output image
        max_size: Maximum dimension (width or height)
        quality: JPEG quality (1-100)

    Returns:
        Path to resized image
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            # Calculate new size
            width, height = img.size
            if width > height:
                if width > max_size:
                    new_width = max_size
                    new_height = int(height * max_size / width)
                else:
                    new_width, new_height = width, height
            else:
                if height > max_size:
                    new_height = max_size
                    new_width = int(width * max_size / height)
                else:
                    new_width, new_height = width, height

            # Resize
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_path.suffix.lower() in (".jpg", ".jpeg"):
                resized.save(output_path, "JPEG", quality=quality)
            else:
                resized.save(output_path)

            return str(output_path)

    except ImportError:
        logger.warning("Pillow not installed, cannot resize image")
        return str(image_path)


def extract_frame(
    video_path: Union[str, Path],
    output_path: Union[str, Path],
    position: str = "last",
    quality: int = 95,
) -> Optional[str]:
    """
    Extract a frame from a video file.

    Requires ffmpeg to be installed.

    Args:
        video_path: Path to video file
        output_path: Path for output image
        position: "first", "last", or timestamp (e.g., "00:00:05")
        quality: JPEG quality

    Returns:
        Path to extracted frame, or None if failed
    """
    import subprocess

    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        logger.error(f"Video not found: {video_path}")
        return None

    try:
        # Get video duration for "last" position
        if position == "last":
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
            )
            duration = float(result.stdout.strip())
            position = str(max(0, duration - 0.1))

        elif position == "first":
            position = "0"

        # Extract frame
        output_path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", position,
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", str(int((100 - quality) / 3) + 1),
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

        if output_path.exists():
            return str(output_path)

    except subprocess.CalledProcessError as e:
        logger.error(f"Frame extraction failed: {e}")
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg.")
    except Exception as e:
        logger.error(f"Frame extraction error: {e}")

    return None


def get_image_dimensions(image_path: Union[str, Path]) -> Optional[Tuple[int, int]]:
    """
    Get the dimensions of an image.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (width, height), or None if failed
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return None
