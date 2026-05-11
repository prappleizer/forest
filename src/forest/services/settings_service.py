"""
Settings service for managing user preferences like rating categories.
"""

import json
from pathlib import Path
from typing import Optional

from ..config import settings
from ..models import RatingCategory, UserSettings


def _get_settings_path() -> Path:
    return settings.data_dir / "settings.json"


def load_settings() -> UserSettings:
    """Load user settings from disk."""
    path = _get_settings_path()

    if not path.exists():
        return UserSettings()

    try:
        data = json.loads(path.read_text())
        return UserSettings(**data)
    except Exception:
        return UserSettings()


def save_settings(user_settings: UserSettings) -> None:
    """Save user settings to disk."""
    path = _get_settings_path()
    path.write_text(json.dumps(user_settings.model_dump(), indent=2))


def get_rating_categories() -> list[RatingCategory]:
    """Get the list of enabled rating categories."""
    user_settings = load_settings()
    return [cat for cat in user_settings.rating_categories if cat.enabled]


def set_rating_categories(categories: list[str]) -> None:
    """Set the rating categories (by name)."""
    user_settings = load_settings()
    user_settings.rating_categories = [
        RatingCategory(name=name, enabled=True) for name in categories
    ]
    save_settings(user_settings)


def add_rating_category(name: str) -> None:
    """Add a new rating category."""
    user_settings = load_settings()

    # Check if already exists
    for cat in user_settings.rating_categories:
        if cat.name.lower() == name.lower():
            cat.enabled = True
            save_settings(user_settings)
            return

    user_settings.rating_categories.append(RatingCategory(name=name, enabled=True))
    save_settings(user_settings)


def remove_rating_category(name: str) -> None:
    """Remove a rating category."""
    user_settings = load_settings()
    user_settings.rating_categories = [
        cat
        for cat in user_settings.rating_categories
        if cat.name.lower() != name.lower()
    ]
    save_settings(user_settings)


def is_onboarding_complete() -> bool:
    """Check if onboarding has been completed."""
    return load_settings().onboarding_complete


def complete_onboarding() -> None:
    """Mark onboarding as complete."""
    user_settings = load_settings()
    user_settings.onboarding_complete = True
    save_settings(user_settings)


def get_hardcover_api_key() -> Optional[str]:
    """Get the Hardcover API key."""
    return load_settings().hardcover_api_key


def set_hardcover_api_key(api_key: Optional[str]) -> None:
    """Set the Hardcover API key."""
    user_settings = load_settings()
    user_settings.hardcover_api_key = api_key.strip() if api_key else None
    save_settings(user_settings)


def get_reading_goals() -> dict[str, dict]:
    """Get all reading goals."""
    return load_settings().reading_goals


def get_reading_goal(year: int) -> Optional[dict]:
    """Get reading goal for a specific year."""
    goals = load_settings().reading_goals
    return goals.get(str(year))


def set_reading_goal(year: int, goal_type: str, target: int) -> None:
    """Set a reading goal for a year."""
    user_settings = load_settings()
    user_settings.reading_goals[str(year)] = {
        "type": goal_type,  # "books" or "pages"
        "target": target,
    }
    save_settings(user_settings)


def delete_reading_goal(year: int) -> None:
    """Delete a reading goal for a year."""
    user_settings = load_settings()
    if str(year) in user_settings.reading_goals:
        del user_settings.reading_goals[str(year)]
        save_settings(user_settings)
