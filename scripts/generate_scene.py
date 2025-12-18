#!/usr/bin/env python3
"""
CLI Script: Generate Scene
==========================

Command-line tool for generating a single scene.

Usage:
    python scripts/generate_scene.py --character protagonist --action "walking" --duration 5
    python scripts/generate_scene.py -c protagonist -a "talking on phone" -l office
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow import VideoProducer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a video scene with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c protagonist -a "walking through city"
  %(prog)s -c protagonist -a "sitting at desk" -l office -d 10
  %(prog)s --prompt "A sunset over ocean" --duration 5
        """,
    )

    # Character-based generation
    parser.add_argument(
        "-c", "--character",
        help="Character ID from character bible",
    )
    parser.add_argument(
        "-a", "--action",
        help="What the character is doing",
    )
    parser.add_argument(
        "-l", "--location",
        help="Location ID from character bible",
    )

    # Direct prompt (alternative to character-based)
    parser.add_argument(
        "--prompt",
        help="Direct prompt (bypasses character bible)",
    )

    # Video settings
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=5,
        help="Video duration in seconds (default: 5)",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        choices=["16:9", "9:16", "1:1", "4:3"],
        help="Aspect ratio (default: 16:9)",
    )
    parser.add_argument(
        "--resolution",
        default="720p",
        choices=["480p", "720p", "1080p"],
        help="Resolution (default: 720p)",
    )

    # Provider settings
    parser.add_argument(
        "--provider",
        default="fal",
        help="API provider (default: fal)",
    )
    parser.add_argument(
        "--model",
        default="kling-2.5",
        help="Model to use (default: kling-2.5)",
    )

    # Reference images
    parser.add_argument(
        "-r", "--reference",
        action="append",
        help="Reference image path (can be specified multiple times)",
    )

    # Episode tracking
    parser.add_argument(
        "--episode",
        help="Episode ID for tracking",
    )
    parser.add_argument(
        "--scene-number",
        type=int,
        help="Scene number within episode",
    )

    # Output
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: auto-generated)",
    )

    # Config
    parser.add_argument(
        "--config",
        help="Path to config file",
    )
    parser.add_argument(
        "--bible",
        help="Path to character bible",
    )

    return parser.parse_args()


async def main():
    """Main CLI entry point."""
    args = parse_args()

    # Validate arguments
    if not args.prompt and not args.character:
        print("Error: Either --character or --prompt is required")
        sys.exit(1)

    if args.character and not args.action:
        print("Error: --action is required when using --character")
        sys.exit(1)

    # Check API key
    if not os.getenv("FAL_API_KEY") and args.provider == "fal":
        print("Error: FAL_API_KEY environment variable not set")
        print("Get your key at: https://fal.ai/")
        sys.exit(1)

    # Paths
    project_root = Path(__file__).parent.parent
    config_path = args.config or project_root / "config" / "defaults.yaml"
    bible_path = args.bible or project_root / "context" / "character_bible.yaml"
    output_path = project_root / "output"

    # Initialize producer
    producer = VideoProducer(
        config_path=config_path if Path(config_path).exists() else None,
        character_bible_path=bible_path if Path(bible_path).exists() else None,
        output_path=output_path,
        provider=args.provider,
    )

    print("=" * 50)
    print("AI Video Scene Generator")
    print("=" * 50)

    try:
        async with producer:
            if args.prompt:
                # Direct prompt generation
                print(f"\nPrompt: {args.prompt}")
                print(f"Duration: {args.duration}s")
                print(f"Model: {args.model}")

                result = await producer.quick_generate(
                    prompt=args.prompt,
                    reference_image=args.reference[0] if args.reference else None,
                    duration=args.duration,
                    model=args.model,
                    aspect_ratio=args.aspect_ratio,
                )
            else:
                # Character-based generation
                print(f"\nCharacter: {args.character}")
                print(f"Action: {args.action}")
                if args.location:
                    print(f"Location: {args.location}")
                print(f"Duration: {args.duration}s")
                print(f"Model: {args.model}")

                result = await producer.generate_scene(
                    character_id=args.character,
                    action=args.action,
                    location_id=args.location,
                    episode_id=args.episode,
                    scene_number=args.scene_number,
                    duration=args.duration,
                    model=args.model,
                    resolution=args.resolution,
                    aspect_ratio=args.aspect_ratio,
                )

            print("\n" + "-" * 50)
            print(f"Status: {result.status.value}")

            if result.video_path:
                print(f"Video saved: {result.video_path}")
            if result.video_url:
                print(f"Video URL: {result.video_url}")
            if result.seed:
                print(f"Seed: {result.seed}")
            if result.error_message:
                print(f"Error: {result.error_message}")

            print("=" * 50)

            # Exit code based on status
            sys.exit(0 if result.status.value == "completed" else 1)

    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
