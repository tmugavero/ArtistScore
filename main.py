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
        .container { max-width: 720px; padding: 48px 32px; }
        h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 8px; color: #fff; }
        h1 span { background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .tagline { font-size: 1.1rem; color: #888; margin-bottom: 40px; }
        .card { background: #151515; border: 1px solid #252525; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
        .card h3 { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #6366f1; margin-bottom: 12px; }
        .endpoint { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85rem; }
        .method { background: #1a3a2a; color: #4ade80; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; }
        .method.post { background: #2a2a1a; color: #facc15; }
        .path { color: #ccc; }
        .desc { color: #666; font-size: 0.8rem; margin-left: 60px; margin-bottom: 16px; }
        .sources { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; }
        .source { background: #1a1a1a; border: 1px solid #252525; border-radius: 8px; padding: 12px; text-align: center; font-size: 0.8rem; }
        .source .pct { font-size: 1.2rem; font-weight: 700; color: #a855f7; }
        .links { display: flex; gap: 12px; margin-top: 32px; }
        .links a { display: inline-block; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.9rem; }
        .links a.primary { background: #6366f1; color: #fff; }
        .links a.secondary { background: #1a1a1a; border: 1px solid #333; color: #ccc; }
        .links a:hover { opacity: 0.85; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Artist<span>Score</span></h1>
        <p class="tagline">FICO-like scoring for music artists. Built for brands.</p>

        <div class="card">
            <h3>API Endpoints</h3>
            <div class="endpoint"><span class="method">GET</span> <span class="path">/api/v1/score/{artist_name}</span></div>
            <p class="desc">Full score with breakdown, sentiment, and AI summary</p>
            <div class="endpoint"><span class="method post">POST</span> <span class="path">/api/v1/score</span></div>
            <p class="desc">Score via JSON body: {"artist_name": "..."}</p>
            <div class="endpoint"><span class="method">GET</span> <span class="path">/api/v1/score/{artist_name}/quick</span></div>
            <p class="desc">Quick score and grade only</p>
            <div class="endpoint"><span class="method">GET</span> <span class="path">/api/v1/health</span></div>
            <p class="desc">Health check (no auth required)</p>
        </div>

        <div class="card">
            <h3>Data Sources &amp; Weights</h3>
            <div class="sources">
                <div class="source"><div class="pct">35%</div>Spotify</div>
                <div class="source"><div class="pct">30%</div>YouTube</div>
                <div class="source"><div class="pct">25%</div>Chartmetric</div>
            </div>
            <div class="sources" style="grid-template-columns: repeat(2, 1fr); margin-top: 8px;">
                <div class="source"><div class="pct">7%</div>Gemini AI Sentiment</div>
                <div class="source"><div class="pct">3%</div>Brave Web Presence</div>
            </div>
        </div>

        <div class="card">
            <h3>Authentication</h3>
            <p style="font-family: monospace; font-size: 0.85rem; color: #ccc;">X-API-Key: &lt;your-api-key&gt;</p>
            <p style="font-size: 0.8rem; color: #666; margin-top: 8px;">All scoring endpoints require an API key header.</p>
        </div>

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
