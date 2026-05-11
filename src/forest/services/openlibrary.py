"""
Open Library API service for searching and fetching book metadata.
"""

import httpx
from typing import Optional
from datetime import datetime
import uuid

from ..config import settings
from ..models import Book, OpenLibrarySearchResult


class OpenLibraryError(Exception):
    """Error fetching from Open Library API"""
    pass


async def search_books(query: str, limit: int = 20) -> list[OpenLibrarySearchResult]:
    """
    Search Open Library for books by title/author.
    
    Args:
        query: Search query (title, author, or both)
        limit: Maximum results to return
    
    Returns:
        List of search results
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                settings.open_library_search_url,
                params={
                    "q": query,
                    "limit": limit,
                    "fields": "key,title,author_name,first_publish_year,cover_i,isbn,number_of_pages_median,subject"
                }
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            raise OpenLibraryError(f"Failed to search Open Library: {e}")
    
    results = []
    for doc in data.get("docs", []):
        results.append(OpenLibrarySearchResult(
            key=doc.get("key", ""),
            title=doc.get("title", "Unknown Title"),
            authors=doc.get("author_name", []),
            first_publish_year=doc.get("first_publish_year"),
            cover_i=doc.get("cover_i"),
            isbn=doc.get("isbn", [])[:5],  # Limit ISBNs
            number_of_pages=doc.get("number_of_pages_median"),
            subject=doc.get("subject", [])[:10],  # Limit subjects
        ))
    
    return results


async def fetch_book_details(open_library_key: str, search_data: Optional[dict] = None) -> Book:
    """
    Fetch full book details from Open Library.
    
    Args:
        open_library_key: Open Library work key (e.g., "/works/OL45883W")
        search_data: Optional search result data to use (avoids extra API calls)
    
    Returns:
        Book object with metadata
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch work details for description
        description = None
        work_covers = []
        work_title = None
        
        try:
            work_url = f"https://openlibrary.org{open_library_key}.json"
            response = await client.get(work_url)
            response.raise_for_status()
            work_data = response.json()
            
            # Extract description
            if "description" in work_data:
                desc = work_data["description"]
                if isinstance(desc, dict):
                    description = desc.get("value", "")
                else:
                    description = str(desc)
            
            work_covers = work_data.get("covers", [])
            work_title = work_data.get("title")
            
            # If we don't have search_data, try to get authors from work
            if not search_data:
                authors = []
                for author_ref in work_data.get("authors", []):
                    author_key = author_ref.get("author", {}).get("key") if isinstance(author_ref, dict) else None
                    if author_key:
                        try:
                            author_response = await client.get(f"https://openlibrary.org{author_key}.json")
                            if author_response.status_code == 200:
                                author_data = author_response.json()
                                authors.append(author_data.get("name", "Unknown Author"))
                        except:
                            pass
                if not authors:
                    authors = ["Unknown Author"]
                search_data = {"authors": authors, "title": work_title}
                
        except httpx.HTTPError as e:
            raise OpenLibraryError(f"Failed to fetch book details: {e}")
    
    # Use search data for authors, title, etc. (more reliable)
    title = search_data.get("title") or work_title or "Unknown Title"
    authors = search_data.get("authors", []) or ["Unknown Author"]
    first_publish_year = search_data.get("first_publish_year")
    page_count = search_data.get("number_of_pages")
    subjects = search_data.get("subject", [])[:10] if search_data.get("subject") else []
    
    # Get cover URL - prefer search result cover_i, fall back to work covers
    cover_url = None
    cover_i = search_data.get("cover_i") if search_data else None
    if cover_i:
        cover_url = f"{settings.open_library_covers_url}/id/{cover_i}-L.jpg"
    elif work_covers:
        cover_url = f"{settings.open_library_covers_url}/id/{work_covers[0]}-L.jpg"
    
    # Get ISBNs
    isbns = search_data.get("isbn", []) if search_data else []
    isbn_13 = None
    isbn_10 = None
    for isbn in isbns:
        if len(isbn) == 13 and not isbn_13:
            isbn_13 = isbn
        elif len(isbn) == 10 and not isbn_10:
            isbn_10 = isbn
    
    # Create book object
    return Book(
        id=str(uuid.uuid4()),
        open_library_key=open_library_key,
        title=title,
        authors=authors if isinstance(authors, list) else [authors],
        description=description,
        cover_url=cover_url,
        page_count=page_count,
        first_publish_year=first_publish_year,
        isbn_13=isbn_13,
        isbn_10=isbn_10,
        subjects=subjects if isinstance(subjects, list) else [],
        added_at=datetime.utcnow(),
    )


def get_cover_url(cover_id: int, size: str = "M") -> str:
    """
    Build a cover image URL from a cover ID.
    
    Args:
        cover_id: Open Library cover ID
        size: S (small), M (medium), or L (large)
    
    Returns:
        URL to cover image
    """
    return f"{settings.open_library_covers_url}/id/{cover_id}-{size}.jpg"


async def download_cover(cover_url: str, filename: str) -> bool:
    """
    Download a cover image and save it locally.
    
    Args:
        cover_url: URL to the cover image
        filename: Local filename to save as
    
    Returns:
        True if successful, False otherwise
    """
    filepath = settings.covers_dir / filename
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(cover_url)
            response.raise_for_status()
            
            # Verify it's an image
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                return False
            
            filepath.write_bytes(response.content)
            return True
    except Exception as e:
        print(f"Failed to download cover: {e}")
        return False
