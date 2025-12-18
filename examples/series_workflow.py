#!/usr/bin/env python3
"""
Series Workflow Example
=======================

Complete example of generating a video series with consistent characters.
"""

import asyncio
import os
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow import VideoProducer


async def main():
    """Generate a video series with consistent characters."""

    # Check for API key
    if not os.getenv("FAL_API_KEY"):
        print("Please set FAL_API_KEY environment variable")
        return

    # Initialize producer with character bible
    project_root = Path(__file__).parent.parent
    producer = VideoProducer(
        config_path=project_root / "config" / "defaults.yaml",
        character_bible_path=project_root / "context" / "character_bible.yaml",
        output_path=project_root / "output",
        provider="fal",
    )

    print("=== Video Series Production ===")
    print(f"Series: {producer.character_bible.series_name}")
    print(f"Characters: {list(producer.character_bible.characters.keys())}")
    print(f"Locations: {list(producer.character_bible.locations.keys())}")

    # Define episode scenes
    episode_scenes = [
        {
            "character_id": "protagonist",
            "action": "entering the office building, looking determined",
            "location_id": "office",
            "duration": 5,
        },
        {
            "character_id": "protagonist",
            "action": "walking to desk and sitting down",
            "location_id": "office",
            "duration": 5,
        },
        {
            "character_id": "protagonist",
            "action": "opening laptop and starting to work",
            "location_id": "office",
            "duration": 5,
        },
    ]

    print(f"\nGenerating {len(episode_scenes)} scenes...")
    print("-" * 50)

    try:
        async with producer:
            # Generate the episode
            results = await producer.generate_episode(
                series_id="my_series",
                episode_number=1,
                scenes=episode_scenes,
                title="A New Day",
            )

            # Print results
            for i, result in enumerate(results):
                print(f"\nScene {i + 1}:")
                print(f"  Status: {result.status.value}")
                if result.video_path:
                    print(f"  Video: {result.video_path}")
                if result.error_message:
                    print(f"  Error: {result.error_message}")

            # Summary
            completed = sum(1 for r in results if r.status.value == "completed")
            print(f"\n{'=' * 50}")
            print(f"Completed: {completed}/{len(results)} scenes")

    except Exception as e:
        print(f"Error: {e}")


async def quick_single_scene():
    """Quick single scene generation without full series setup."""

    project_root = Path(__file__).parent.parent
    producer = VideoProducer(
        output_path=project_root / "output",
        provider="fal",
    )

    # Load character bible
    producer.load_character_bible(project_root / "context" / "character_bible.yaml")

    async with producer:
        # Generate a single scene
        result = await producer.generate_scene(
            character_id="protagonist",
            action="walking through a busy city street",
            location_id="street",
            duration=5,
        )

        print(f"Status: {result.status.value}")
        if result.video_url:
            print(f"Video: {result.video_url}")


if __name__ == "__main__":
    # Run the full series workflow
    asyncio.run(main())

    # Or run a quick single scene:
    # asyncio.run(quick_single_scene())
