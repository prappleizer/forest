import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Optional

from ..models import Book, BookCreate, BookUpdate, SearchQuery, SearchResult, OpenLibrarySearchResult, HardcoverSearchResult
from ..services import (
    search_books_openlibrary, fetch_book_details, download_cover, OpenLibraryError,
    search_books_hardcover, create_book_from_hardcover, hardcover_is_configured, HardcoverError
)
from ..db import BookRepository
from ..config import settings


router = APIRouter(prefix="/api/books", tags=["books"])


# Dependency injection - will be set by main.py
_book_repo: Optional[BookRepository] = None


def get_book_repo() -> BookRepository:
    if _book_repo is None:
        raise RuntimeError("Book repository not initialized")
    return _book_repo


def set_book_repo(repo: BookRepository):
    global _book_repo
    _book_repo = repo


# === Search Endpoints ===

@router.get("/search-hardcover", response_model=list[HardcoverSearchResult])
async def search_hardcover(q: str, limit: int = 10):
    """Search Hardcover for books (requires API key in settings)."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query required")
    
    if not hardcover_is_configured():
        raise HTTPException(status_code=400, detail="Hardcover API key not configured")
    
    try:
        results = await search_books_hardcover(q, limit=limit)
        return results
    except HardcoverError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-openlibrary", response_model=list[OpenLibrarySearchResult])
async def search_openlibrary(q: str, limit: int = 20):
    """Search Open Library for books."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query required")
    
    try:
        results = await search_books_openlibrary(q, limit=limit)
        return results
    except OpenLibraryError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-status")
async def search_status():
    """Get search configuration status."""
    return {
        "hardcover_configured": hardcover_is_configured(),
        "openlibrary_available": True,  # Always available
    }


# === Add Book Endpoint ===

