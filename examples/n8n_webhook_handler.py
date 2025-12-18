#!/usr/bin/env python3
"""
n8n Webhook Handler
===================

FastAPI server for handling n8n webhook requests.
Provides REST API endpoints for video generation.

Usage:
    uvicorn examples.n8n_webhook_handler:app --reload --port 8000
"""

import asyncio
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow import VideoProducer
from src.api.base import GenerationStatus

app = FastAPI(
    title="AI Video Series Producer API",
    description="REST API for generating AI video series with consistent characters",
    version="0.1.0",
)

# Global producer instance
producer: Optional[VideoProducer] = None

# Job tracking
jobs: Dict[str, Dict[str, Any]] = {}


class GenerationRequest(BaseModel):
    """Request model for video generation."""
    character_id: str
    action: str
    location_id: Optional[str] = None
    episode_id: Optional[str] = None
    scene_number: Optional[int] = None
    duration: int = 5
    provider: Optional[str] = None
    model: Optional[str] = None
    reference_images: Optional[List[str]] = None
    chain_from_previous: bool = True


class BatchRequest(BaseModel):
    """Request model for batch generation."""
    episode_id: str
    episode_number: int = 1
    title: str = ""
    scenes: List[Dict[str, Any]]


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: Optional[float] = None
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


@app.on_event("startup")
async def startup():
    """Initialize the producer on startup."""
    global producer

    project_root = Path(__file__).parent.parent
    producer = VideoProducer(
        config_path=project_root / "config" / "defaults.yaml",
        character_bible_path=project_root / "context" / "character_bible.yaml",
        output_path=project_root / "output",
        provider="fal",
    )

    print("Video Producer initialized")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    global producer
    if producer:
        await producer.close()


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AI Video Series Producer API",
        "version": "0.1.0",
        "endpoints": {
            "generate": "POST /generate",
            "batch": "POST /batch",
            "status": "GET /status/{job_id}",
            "characters": "GET /characters",
            "locations": "GET /locations",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "producer_ready": producer is not None,
        "api_configured": bool(os.getenv("FAL_API_KEY")),
    }


@app.get("/characters")
async def list_characters():
    """List available characters from the character bible."""
    if not producer:
        raise HTTPException(status_code=503, detail="Producer not initialized")

    return {
        "characters": [
            {
                "id": char_id,
                "name": char.name,
                "role": char.role,
            }
            for char_id, char in producer.character_bible.characters.items()
        ]
    }


@app.get("/locations")
async def list_locations():
    """List available locations from the character bible."""
    if not producer:
        raise HTTPException(status_code=503, detail="Producer not initialized")

    return {
        "locations": [
            {
                "id": loc_id,
                "name": loc.name,
            }
            for loc_id, loc in producer.character_bible.locations.items()
        ]
    }


@app.post("/generate")
async def generate_video(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate a video scene.

    The generation runs in the background. Use /status/{job_id} to check progress.
    """
    if not producer:
        raise HTTPException(status_code=503, detail="Producer not initialized")

    # Create job
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    jobs[job_id] = {
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "request": request.dict(),
    }

    # Add background task
    background_tasks.add_task(
        run_generation,
        job_id,
        request,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Generation started. Check /status/{job_id} for progress.",
    }


async def run_generation(job_id: str, request: GenerationRequest):
    """Background task for video generation."""
    jobs[job_id]["status"] = "processing"

    try:
        result = await producer.generate_scene(
            character_id=request.character_id,
            action=request.action,
            location_id=request.location_id,
            episode_id=request.episode_id,
            scene_number=request.scene_number,
            duration=request.duration,
            provider=request.provider,
            model=request.model,
            chain_from_previous=request.chain_from_previous,
        )

        jobs[job_id].update({
            "status": result.status.value,
            "video_url": result.video_url,
            "video_path": result.video_path,
            "seed": result.seed,
            "completed_at": datetime.now().isoformat(),
        })

        if result.error_message:
            jobs[job_id]["error"] = result.error_message

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        })


@app.post("/batch")
async def batch_generate(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate multiple scenes (an episode).

    All scenes are generated in sequence with frame chaining.
    """
    if not producer:
        raise HTTPException(status_code=503, detail="Producer not initialized")

    # Create batch job
    job_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    jobs[job_id] = {
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "total_scenes": len(request.scenes),
        "completed_scenes": 0,
        "scenes": [],
    }

    # Add background task
    background_tasks.add_task(
        run_batch_generation,
        job_id,
        request,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "total_scenes": len(request.scenes),
        "message": "Batch generation started. Check /status/{job_id} for progress.",
    }


async def run_batch_generation(job_id: str, request: BatchRequest):
    """Background task for batch generation."""
    jobs[job_id]["status"] = "processing"

    try:
        results = await producer.generate_episode(
            series_id="api_series",
            episode_number=request.episode_number,
            scenes=request.scenes,
            title=request.title,
        )

        scene_results = []
        for i, result in enumerate(results):
            scene_results.append({
                "scene_number": i + 1,
                "status": result.status.value,
                "video_url": result.video_url,
                "video_path": result.video_path,
            })
            jobs[job_id]["completed_scenes"] = i + 1

        completed_count = sum(1 for r in results if r.status == GenerationStatus.COMPLETED)

        jobs[job_id].update({
            "status": "completed" if completed_count == len(results) else "partial",
            "scenes": scene_results,
            "completed_at": datetime.now().isoformat(),
        })

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        })


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get the status of a generation job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]


@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from tracking (does not cancel running jobs)."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del jobs[job_id]
    return {"message": f"Job {job_id} deleted"}


# n8n specific endpoint format
@app.post("/webhook/video-series/generate")
async def n8n_generate(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
):
    """n8n webhook endpoint for video generation."""
    return await generate_video(request, background_tasks)


@app.post("/webhook/video-series/batch")
async def n8n_batch(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
):
    """n8n webhook endpoint for batch generation."""
    return await batch_generate(request, background_tasks)


@app.get("/webhook/video-series/status/{job_id}")
async def n8n_status(job_id: str):
    """n8n webhook endpoint for status check."""
    return await get_status(job_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
