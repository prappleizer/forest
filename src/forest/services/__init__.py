from .hardcover import HardcoverError, create_book_from_hardcover
from .hardcover import is_configured as hardcover_is_configured
from .hardcover import search_books as search_books_hardcover
from .openlibrary import (
    OpenLibraryError,
    download_cover,
    fetch_book_details,
    get_cover_url,
)
from .openlibrary import search_books as search_books_openlibrary
from .settings_service import (
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
    save_settings,
    set_hardcover_api_key,
    set_rating_categories,
    set_reading_goal,
)

__all__ = [
    "search_books_openlibrary",
    "fetch_book_details",
    "get_cover_url",
    "download_cover",
    "OpenLibraryError",
    "search_books_hardcover",
    "create_book_from_hardcover",
    "hardcover_is_configured",
    "HardcoverError",
    "load_settings",
    "save_settings",
    "get_rating_categories",
    "set_rating_categories",
    "add_rating_category",
    "remove_rating_category",
    "is_onboarding_complete",
    "complete_onboarding",
    "get_hardcover_api_key",
    "set_hardcover_api_key",
    "get_reading_goals",
    "get_reading_goal",
    "set_reading_goal",
    "delete_reading_goal",
]
