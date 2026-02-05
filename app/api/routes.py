from fastapi import APIRouter, HTTPException, Query, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app.services.artist_service import ArtistScoringService
from app.models.score import ArtistScoreResponse
from app.config import Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["scoring"])

# API key security
api_key_header = APIKeyHeader(name="X-API-Key")


async def verify_api_key(
    api_key: str = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify the API key from the X-API-Key header."""
    if api_key != settings.ARTIST_SCORE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# Request/Response models
class ScoreRequest(BaseModel):
    artist_name: str
    include_breakdown: bool = True


class QuickScoreResponse(BaseModel):
    artist_name: str
    score: float
    grade: str


class HealthResponse(BaseModel):
    status: str
    version: str


# Service instance cache
_service_instance = None


def get_scoring_service(settings: Settings = Depends(get_settings)) -> ArtistScoringService:
    """Get or create the scoring service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ArtistScoringService(settings)
    return _service_instance


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (no auth required)."""
    return HealthResponse(status="healthy", version="1.0.0")


@router.get("/score/{artist_name}", response_model=ArtistScoreResponse)
async def get_artist_score(
    artist_name: str,
    include_breakdown: bool = Query(True, description="Include detailed score breakdown"),
    _api_key: str = Depends(verify_api_key),
    service: ArtistScoringService = Depends(get_scoring_service),
):
    """
    Get artist score by name.

    Requires `X-API-Key` header.

    - **artist_name**: Name of the artist to score
    - **include_breakdown**: Whether to include detailed component scores

    Returns a 0-100 score with breakdown and AI-generated insights.
    """
    try:
        return await service.get_artist_score(
            artist_name=artist_name,
            include_details=include_breakdown,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Artist not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.post("/score", response_model=ArtistScoreResponse)
async def score_artist(
    request: ScoreRequest,
    _api_key: str = Depends(verify_api_key),
    service: ArtistScoringService = Depends(get_scoring_service),
):
    """
    Score an artist (POST version). Requires `X-API-Key` header.
    """
    try:
        return await service.get_artist_score(
            artist_name=request.artist_name,
            include_details=request.include_breakdown,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Artist not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.get("/score/{artist_name}/quick", response_model=QuickScoreResponse)
async def get_quick_score(
    artist_name: str,
    _api_key: str = Depends(verify_api_key),
    service: ArtistScoringService = Depends(get_scoring_service),
):
    """
    Get a quick score without full breakdown. Requires `X-API-Key` header.
    """
    try:
        result = await service.get_artist_score(
            artist_name=artist_name,
            include_details=False,
        )
        return QuickScoreResponse(
            artist_name=result.artist_name,
            score=result.final_score,
            grade=result.score_grade,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")
