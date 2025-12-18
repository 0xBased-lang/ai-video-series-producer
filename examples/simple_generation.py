#!/usr/bin/env python3
"""
Simple Generation Example
=========================

Basic example of generating a video with the AI Video Series Producer.
"""

import asyncio
import os
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import get_provider
from src.api.base import GenerationRequest


async def main():
    """Simple video generation example."""

    # Check for API key
    if not os.getenv("FAL_API_KEY"):
        print("Please set FAL_API_KEY environment variable")
        print("Get your key at: https://fal.ai/")
        return

    # Get the fal.ai provider
    provider = get_provider("fal")

    print("=== Simple Video Generation ===")
    print(f"Provider: {provider.provider_name}")
    print(f"Available models: {provider.supported_models}")

    # Create a simple request
    request = GenerationRequest(
        prompt="A beautiful sunset over the ocean, waves gently rolling, "
               "cinematic lighting, professional quality, 4K",
        duration=5,
        aspect_ratio="16:9",
        model="kling-2.5",
    )

    print(f"\nPrompt: {request.prompt}")
    print(f"Duration: {request.duration}s")
    print(f"Model: {request.model}")
    print("\nGenerating video...")

    try:
        # Generate the video
        result = await provider.generate_video(request)

        print(f"\nStatus: {result.status.value}")

        if result.video_url:
            print(f"Video URL: {result.video_url}")

            # Download the video
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "simple_example.mp4"

            print(f"\nDownloading to {output_path}...")
            await provider.download_video(result, output_path)
            print(f"Downloaded: {output_path}")

        if result.error_message:
            print(f"Error: {result.error_message}")

    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
