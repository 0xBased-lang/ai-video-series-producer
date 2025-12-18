"""
Utilities
=========

Helper functions and utilities for the AI Video Series Producer.
"""

from .image_utils import encode_image, resize_image, extract_frame
from .storage import save_video, save_metadata, load_metadata

__all__ = [
    "encode_image",
    "resize_image",
    "extract_frame",
    "save_video",
    "save_metadata",
    "load_metadata",
]
