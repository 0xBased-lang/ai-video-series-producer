"""
Workflow Orchestration
======================

High-level orchestration for video series production.

Components:
- VideoProducer: Main entry point for video generation
- SceneChainer: Handles frame chaining for scene continuity
- QualityValidator: Automated quality checks
"""

from .generator import VideoProducer
from .chainer import SceneChainer
from .validator import QualityValidator

__all__ = [
    "VideoProducer",
    "SceneChainer",
    "QualityValidator",
]
