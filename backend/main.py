"""
AgriMind AI – FastAPI Application
Serves the REST API and the static frontend from a single container.
"""

from __future__ import annotations
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

from .rag import rag_engine
from .chat import chat
from .weather import get_weather, get_weather_by_coords


# ── Startup / shutdown ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading AgriMind RAG engine…")
    await rag_engine.load()
    logger.info("RAG engine ready.")
    yield
    logger.info("AgriMind AI shutting down.")


# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgriMind AI",
    description="AI-powered agricultural advisor with weather analysis and RAG",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ───────────────────────────────────────────────

class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    weather_context: Optional[str] = ""


class ChatResponse(BaseModel):
    reply: str


class WeatherRequest(BaseModel):
    location: str


class WeatherCoordsRequest(BaseModel):
    latitude: float
    longitude: float


# ── API Routes ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "rag_documents": len(rag_engine.documents),
        "rag_loaded": rag_engine._loaded,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages list is empty")

    try:
        reply = await chat(
            messages=[m.model_dump() for m in req.messages],
            weather_context=req.weather_context or "",
        )
        return ChatResponse(reply=reply)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        # Log full exception and forward the message to the client for debugging
        logger.exception("Chat error: %s", exc)
        # If this is an unexpected error, include its message in the response
        detail = str(exc) or "AI service error. Please try again."
        raise HTTPException(status_code=502, detail=detail)


@app.post("/api/weather")
async def weather_endpoint(req: WeatherRequest):
    if not req.location.strip():
        raise HTTPException(status_code=400, detail="location is required")
    try:
        data = await get_weather(req.location.strip())
        return data
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Weather error: %s", exc)
        raise HTTPException(status_code=502, detail="Weather service error.")


@app.post("/api/weather/by-coords")
async def weather_by_coords_endpoint(req: WeatherCoordsRequest):
    """Fetch weather by geographic coordinates (for auto-location detection)."""
    if req.latitude < -90 or req.latitude > 90:
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if req.longitude < -180 or req.longitude > 180:
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
    try:
        data = await get_weather_by_coords(req.latitude, req.longitude)
        return data
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Weather error: %s", exc)
        raise HTTPException(status_code=502, detail="Weather service error.")


# ── Serve static frontend ───────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    # Serve static assets (css, js) from /static
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Fall-through: serve index.html for any unknown path (SPA routing)."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    logger.warning("Frontend directory not found at %s", FRONTEND_DIR)