# AI Video Series Producer

A comprehensive framework for creating AI-generated video series with **consistent characters**, **style preservation**, and **context management** across episodes.

## Features

- **Multi-Provider Support**: fal.ai, Google Veo, Runway, Kling, MiniMax Hailuo, Luma, Replicate
- **Fluent Builder API**: Clean, readable series setup with method chaining
- **Character Bible**: Define characters once, use everywhere with consistent prompts
- **Style Presets**: Cinematic, Anime, Documentary, Noir, Sci-Fi styles built-in
- **Quality Presets**: Draft, Balanced, High, Cinematic quality levels
- **Scene Chaining**: Automatic frame continuity between clips
- **Context Preservation**: Track generation history for consistency
- **Security Built-in**: Path validation, input sanitization, safe error handling
- **n8n Integration**: Workflow automation templates included
- **CLI & API**: Use from command line or as a library

## What's New in v0.2.0

- **Clean Series Builder**: Fluent API for setting up video series
- **Character Builder**: Type-safe character creation with prompts
- **Style System**: Visual presets and custom style configuration
- **Core Module**: Centralized config, exceptions, and security utilities
- **Improved Architecture**: Reduced code duplication, better error handling

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/ai-video-series-producer.git
cd ai-video-series-producer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env and add your API keys
```

**Required Keys (at least one):**
- `FAL_API_KEY` - Get from [fal.ai](https://fal.ai/) (recommended)
- `GOOGLE_API_KEY` - Get from [Google AI Studio](https://aistudio.google.com/)
- `RUNWAY_API_KEY` - Get from [Runway](https://runwayml.com/)

### 3. Create Your First Series (New Clean API)

```python
from src import create_series, CharacterBuilder, QualityPreset

# Create a series with the fluent builder
series = (
    create_series("My Adventure Series")
    .description("An epic journey of discovery")
    .genre("adventure")

    # Visual style (choose one)
    .cinematic_style()  # or .anime_style(), .noir_style(), .scifi_style()

    # Quality preset
    .high_quality()  # or .draft_quality(), .cinematic_quality()

    # Add characters
    .character(
        CharacterBuilder("hero")
        .name("Alex Chen")
        .age("30")
        .gender("female")
        .hair("auburn", "shoulder-length wavy")
        .eyes("green")
        .outfit("leather jacket, dark jeans")
        .feature("small scar on left cheek")
        .reference("front", "refs/alex_front.jpg")
        .build()
    )
    .character(
        CharacterBuilder("mentor")
        .name("Marcus")
        .age("55")
        .gender("male")
        .hair("gray", "short")
        .outfit("tweed jacket, reading glasses")
        .build()
    )

    # Add locations
    .location("cafe", "Coffee Shop", "cozy coffee shop, warm lighting, brick walls")
    .location("street", "City Street", "busy urban street at golden hour")

    # Production settings
    .provider("fal")
    .model("kling-2.5")
    .output_path("./output/my_series")

    # Pre-plan episodes
    .episode(
        title="The Beginning",
        scenes=[
            {"character_id": "hero", "action": "sitting alone, looking thoughtful", "location_id": "cafe"},
            {"character_id": "mentor", "action": "approaching the table", "location_id": "cafe"},
        ]
    )

    .build()
)

# Save configuration for later
create_series("My Series").save("./my_series.yaml")

# Load existing configuration
loaded = load_series("./my_series.yaml").build()
```

### 4. Quick Generation (CLI)

```bash
# Simple generation
python scripts/generate_scene.py \
  --prompt "A beautiful sunset over the ocean, cinematic" \
  --duration 5

# Character-based generation
python scripts/generate_scene.py \
  --character protagonist \
  --action "walking through the city" \
  --location street \
  --duration 5
```

## Project Structure

```
ai-video-series-producer/
├── .env.example              # API key template
├── config/
│   ├── apis.yaml            # Provider configurations
│   └── defaults.yaml        # Default settings
├── context/
│   └── character_bible.yaml # Character & location definitions
├── src/
│   ├── api/                 # Provider integrations
│   │   ├── base.py         # Base provider class
│   │   ├── fal.py          # fal.ai (unified)
│   │   ├── google.py       # Google Veo
│   │   ├── runway.py       # Runway Gen-4
│   │   └── ...
│   ├── context/             # Context management
│   │   ├── character_manager.py
│   │   └── scene_tracker.py
│   └── workflow/            # Orchestration
│       ├── generator.py    # VideoProducer
│       └── chainer.py      # Frame chaining
├── workflows/
│   └── n8n/                 # n8n workflow templates
├── examples/                # Example scripts
└── scripts/                 # CLI tools
```

## Usage Examples

### Python API

```python
import asyncio
from src.workflow import VideoProducer

async def main():
    # Initialize with character bible
    producer = VideoProducer(
        character_bible_path="context/character_bible.yaml",
        output_path="./output",
        provider="fal",
    )

    async with producer:
        # Generate a scene
        result = await producer.generate_scene(
            character_id="protagonist",
            action="walking through the city at sunset",
            location_id="street",
            duration=5,
        )

        print(f"Video: {result.video_path}")

