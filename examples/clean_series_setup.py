#!/usr/bin/env python3
"""
Clean Series Setup Example
==========================

This example demonstrates the new fluent builder API for creating
video series with clean, readable code.

The new API provides:
- Fluent builder pattern for series creation
- Type-safe character and style definitions
- Quality presets for different use cases
- Easy export/import of series configurations
"""

import asyncio
from pathlib import Path

# Import the new clean API
from src import (
    create_series,
    load_series,
    quick_series,
    CharacterBuilder,
    StylePresets,
    QualityPreset,
)


def example_basic_series():
    """
    Example 1: Basic series with minimal setup.

    Perfect for quick testing or simple projects.
    """
    print("\n" + "=" * 60)
    print("Example 1: Quick Series Setup")
    print("=" * 60)

    # One-liner for simple series
    series = quick_series(
        name="Test Series",
        protagonist_name="Alex",
        protagonist_description="A brave adventurer",
        style="cinematic",
        quality="balanced",
    )

    print(f"Created: {series.name}")
    print(f"Protagonist: {series.character_ids}")
    print(f"Quality: {series.quality_preset}")


def example_full_series():
    """
    Example 2: Full series with all features.

    Shows the complete fluent builder API.
    """
    print("\n" + "=" * 60)
    print("Example 2: Full Series Setup")
    print("=" * 60)

    series = (
        create_series("The Last Frontier")
        .description("A sci-fi adventure about humanity's expansion into deep space")
        .genre("science fiction")

        # Visual Style
        .scifi_style()
        .high_quality()

        # Main Character
        .character(
            CharacterBuilder("captain")
            .name("Captain Elena Vasquez")
            .as_protagonist()
            .age("35-40")
            .gender("female")
            .ethnicity("Latina")
            .hair("dark brown", "tied back in a practical bun")
            .eyes("intense brown")
            .feature("small scar above left eyebrow")
            .outfit("navy blue captain's uniform with silver insignia")
            .outfit_variant("casual", "gray tank top, cargo pants")
            .outfit_variant("EVA", "sleek white space suit with blue accents")
            .reference("front", "refs/elena_front.jpg")
            .reference("profile", "refs/elena_profile.jpg")
            .prompt_suffix("determined expression, confident posture")
            .build()
        )

        # Supporting Character
        .character(
            CharacterBuilder("engineer")
            .name("Dr. James Chen")
            .role("Chief Engineer")
            .age("45-50")
            .gender("male")
            .ethnicity("Asian")
            .hair("gray", "short cropped")
            .eyes("dark brown")
            .facial_hair("neat goatee")
            .outfit("oil-stained engineering jumpsuit")
            .feature("cybernetic left arm")
            .build()
        )

        # Antagonist
        .character(
            CharacterBuilder("admiral")
            .name("Admiral Marcus Stone")
            .as_antagonist()
            .age("55-60")
            .gender("male")
            .hair("silver", "slicked back")
            .eyes("cold gray")
            .outfit("black military uniform with medals")
            .prompt_prefix("imposing figure")
            .build()
        )

        # Locations
        .location(
            "bridge",
            "Ship's Bridge",
            "futuristic spaceship bridge with holographic displays, blue ambient lighting",
            reference_image="refs/bridge.jpg",
        )
        .location(
            "engineering",
            "Engineering Bay",
            "massive engine room with glowing reactor core, steam vents, industrial lighting",
        )
        .location(
            "space",
            "Deep Space",
            "vast starfield with distant nebula, planet visible in background",
        )

        # Production Settings
        .provider("fal")
        .model("kling-2.6")
        .duration(8)
        .widescreen()
        .output_path("./output/last_frontier")

        # Pre-planned episodes
        .episode(
            title="Departure",
            description="The crew prepares for their journey into unknown space",
            scenes=[
                {"character_id": "captain", "action": "giving orders on the bridge", "location_id": "bridge", "camera": "medium shot"},
                {"character_id": "engineer", "action": "checking engine readouts", "location_id": "engineering"},
                {"character_id": "captain", "action": "looking out at stars, contemplative", "location_id": "bridge", "camera": "close-up"},
            ],
        )
        .episode(
            title="First Contact",
            description="An unexpected signal changes everything",
            scenes=[
                {"character_id": "captain", "action": "receiving urgent transmission", "location_id": "bridge"},
                {"character_id": "admiral", "action": "appearing on holographic screen, threatening", "location_id": "bridge"},
            ],
        )

        .build()
    )

    print(f"Created: {series.name}")
    print(f"Genre: {series.genre}")
    print(f"Characters: {len(series.character_ids)}")
    print(f"Episodes: {len(series.episodes)}")
    print(f"Total scenes: {series.get_total_scenes()}")

    # Access character details
    captain = series._characters["captain"]
    print(f"\nProtagonist: {captain.name}")
    print(f"  Style: {captain.style.build_prompt_fragment()}")

    return series


