from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models import RatingCategory, UserSettings
from ..services import (
    add_rating_category,
    complete_onboarding,
    delete_reading_goal,
    get_hardcover_api_key,
    get_rating_categories,
    get_reading_goal,
    get_reading_goals,
    is_onboarding_complete,
    load_settings,
    remove_rating_category,
    set_hardcover_api_key,
    set_rating_categories,
    set_reading_goal,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class RatingCategoriesUpdate(BaseModel):
    categories: list[str]


class AddCategoryRequest(BaseModel):
    name: str


class ApiKeyUpdate(BaseModel):
    api_key: Optional[str] = None


@router.get("", response_model=UserSettings)
async def get_settings():
    """Get all user settings."""
    settings = load_settings()
    # Mask the API key for security
    if settings.hardcover_api_key:
        settings.hardcover_api_key = "***configured***"
    return settings


@router.get("/rating-categories", response_model=list[RatingCategory])
async def get_categories():
    """Get enabled rating categories."""
    return get_rating_categories()


@router.put("/rating-categories")
async def update_categories(data: RatingCategoriesUpdate):
    """Set all rating categories."""
    set_rating_categories(data.categories)
    return {"status": "success", "categories": data.categories}


@router.post("/rating-categories")
async def add_category(data: AddCategoryRequest):
    """Add a new rating category."""
    add_rating_category(data.name)
    return {"status": "success", "name": data.name}


@router.delete("/rating-categories/{name}")
async def delete_category(name: str):
    """Remove a rating category."""
    remove_rating_category(name)
    return {"status": "deleted"}


@router.get("/onboarding")
async def get_onboarding_status():
    """Check if onboarding is complete."""
    return {"complete": is_onboarding_complete()}


@router.post("/onboarding/complete")
async def mark_onboarding_complete():
    """Mark onboarding as complete."""
    complete_onboarding()
    return {"status": "success"}


@router.get("/hardcover-api-key")
async def get_api_key_status():
    """Check if Hardcover API key is configured."""
    key = get_hardcover_api_key()
    return {
        "configured": key is not None and len(key) > 0,
    }


@router.put("/hardcover-api-key")
async def update_api_key(data: ApiKeyUpdate):
    """Set the Hardcover API key."""
    set_hardcover_api_key(data.api_key)
    return {
        "status": "success",
        "configured": data.api_key is not None and len(data.api_key) > 0,
    }


@router.delete("/hardcover-api-key")
async def delete_api_key():
    """Remove the Hardcover API key."""
    set_hardcover_api_key(None)
    return {"status": "deleted"}


@router.post("/hardcover-api-key/test")
async def test_api_key():
    """Test if the Hardcover API key is working."""
    from ..services.hardcover import HardcoverError, is_configured
    from ..services.hardcover import search_books as hc_search

    if not is_configured():
        return {"success": False, "error": "API key not configured"}

    try:
        # Try a simple search
        results = await hc_search("Dune", limit=1)
        return {
            "success": True,
            "message": f"API key working! Found {len(results)} result(s)",
        }
    except HardcoverError as e:
        return {"success": False, "error": str(e)}


# === Reading Goals ===


class ReadingGoalUpdate(BaseModel):
    year: int
    goal_type: str  # "books" or "pages"
    target: int


@router.get("/reading-goals")
async def get_goals():
    """Get all reading goals."""
    return get_reading_goals()


@router.get("/reading-goals/{year}")
async def get_goal(year: int):
    """Get reading goal for a specific year."""
    goal = get_reading_goal(year)
    if not goal:
        return {"year": year, "goal": None}
    return {"year": year, "goal": goal}


@router.put("/reading-goals")
async def update_goal(data: ReadingGoalUpdate):
    """Set a reading goal."""
    if data.goal_type not in ("books", "pages"):
        raise HTTPException(
            status_code=400, detail="goal_type must be 'books' or 'pages'"
        )
    if data.target <= 0:
        raise HTTPException(status_code=400, detail="target must be positive")

    set_reading_goal(data.year, data.goal_type, data.target)
    return {
        "status": "success",
        "year": data.year,
        "goal": {"type": data.goal_type, "target": data.target},
    }


@router.delete("/reading-goals/{year}")
async def remove_goal(year: int):
    """Delete a reading goal."""
    delete_reading_goal(year)
    return {"status": "deleted", "year": year}