asyncio.run(main())
```

### Generate an Episode

```python
async with producer:
    results = await producer.generate_episode(
        series_id="my_series",
        episode_number=1,
        scenes=[
            {"character_id": "protagonist", "action": "entering office"},
            {"character_id": "protagonist", "action": "sitting at desk"},
            {"character_id": "protagonist", "action": "opening laptop"},
        ],
        title="A New Day",
    )
```

### CLI Usage

```bash
# Simple prompt
python scripts/generate_scene.py --prompt "A sunset" --duration 5

# Character-based
python scripts/generate_scene.py \
  -c protagonist \
  -a "running through rain" \
  -l street \
  -d 10 \
  --model kling-2.6

# With reference image
python scripts/generate_scene.py \
  -c protagonist \
  -a "smiling at camera" \
  -r references/characters/alex_front.jpg
```

## Character Bible

Define your characters and locations in `context/character_bible.yaml`:

```yaml
characters:
  protagonist:
    name: "Alex"
    role: "protagonist"
    visual:
      age: "early 30s"
      gender: "female"
      hair: "auburn, shoulder-length"
      eyes: "green, expressive"
    references:
      front: "./references/characters/alex_front.jpg"
      profile: "./references/characters/alex_profile.jpg"
    prompt_fragments:
      identity: "30yo woman with auburn hair, green eyes"
      outfit: "wearing leather jacket, white t-shirt"

locations:
  office:
    name: "Alex's Office"
    description: "Modern office with city view"
    prompt_fragments:
      setting: "modern office, large windows, city skyline"
```

## Supported Providers

| Provider | Models | Reference Images | Best For |
|----------|--------|------------------|----------|
| **fal.ai** | Kling 2.5/2.6, Veo 3, Hailuo, Wan | Up to 4 | Unified API, best value |
| **Google Veo** | Veo 3.1, Veo 2 | Up to 3 | Best reference control |
| **Runway** | Gen-4 Turbo | 1 | Persistent memory |
| **PiAPI** | Kling 2.0-2.5 | Up to 4 | Kling specialist |
| **Replicate** | HunyuanVideo, Wan2.1 | LoRA support | Open source + LoRA |

## n8n Integration

Import the workflow template and trigger via webhook:

```bash
# Start the webhook handler
uvicorn examples.n8n_webhook_handler:app --port 8000

# Or use the n8n workflow directly
# Import workflows/n8n/video_series_workflow.json
```

**Webhook endpoints:**
- `POST /webhook/video-series/generate` - Single scene
- `POST /webhook/video-series/batch` - Episode
- `GET /webhook/video-series/status/{job_id}` - Check status

## Frame Chaining

The system automatically chains scenes for continuity:

1. Generate Scene 1
2. Extract last frame from Scene 1
3. Use last frame as first frame for Scene 2
4. Add "continuation" to prompt
5. Generate Scene 2 with visual continuity

```python
# Automatic chaining in episodes
results = await producer.generate_episode(
    series_id="my_series",
    episode_number=1,
    scenes=[...],  # Each scene chains from previous
)
```

## Configuration

### `config/defaults.yaml`

```yaml
generation:
  preferred_provider: "fal"
  preferred_model: "kling-2.5"

video:
  duration: 5
  resolution: "720p"
  aspect_ratio: "16:9"

consistency:
  character_weight: 0.7
  use_last_frame: true
```

### Environment Variables

```bash
# Primary API keys
FAL_API_KEY=your_key
GOOGLE_API_KEY=your_key
RUNWAY_API_KEY=your_key

# Optional
REPLICATE_API_TOKEN=your_token
```

## Tips for Best Results

### Character Consistency

1. **Use reference images**: Always provide 2-4 reference images
2. **Consistent prompts**: Use the same descriptive terms
3. **Frame chaining**: Enable for multi-scene sequences
4. **Train LoRA**: For long series, consider LoRA training

### Prompt Writing

```
Good: "30yo woman with auburn hair, green eyes, wearing leather jacket,
      walking confidently through busy city street, golden hour lighting,
      cinematic, 35mm film"

Bad:  "woman walking"
```

### Model Selection

- **Kling 2.5**: Best value, 4 references
- **Kling 2.6**: Best quality + audio
- **Veo 3.1**: Best reference control
- **Runway Gen-4**: Best for camera control

## Troubleshooting

### "Character looks different in each scene"

- Add more reference images (2-4)
- Use consistent prompt fragments from character bible
- Enable frame chaining
- Consider LoRA training for long series

### "API timeout"

- Video generation takes 30s-5min
- Use background generation and poll status
- Check provider status pages

### "Video quality is low"

- Increase resolution to 1080p
- Use quality-focused models (Kling 2.6, Veo 3.1)
- Add style modifiers to prompt

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## License

MIT License - see LICENSE file

## Resources

- [fal.ai Documentation](https://fal.ai/docs)
- [Google Veo API](https://ai.google.dev/gemini-api/docs/video)
- [Runway API](https://runwayml.com/api)
- [n8n Documentation](https://docs.n8n.io/)
