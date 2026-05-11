from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LetterGrade(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    DNF = "DNF"
    UNSET = ""


# === Book Models ===


class BookBase(BaseModel):
    """Core book data - can come from Hardcover, Open Library, or manual entry"""

    # Source identifiers (at least one should be set, or manual=True)
    open_library_key: Optional[str] = None  # e.g., "/works/OL45883W"
    hardcover_id: Optional[str] = None  # e.g., "1906054"

    title: str
    authors: list[str]
    description: Optional[str] = None
    cover_url: Optional[str] = None  # URL to cover image
    cover_image: Optional[str] = None  # Local filename if downloaded
    page_count: Optional[int] = None
    first_publish_year: Optional[int] = None
    isbn_13: Optional[str] = None
    isbn_10: Optional[str] = None
    subjects: list[str] = Field(default_factory=list)


class BookCreate(BaseModel):
    """Request to add a book - from Hardcover, Open Library, or manual entry"""

    # Source - one of these should be set (or none for manual)
    source: str = "manual"  # "hardcover", "openlibrary", or "manual"

    # Hardcover fields
    hardcover_id: Optional[str] = None

    # Open Library fields
    open_library_key: Optional[str] = None
    cover_i: Optional[int] = None  # Open Library cover ID

    # Common fields (from search results or manual entry)
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    description: Optional[str] = None
    first_publish_year: Optional[int] = None
    number_of_pages: Optional[int] = None
    isbn: Optional[list[str]] = None
    subject: Optional[list[str]] = None
    cover_url: Optional[str] = None  # Direct cover URL (Hardcover or manual)


class BookUpdate(BaseModel):
    """User-editable book metadata"""

    shelves: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    starred: Optional[bool] = None

    # Reading progress
    current_page: Optional[int] = None
    started_date: Optional[date] = None
    finished_date: Optional[date] = None

    # Ratings
    rating_overall: Optional[float] = None  # 0-5, 0.1 increments
    ratings_custom: Optional[dict[str, float]] = None  # category -> rating
    letter_grade: Optional[LetterGrade] = None

    # Review/notes
    review: Optional[str] = None


class Book(BookBase):
    """Full book model with user data"""

    id: str  # UUID
    shelves: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    starred: bool = False
    added_at: datetime = Field(default_factory=datetime.utcnow)

    # Reading progress
    current_page: Optional[int] = None
    started_date: Optional[date] = None
    finished_date: Optional[date] = None

    # Ratings
    rating_overall: Optional[float] = None
    ratings_custom: dict[str, float] = Field(default_factory=dict)
    letter_grade: LetterGrade = LetterGrade.UNSET

    # Review
    review: Optional[str] = None

    class Config:
        from_attributes = True


# === Shelf Models ===


class ShelfBase(BaseModel):
    name: str
    description: Optional[str] = None


class ShelfCreate(ShelfBase):
    pass


class ShelfUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Shelf(ShelfBase):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    book_count: int = 0

    class Config:
        from_attributes = True


# === Tag Models ===


class TagBase(BaseModel):
    name: str
    color: Optional[str] = None


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    book_count: int = 0

    class Config:
        from_attributes = True


# === Search Models ===


class SearchQuery(BaseModel):
    q: Optional[str] = None
    tags: Optional[list[str]] = None
    shelves: Optional[list[str]] = None
    letter_grade: Optional[LetterGrade] = None
    limit: int = 50
    offset: int = 0


class SearchResult(BaseModel):
    books: list[Book]
    total: int


# === Open Library Search Result ===


class OpenLibrarySearchResult(BaseModel):
    """A book result from Open Library search"""

    key: str  # e.g., "/works/OL45883W"
    title: str
    authors: list[str] = Field(default_factory=list)
    first_publish_year: Optional[int] = None
    cover_i: Optional[int] = None  # Cover ID for building URL
    isbn: list[str] = Field(default_factory=list)
    number_of_pages: Optional[int] = None
    subject: list[str] = Field(default_factory=list)


# === Settings Models ===


class RatingCategory(BaseModel):
    name: str
    enabled: bool = True


class UserSettings(BaseModel):
    rating_categories: list[RatingCategory] = Field(
        default_factory=lambda: [
            RatingCategory(name="Writing"),
            RatingCategory(name="Characters"),
            RatingCategory(name="Plot"),
            RatingCategory(name="World Building"),
            RatingCategory(name="Enjoyment"),
        ]
    )
    onboarding_complete: bool = False
    hardcover_api_key: Optional[str] = None
    reading_goals: dict[str, dict] = Field(
        default_factory=dict
    )  # {"2025": {"type": "books", "target": 50}}


# === Hardcover Search Result ===


class HardcoverSearchResult(BaseModel):
    """A book result from Hardcover search"""

    id: str  # Hardcover book ID
    title: str
    authors: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    pages: Optional[int] = None
    release_year: Optional[int] = None
    cover_url: Optional[str] = None
    slug: Optional[str] = None
    isbns: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