def example_save_and_load():
    """
    Example 3: Save and load series configuration.

    Shows how to persist and restore series setup.
    """
    print("\n" + "=" * 60)
    print("Example 3: Save and Load")
    print("=" * 60)

    # Create a series
    builder = (
        create_series("Noir Detective")
        .description("A hardboiled detective story")
        .noir_style()
        .character(
            CharacterBuilder("detective")
            .name("Jack Morrison")
            .as_protagonist()
            .age("40")
            .gender("male")
            .hair("dark", "slicked back")
            .outfit("rumpled trench coat, fedora")
            .feature("cigarette in mouth")
            .build()
        )
        .location("office", "Detective's Office", "dimly lit office, venetian blinds casting shadows")
    )

    # Save to file
    config_path = Path("./output/noir_detective.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    builder.save(config_path)
    print(f"Saved configuration to: {config_path}")

    # Load from file
    loaded = load_series(config_path)
    series = loaded.build()
    print(f"Loaded: {series.name}")
    print(f"Characters: {list(loaded._characters.keys())}")


def example_style_presets():
    """
    Example 4: Using different style presets.

    Shows the available visual style presets.
    """
    print("\n" + "=" * 60)
    print("Example 4: Style Presets")
    print("=" * 60)

    presets = [
        ("Cinematic", StylePresets.cinematic()),
        ("Anime", StylePresets.anime()),
        ("Documentary", StylePresets.documentary()),
        ("Noir", StylePresets.noir()),
        ("Sci-Fi", StylePresets.scifi()),
    ]

    for name, style in presets:
        print(f"\n{name}:")
        print(f"  Aesthetic: {style.aesthetic}")
        print(f"  Mood: {style.mood}")
        print(f"  Style modifiers: {', '.join(style.style_modifiers[:3])}...")
        print(f"  Prompt fragment: {style.build_style_prompt()[:60]}...")


def example_quality_presets():
    """
    Example 5: Quality presets for different use cases.
    """
    print("\n" + "=" * 60)
    print("Example 5: Quality Presets")
    print("=" * 60)

    for preset in QualityPreset:
        settings = preset.get_settings()
        print(f"\n{preset.value.upper()}:")
        print(f"  Model: {settings['model']}")
        print(f"  Duration: {settings['duration']}s")
        print(f"  Resolution: {settings['resolution']}")
        print(f"  Audio: {settings['with_audio']}")


def example_character_prompt():
    """
    Example 6: Generate prompts for characters.

    Shows how the character system builds consistent prompts.
    """
    print("\n" + "=" * 60)
    print("Example 6: Character Prompts")
    print("=" * 60)

    # Create a detailed character
    character = (
        CharacterBuilder("hero")
        .name("Sarah")
        .age("28")
        .gender("female")
        .hair("red", "long wavy")
        .eyes("bright blue")
        .feature("freckles")
        .outfit("green hoodie, ripped jeans")
        .outfit_variant("formal", "elegant black dress")
        .prompt_suffix("confident, smiling")
        .build()
    )

    # Generate different prompts
    print(f"\nCharacter: {character.name}")
    print(f"\nDefault outfit:")
    prompt = character.build_prompt(
        action="walking through a park",
        location="city park at sunset",
        camera="medium tracking shot",
    )
    print(f"  {prompt}")

    print(f"\nFormal outfit:")
    prompt = character.build_prompt(
        action="entering a ballroom",
        location="grand ballroom",
        outfit_variant="formal",
        camera="wide shot",
    )
    print(f"  {prompt}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("AI Video Series Producer - Clean API Examples")
    print("=" * 60)

    example_basic_series()
    example_full_series()
    example_save_and_load()
    example_style_presets()
    example_quality_presets()
    example_character_prompt()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
