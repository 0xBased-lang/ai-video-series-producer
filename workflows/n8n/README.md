# n8n Workflow Integration

This directory contains n8n workflow templates for automating video series production.

## Setup

### 1. Install n8n

```bash
# Using npm
npm install n8n -g
n8n start

# Or using Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

### 2. Import Workflows

1. Open n8n at http://localhost:5678
2. Go to **Workflows** → **Import**
3. Upload `video_series_workflow.json`

### 3. Configure Credentials

In n8n, add credentials for:
- **HTTP Header Auth** - For API calls (fal.ai, PiAPI, etc.)
- **Webhook** - For receiving generation callbacks

### 4. Set Environment Variables

The workflow uses these environment variables:
- `FAL_API_KEY` - fal.ai API key
- `VIDEO_PRODUCER_WEBHOOK` - Your webhook URL for callbacks

## Available Workflows

### video_series_workflow.json

Main workflow for video series production:

```
┌─────────────────────────────────────────────────────────────────┐
│                  VIDEO SERIES PRODUCTION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Trigger]         [Process]           [Generate]               │
│                                                                 │
│  Webhook    ──→   Load Context   ──→   API Request             │
│  Manual           Build Prompt         (fal.ai/etc)             │
│  Schedule         Get References                                │
│                                                                 │
│       └──────────────┬──────────────┘                          │
│                      │                                          │
│                      ▼                                          │
│                                                                 │
│  [Post-Process]    [Store]            [Notify]                  │
│                                                                 │
│  Download Video    Save to S3    ──→  Slack/Discord            │
│  Extract Frame     Update DB          Webhook callback          │
│  Quality Check     Log metadata                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Webhook Endpoints

### Trigger Generation

```bash
POST /webhook/video-series/generate
Content-Type: application/json

{
  "character_id": "protagonist",
  "action": "walking through the city",
  "location_id": "street",
  "episode_id": "ep_001",
  "scene_number": 1,
  "duration": 5,
  "provider": "fal",
  "model": "kling-2.5"
}
```

### Batch Generation

```bash
POST /webhook/video-series/batch
Content-Type: application/json

{
  "episode_id": "ep_001",
  "scenes": [
    {"character_id": "protagonist", "action": "entering office"},
    {"character_id": "protagonist", "action": "sitting at desk"},
    {"character_id": "protagonist", "action": "looking at laptop"}
  ]
}
```

### Check Status

```bash
GET /webhook/video-series/status/{job_id}
```

## Custom Nodes

The workflow uses these HTTP Request configurations:

### fal.ai Generation

```json
{
  "method": "POST",
  "url": "https://fal.run/fal-ai/kling-video/v2.5/standard/text-to-video",
  "headers": {
    "Authorization": "Key {{ $credentials.falApiKey }}",
    "Content-Type": "application/json"
  },
  "body": {
    "prompt": "{{ $json.prompt }}",
    "duration": "{{ $json.duration }}",
    "aspect_ratio": "{{ $json.aspect_ratio }}"
  }
}
```

### With Reference Images

```json
{
  "method": "POST",
  "url": "https://fal.run/fal-ai/kling-video/v2.5/standard/image-to-video",
  "body": {
    "prompt": "{{ $json.prompt }}",
    "image_url": "{{ $json.reference_image_url }}",
    "duration": "{{ $json.duration }}"
  }
}
```

## Integration with Python Backend

The n8n workflow can call the Python backend via webhooks:

```python
# examples/n8n_webhook_handler.py
from fastapi import FastAPI, BackgroundTasks
from src.workflow import VideoProducer

app = FastAPI()
producer = VideoProducer()

@app.post("/webhook/generate")
async def generate_video(request: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        producer.generate_scene,
        **request
    )
    return {"status": "queued"}
```

## Tips

1. **Use Wait Nodes** - Video generation takes 30s-5min. Use wait nodes between steps.

2. **Error Handling** - Add error branches to handle API failures gracefully.

3. **Rate Limiting** - Add delays between API calls to respect rate limits.

4. **Parallel Processing** - Use split nodes to process multiple scenes in parallel.

5. **Callbacks** - Configure webhook callbacks for long-running generations.
