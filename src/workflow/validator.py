"""
Quality Validator
=================

Automated quality checks for generated videos.
Validates character consistency, style adherence, and technical quality.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Quality assessment report for a video."""

    # Overall scores (0.0 - 1.0)
    overall_score: float = 0.0
    character_consistency_score: float = 0.0
    style_consistency_score: float = 0.0
    motion_quality_score: float = 0.0
    technical_quality_score: float = 0.0

    # Flags
    passed: bool = False
    requires_review: bool = False
    auto_approved: bool = False

    # Issues found
    issues: List[str] = None
    warnings: List[str] = None

    # Recommendations
    recommendations: List[str] = None

    def __post_init__(self):
        self.issues = self.issues or []
        self.warnings = self.warnings or []
        self.recommendations = self.recommendations or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_score": self.overall_score,
            "character_consistency_score": self.character_consistency_score,
            "style_consistency_score": self.style_consistency_score,
            "motion_quality_score": self.motion_quality_score,
            "technical_quality_score": self.technical_quality_score,
            "passed": self.passed,
            "requires_review": self.requires_review,
            "auto_approved": self.auto_approved,
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


class QualityValidator:
    """
    Validates quality of generated videos.

    Can use AI models (Claude/GPT) for visual inspection,
    or rule-based checks for technical validation.
    """

    def __init__(
        self,
        ai_provider: Optional[str] = None,  # "claude" or "openai"
        min_quality_score: float = 0.7,
        auto_approve_threshold: float = 0.9,
        auto_reject_threshold: float = 0.5,
    ):
        """
        Initialize the quality validator.

        Args:
            ai_provider: AI provider for visual analysis
            min_quality_score: Minimum score to pass
            auto_approve_threshold: Score above which to auto-approve
            auto_reject_threshold: Score below which to auto-reject
        """
        self.ai_provider = ai_provider
        self.min_quality_score = min_quality_score
        self.auto_approve_threshold = auto_approve_threshold
        self.auto_reject_threshold = auto_reject_threshold

    async def validate_video(
        self,
        video_path: Union[str, Path],
        reference_images: Optional[List[str]] = None,
        expected_character: Optional[str] = None,
        expected_style: Optional[str] = None,
    ) -> QualityReport:
        """
        Validate a generated video.

        Args:
            video_path: Path to the video file
            reference_images: Reference images for comparison
            expected_character: Expected character description
            expected_style: Expected style description

        Returns:
            QualityReport with assessment results
        """
        report = QualityReport()

        video_path = Path(video_path)
        if not video_path.exists():
            report.issues.append(f"Video file not found: {video_path}")
            return report

        # Technical quality checks
        tech_score = await self._check_technical_quality(video_path)
        report.technical_quality_score = tech_score

        # If AI provider is configured, do visual analysis
        if self.ai_provider and reference_images:
            visual_scores = await self._analyze_visual_quality(
                video_path,
                reference_images,
                expected_character,
                expected_style,
            )
            report.character_consistency_score = visual_scores.get("character", 0.7)
            report.style_consistency_score = visual_scores.get("style", 0.7)
            report.motion_quality_score = visual_scores.get("motion", 0.7)
        else:
            # Default scores without AI analysis
            report.character_consistency_score = 0.7
            report.style_consistency_score = 0.7
            report.motion_quality_score = 0.7

        # Calculate overall score
        report.overall_score = (
            report.character_consistency_score * 0.35 +
            report.style_consistency_score * 0.25 +
            report.motion_quality_score * 0.25 +
            report.technical_quality_score * 0.15
        )

        # Determine pass/fail status
        if report.overall_score >= self.auto_approve_threshold:
            report.passed = True
            report.auto_approved = True
        elif report.overall_score >= self.min_quality_score:
            report.passed = True
            report.requires_review = True
        elif report.overall_score <= self.auto_reject_threshold:
            report.passed = False
            report.issues.append("Quality score below acceptable threshold")
        else:
            report.passed = False
            report.requires_review = True

        # Add recommendations
        self._add_recommendations(report)

        return report

    async def _check_technical_quality(
        self,
        video_path: Path,
    ) -> float:
        """
        Check technical quality of the video.

        Validates:
        - File integrity
        - Resolution
        - Duration
        - Codec
        """
        score = 1.0
        issues = []

        try:
            import subprocess

            # Get video info using ffprobe
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,duration,codec_name",
                    "-of", "json",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return 0.5  # File might be corrupted

            import json
            info = json.loads(result.stdout)
            stream = info.get("streams", [{}])[0]

            width = stream.get("width", 0)
            height = stream.get("height", 0)

            # Check resolution
            if width < 480 or height < 360:
                score -= 0.2
                issues.append("Low resolution")

            # Check duration
            duration = float(stream.get("duration", 0))
            if duration < 1:
                score -= 0.3
                issues.append("Very short duration")

        except Exception as e:
            logger.warning(f"Technical quality check failed: {e}")
            score = 0.6

        return max(0.0, score)

    async def _analyze_visual_quality(
        self,
        video_path: Path,
        reference_images: List[str],
        expected_character: Optional[str],
        expected_style: Optional[str],
    ) -> Dict[str, float]:
        """
        Analyze visual quality using AI.

        This is a placeholder for AI-based analysis.
        In production, this would:
        1. Extract frames from the video
        2. Send frames + references to Claude/GPT vision
        3. Ask for consistency analysis
        4. Parse and return scores
        """
        # Placeholder implementation
        # In production, implement with actual AI vision API

        logger.info("Visual quality analysis would use AI here")

        return {
            "character": 0.75,
            "style": 0.75,
            "motion": 0.75,
        }

    def _add_recommendations(self, report: QualityReport) -> None:
        """Add recommendations based on scores."""
        if report.character_consistency_score < 0.7:
            report.recommendations.append(
                "Consider using more reference images or adjusting prompt"
            )

        if report.style_consistency_score < 0.7:
            report.recommendations.append(
                "Review style modifiers in character bible"
            )

        if report.motion_quality_score < 0.7:
            report.recommendations.append(
                "Try a different model or adjust motion-related prompt terms"
            )

        if report.technical_quality_score < 0.7:
            report.recommendations.append(
                "Check video generation parameters (resolution, duration)"
            )

    async def batch_validate(
        self,
        video_paths: List[Union[str, Path]],
        **kwargs,
    ) -> List[QualityReport]:
        """
        Validate multiple videos.

        Args:
            video_paths: List of video paths
            **kwargs: Arguments passed to validate_video

        Returns:
            List of QualityReport objects
        """
        reports = []
        for path in video_paths:
            report = await self.validate_video(path, **kwargs)
            reports.append(report)
        return reports

    def get_summary(self, reports: List[QualityReport]) -> Dict[str, Any]:
        """
        Get summary statistics from multiple reports.

        Args:
            reports: List of QualityReport objects

        Returns:
            Summary statistics
        """
        if not reports:
            return {}

        passed_count = sum(1 for r in reports if r.passed)
        auto_approved_count = sum(1 for r in reports if r.auto_approved)
        review_needed_count = sum(1 for r in reports if r.requires_review)

        avg_score = sum(r.overall_score for r in reports) / len(reports)

        return {
            "total_videos": len(reports),
            "passed": passed_count,
            "failed": len(reports) - passed_count,
            "auto_approved": auto_approved_count,
            "requires_review": review_needed_count,
            "average_score": round(avg_score, 3),
            "pass_rate": round(passed_count / len(reports), 3),
        }