@router.post("", response_model=Book)
async def add_book(
    data: BookCreate,
    repo: BookRepository = Depends(get_book_repo)
):
    """Add a book to the library from Hardcover, Open Library, or manual entry."""
    
    # Check for duplicates based on source
    if data.hardcover_id:
        existing = await repo.get_by_hardcover_id(data.hardcover_id)
        if existing:
            raise HTTPException(status_code=409, detail="Book already in library")
    
    if data.open_library_key:
        existing = await repo.get_by_open_library_key(data.open_library_key)
        if existing:
            raise HTTPException(status_code=409, detail="Book already in library")
    
    # Build book based on source
    if data.source == "hardcover" and data.hardcover_id:
        # Create book from Hardcover data passed from frontend
        book = Book(
            id=str(uuid.uuid4()),
            hardcover_id=data.hardcover_id,
            open_library_key=None,
            title=data.title or "Unknown Title",
            authors=data.authors or ["Unknown Author"],
            description=data.description,
            cover_url=data.cover_url,
            page_count=data.number_of_pages,
            first_publish_year=data.first_publish_year,
            isbn_13=next((i for i in (data.isbn or []) if len(i) == 13), None),
            isbn_10=next((i for i in (data.isbn or []) if len(i) == 10), None),
            subjects=data.subject or [],
            added_at=datetime.utcnow(),
        )
        
    elif data.source == "openlibrary" and data.open_library_key:
        # Fetch from Open Library with search data
        search_data = {
            "title": data.title,
            "authors": data.authors,
            "first_publish_year": data.first_publish_year,
            "cover_i": data.cover_i,
            "number_of_pages": data.number_of_pages,
            "isbn": data.isbn or [],
            "subject": data.subject or [],
        }
        
        try:
            book = await fetch_book_details(data.open_library_key, search_data=search_data)
        except OpenLibraryError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    elif data.source == "manual":
        # Manual entry - create directly from provided data
        if not data.title:
            raise HTTPException(status_code=400, detail="Title is required for manual entry")
        
        book = Book(
            id=str(uuid.uuid4()),
            hardcover_id=None,
            open_library_key=None,
            title=data.title,
            authors=data.authors or ["Unknown Author"],
            description=data.description,
            cover_url=data.cover_url,
            page_count=data.number_of_pages,
            first_publish_year=data.first_publish_year,
            isbn_13=next((i for i in (data.isbn or []) if len(i) == 13), None),
            isbn_10=next((i for i in (data.isbn or []) if len(i) == 10), None),
            subjects=data.subject or [],
            added_at=datetime.utcnow(),
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid source or missing required fields")
    
    # Download cover image if available
    if book.cover_url:
        filename = f"{book.id}.jpg"
        if await download_cover(book.cover_url, filename):
            book.cover_image = filename
    
    return await repo.create(book)


# === List and Search ===

@router.get("", response_model=list[Book])
async def list_books(
    limit: int = 50,
    offset: int = 0,
    repo: BookRepository = Depends(get_book_repo)
):
    """List all books in the library."""
    return await repo.list_all(limit=limit, offset=offset)


@router.get("/search", response_model=SearchResult)
async def search_books_in_library(
    q: Optional[str] = None,
    tags: Optional[str] = None,
    shelves: Optional[str] = None,
    letter_grade: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    repo: BookRepository = Depends(get_book_repo)
):
    """Search books with filters."""
    from ..models import LetterGrade
    
    query = SearchQuery(
        q=q,
        tags=tags.split(",") if tags else None,
        shelves=shelves.split(",") if shelves else None,
        letter_grade=LetterGrade(letter_grade) if letter_grade else None,
        limit=limit,
        offset=offset
    )
    return await repo.search(query)


@router.get("/by-grade/{grade}", response_model=list[Book])
async def get_books_by_grade(
    grade: str,
    repo: BookRepository = Depends(get_book_repo)
):
    """Get all books with a specific letter grade."""
    return await repo.get_by_letter_grade(grade)


@router.get("/tier-list")
async def get_tier_list(repo: BookRepository = Depends(get_book_repo)):
    """Get all books organized by tier/letter grade."""
    grades = ["S", "A", "B", "C", "D", "E", "F", "DNF"]
    result = {}
    
    for grade in grades:
        books = await repo.get_by_letter_grade(grade)
        result[grade] = books
    
    return result


# === Single Book Operations ===

@router.get("/{book_id}", response_model=Book)
async def get_book(
    book_id: str,
    repo: BookRepository = Depends(get_book_repo)
):
    """Get a specific book by ID."""
    book = await repo.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.patch("/{book_id}", response_model=Book)
async def update_book(
    book_id: str,
    data: BookUpdate,
    repo: BookRepository = Depends(get_book_repo)
):
    """Update book metadata."""
    book = await repo.update(book_id, data)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    repo: BookRepository = Depends(get_book_repo)
):
    """Remove a book from the library."""
    book = await repo.get(book_id)
    if book and book.cover_image:
        cover_path = settings.covers_dir / book.cover_image
        if cover_path.exists():
            cover_path.unlink()
    
    if not await repo.delete(book_id):
        raise HTTPException(status_code=404, detail="Book not found")
    
    return {"status": "deleted"}


# === Cover Image Operations ===

@router.post("/{book_id}/cover", response_model=Book)
async def upload_cover(
    book_id: str,
    file: UploadFile = File(...),
    repo: BookRepository = Depends(get_book_repo)
):
    """Upload a custom cover image for a book."""
    book = await repo.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Generate filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{book_id}_{uuid.uuid4().hex[:8]}.{ext}"
    
    # Delete old cover if exists
    if book.cover_image:
        old_path = settings.covers_dir / book.cover_image
        if old_path.exists():
            old_path.unlink()
    
    # Save new cover
    file_path = settings.covers_dir / filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    return await repo.set_cover(book_id, filename)


@router.delete("/{book_id}/cover", response_model=Book)
async def delete_cover(
    book_id: str,
    repo: BookRepository = Depends(get_book_repo)
):
    """Remove a book's cover image."""
    book = await repo.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.cover_image:
        cover_path = settings.covers_dir / book.cover_image
        if cover_path.exists():
            cover_path.unlink()
    
    return await repo.set_cover(book_id, None)
