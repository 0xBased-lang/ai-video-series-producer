"""
Provider Factory
================

Factory for creating video generation provider instances.
"""

import logging
from typing import Optional, List, Dict, Type

from .base import BaseVideoProvider

logger = logging.getLogger(__name__)

# Registry of available providers
_PROVIDERS: Dict[str, Type[BaseVideoProvider]] = {}


def register_provider(name: str):
    """Decorator to register a provider class."""
    def decorator(cls: Type[BaseVideoProvider]):
        _PROVIDERS[name.lower()] = cls
        return cls
    return decorator


def get_provider(
    name: str,
    api_key: Optional[str] = None,
    **kwargs,
) -> BaseVideoProvider:
    """
    Get a video generation provider instance.

    Args:
        name: Provider name (e.g., 'fal', 'google', 'runway', 'piapi')
        api_key: Optional API key (otherwise read from environment)
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured provider instance

    Raises:
        ValueError: If provider name is not recognized
    """
    name_lower = name.lower()

    if name_lower not in _PROVIDERS:
        # Try to import the provider module
        try:
            if name_lower == "fal":
                from .fal import FalProvider
            elif name_lower == "google":
                from .google import GoogleVeoProvider
            elif name_lower == "runway":
                from .runway import RunwayProvider
            elif name_lower == "piapi":
                from .piapi import PiAPIProvider
            elif name_lower == "minimax":
                from .minimax import MiniMaxProvider
            elif name_lower == "luma":
                from .luma import LumaProvider
            elif name_lower == "replicate":
                from .replicate import ReplicateProvider
            elif name_lower == "aimlapi":
                from .aimlapi import AimlApiProvider
            elif name_lower == "openai":
                from .openai_sora import OpenAISoraProvider
            else:
                raise ValueError(f"Unknown provider: {name}")
        except ImportError as e:
            raise ValueError(f"Provider '{name}' not available: {e}")

    provider_class = _PROVIDERS.get(name_lower)
    if provider_class is None:
        raise ValueError(f"Provider '{name}' not registered")

    return provider_class(api_key=api_key, **kwargs)


def list_providers() -> List[str]:
    """
    List all available provider names.

    Returns:
        List of provider names
    """
    # Ensure all providers are imported
    try:
        from . import fal, google, runway, piapi, minimax, luma, replicate
    except ImportError:
        pass

    return list(_PROVIDERS.keys())


def get_best_provider(
    requirement: str = "character_consistency",
    **kwargs,
) -> BaseVideoProvider:
    """
    Get the best provider for a specific requirement.

    Args:
        requirement: What capability is most important
            - 'character_consistency': Best character preservation
            - 'multi_reference': Most reference images supported
            - 'long_duration': Longest video support
            - 'audio': Native audio generation
            - 'lora': LoRA fine-tuning support
            - 'value': Best price/quality ratio

    Returns:
        Best provider for the requirement
    """
    # Provider rankings by capability
    rankings = {
        "character_consistency": ["runway", "minimax", "fal"],
        "multi_reference": ["fal", "google", "piapi"],  # Kling supports 4
        "long_duration": ["openai", "google", "fal"],
        "audio": ["google", "openai", "fal"],
        "lora": ["replicate", "fal"],
        "value": ["fal", "piapi", "luma"],
    }

    providers_to_try = rankings.get(requirement, ["fal"])

    for provider_name in providers_to_try:
        try:
            provider = get_provider(provider_name, **kwargs)
            if provider.api_key:  # Only return if configured
                return provider
        except (ValueError, ImportError):
            continue

    # Fallback to fal
    return get_provider("fal", **kwargs)
