from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArtistScore API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { max-width: 720px; padding: 48px 32px; text-align: center; }
        h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 24px; color: #fff; }
        h1 span { background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .links { display: flex; gap: 12px; justify-content: center; }
        .links a { display: inline-block; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.9rem; }
        .links a.primary { background: #6366f1; color: #fff; }
        .links a.secondary { background: #1a1a1a; border: 1px solid #333; color: #ccc; }
        .links a:hover { opacity: 0.85; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Artist<span>Score</span></h1>

        <div class="links">
            <a href="/docs" class="primary">Interactive Docs</a>
            <a href="/redoc" class="secondary">API Reference</a>
        </div>
    </div>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
