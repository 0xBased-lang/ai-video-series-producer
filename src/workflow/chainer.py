"""
Scene Chainer
=============

Handles frame chaining for maintaining visual continuity
across multiple video clips in a series.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChainContext:
    """Context passed between chained scenes."""
    last_frame_path: str
    seed: Optional[int] = None
    prompt_suffix: str = ""
    reference_images: List[str] = None

    def __post_init__(self):
        if self.reference_images is None:
            self.reference_images = []


class SceneChainer:
    """
    Manages frame chaining between video clips.

    Ensures visual continuity by:
    - Extracting last frames from previous clips
    - Using them as first frames for next clips
    - Maintaining consistent style and character
    """

    def __init__(
        self,
        frames_path: Union[str, Path] = "./output/frames",
        overlap_frames: int = 1,
    ):
        """
        Initialize the scene chainer.

        Args:
            frames_path: Directory for storing extracted frames
            overlap_frames: Number of frames to overlap
        """
        self.frames_path = Path(frames_path)
        self.frames_path.mkdir(parents=True, exist_ok=True)
        self.overlap_frames = overlap_frames

    def extract_frame(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        position: str = "last",  # "first", "last", or timestamp like "00:00:05"
        quality: int = 95,
    ) -> Optional[str]:
        """
        Extract a frame from a video.

        Args:
            video_path: Path to the video file
            output_path: Where to save the extracted frame
            position: Which frame to extract
            quality: JPEG quality (1-100)

        Returns:
            Path to extracted frame, or None if failed
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            logger.error(f"Video not found: {video_path}")
            return None

        try:
            # Get video duration for "last" position
            if position == "last":
                duration = self._get_video_duration(video_path)
                if duration:
                    position = str(max(0, duration - 0.1))
                else:
                    position = "99999"  # ffmpeg will use last frame

            elif position == "first":
                position = "0"

            # Build ffmpeg command
            cmd = [
                "ffmpeg", "-y",
                "-ss", position,
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", str(int((100 - quality) / 3) + 1),  # Convert to ffmpeg scale
                str(output_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if output_path.exists():
                logger.info(f"Extracted frame to {output_path}")
                return str(output_path)
            else:
                logger.error(f"Frame extraction failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Frame extraction error: {e}")
            return None

    def _get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get the duration of a video in seconds."""
        try:
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
            return float(result.stdout.strip())
        except Exception:
            return None

    def create_chain_context(
        self,
        video_path: Union[str, Path],
        scene_id: str,
        seed: Optional[int] = None,
        reference_images: Optional[List[str]] = None,
    ) -> Optional[ChainContext]:
        """
        Create chain context from a completed video.

        Args:
            video_path: Path to the completed video
            scene_id: Scene identifier
            seed: Generation seed (for reproducibility)
            reference_images: Reference images used

        Returns:
            ChainContext for the next scene
        """
        # Extract last frame
        frame_path = self.frames_path / f"{scene_id}_last.jpg"
        extracted = self.extract_frame(video_path, frame_path, position="last")

        if not extracted:
            return None

        return ChainContext(
            last_frame_path=extracted,
            seed=seed,
            prompt_suffix=", continuing from previous scene",
            reference_images=reference_images or [],
        )

    def prepare_continuation_prompt(
        self,
        base_prompt: str,
        chain_context: Optional[ChainContext] = None,
    ) -> str:
        """
        Prepare a prompt for continuation that maintains context.

        Args:
            base_prompt: The base scene prompt
            chain_context: Context from previous scene

        Returns:
            Modified prompt for seamless continuation
        """
        if not chain_context:
            return base_prompt

        # Add continuation cues
        continuation_cues = [
            "Seamless continuation from previous shot",
            "Maintaining visual continuity",
            chain_context.prompt_suffix,
        ]

        prefix = ". ".join(filter(None, continuation_cues))
        return f"{prefix}. {base_prompt}"

    def concatenate_videos(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
        transition: str = "none",  # none, crossfade, fade
        transition_duration: float = 0.5,
    ) -> Optional[str]:
        """
        Concatenate multiple video clips into one.

        Args:
            video_paths: List of video paths to concatenate
            output_path: Output video path
            transition: Transition type between clips
            transition_duration: Duration of transition in seconds

        Returns:
            Path to concatenated video, or None if failed
        """
        if not video_paths:
            return None

        output_path = Path(output_path)

        try:
            if transition == "none":
                # Simple concatenation using concat demuxer
                return self._concat_simple(video_paths, output_path)
            else:
                # Use filter for transitions
                return self._concat_with_transitions(
                    video_paths, output_path, transition, transition_duration
                )

        except Exception as e:
            logger.error(f"Concatenation failed: {e}")
            return None

    def _concat_simple(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Path,
    ) -> Optional[str]:
        """Simple concatenation without transitions."""
        # Create file list
        list_path = output_path.with_suffix(".txt")
        with open(list_path, "w") as f:
            for vp in video_paths:
                f.write(f"file '{Path(vp).absolute()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-c", "copy",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        list_path.unlink()  # Clean up

        if output_path.exists():
            logger.info(f"Concatenated {len(video_paths)} videos to {output_path}")
            return str(output_path)

        logger.error(f"Concatenation failed: {result.stderr}")
        return None

    def _concat_with_transitions(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Path,
        transition: str,
        transition_duration: float,
    ) -> Optional[str]:
        """Concatenation with transitions (crossfade, etc.)."""
        # Build complex filter for transitions
        # This is a simplified version - full implementation would be more complex

        inputs = []
        filter_parts = []

        for i, vp in enumerate(video_paths):
            inputs.extend(["-i", str(vp)])
            filter_parts.append(f"[{i}:v]")

        if transition == "crossfade":
            # Simple crossfade filter
            filter_str = "".join(filter_parts) + f"concat=n={len(video_paths)}:v=1:a=0[outv]"
        else:
            # Fade in/out
            filter_str = "".join(filter_parts) + f"concat=n={len(video_paths)}:v=1:a=0[outv]"

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[outv]",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if output_path.exists():
            return str(output_path)

        logger.error(f"Transition concatenation failed: {result.stderr}")
        return None

    def create_thumbnail(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        size: str = "320x180",
    ) -> Optional[str]:
        """
        Create a thumbnail from a video.

        Args:
            video_path: Path to video
            output_path: Where to save thumbnail
            size: Thumbnail dimensions

        Returns:
            Path to thumbnail
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        # Extract frame from 1 second in (or first frame)
        duration = self._get_video_duration(video_path)
        timestamp = min(1.0, (duration or 0) / 2)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-vf", f"scale={size}",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True)

        if output_path.exists():
            return str(output_path)
        return None
