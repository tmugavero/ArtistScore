from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routes import router
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting Artist Scoring API...")
    settings = get_settings()
    print(f"YouTube API: {'configured' if settings.YOUTUBE_API else 'missing'}")
    print(f"Spotify API: {'configured' if settings.SPOTIFY_API else 'missing'}")
    print(f"Chartmetric API: {'configured' if settings.CHARTMETRIC else 'missing'}")
    print(f"Brave API: {'configured' if settings.BRAVE_API else 'missing'}")
    print(f"Gemini API: {'configured' if settings.GEMINI_API else 'missing'}")
    yield
    # Shutdown
    print("Shutting down Artist Scoring API...")


app = FastAPI(
    title="Artist Scoring API",
    description="FICO-like scoring system for music artists. Combines data from Spotify, YouTube, Chartmetric, and web presence with AI-powered sentiment analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Artist Scoring API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "score_endpoint": "/api/v1/score/{artist_name}",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
