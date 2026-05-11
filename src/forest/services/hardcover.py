"""
Hardcover GraphQL API service for searching and fetching book metadata.
"""

import uuid
from datetime import datetime
from typing import Optional

import httpx

from ..models import Book, HardcoverSearchResult
from .settings_service import load_settings

HARDCOVER_API_URL = "https://api.hardcover.app/v1/graphql"


class HardcoverError(Exception):
    """Error fetching from Hardcover API"""

    pass


def get_api_key() -> Optional[str]:
    """Get the Hardcover API key from settings, properly formatted."""
    key = load_settings().hardcover_api_key
    if not key:
        return None
    # Ensure Bearer prefix is present
    if not key.startswith("Bearer "):
        key = f"Bearer {key}"
    return key


def is_configured() -> bool:
    """Check if Hardcover API key is configured."""
    key = get_api_key()
    return key is not None and len(key) > 0


async def search_books(query: str, limit: int = 10) -> list[HardcoverSearchResult]:
    """
    Search Hardcover for books by title/author.

    Args:
        query: Search query (title, author, or both)
        limit: Maximum results to return

    Returns:
        List of search results
    """
    api_key = get_api_key()
    if not api_key:
        raise HardcoverError("Hardcover API key not configured")

    graphql_query = """
    query SearchBooks($query: String!, $limit: Int!) {
        search(
            query: $query
            query_type: "books"
            per_page: $limit
            page: 1
        ) {
            results
        }
    }
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                HARDCOVER_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "authorization": api_key,
                },
                json={
                    "query": graphql_query,
                    "variables": {"query": query, "limit": limit},
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            raise HardcoverError(f"Failed to search Hardcover: {e}")

    # Check for GraphQL errors
    if "errors" in data:
        raise HardcoverError(f"Hardcover API error: {data['errors']}")

    results = []
    hits = data.get("data", {}).get("search", {}).get("results", {}).get("hits", [])

    for hit in hits:
        doc = hit.get("document", {})

        # Extract cover URL from image object
        cover_url = None
        if doc.get("image") and doc["image"].get("url"):
            cover_url = doc["image"]["url"]

        results.append(
            HardcoverSearchResult(
                id=str(doc.get("id", "")),
                title=doc.get("title", "Unknown Title"),
                authors=doc.get("author_names", []),
                description=doc.get("description"),
                pages=doc.get("pages"),
                release_year=doc.get("release_year"),
                cover_url=cover_url,
                slug=doc.get("slug"),
                isbns=doc.get("isbns", []),
                genres=doc.get("genres", []),
            )
        )

    return results


def create_book_from_hardcover(search_result: HardcoverSearchResult) -> Book:
    """
    Create a Book object from a Hardcover search result.

    Args:
        search_result: HardcoverSearchResult from search

    Returns:
        Book object ready to save
    """
    # Extract ISBNs
    isbn_13 = None
    isbn_10 = None
    for isbn in search_result.isbns:
        if len(isbn) == 13 and not isbn_13:
            isbn_13 = isbn
        elif len(isbn) == 10 and not isbn_10:
            isbn_10 = isbn

    return Book(
        id=str(uuid.uuid4()),
        hardcover_id=search_result.id,
        open_library_key=None,
        title=search_result.title,
        authors=search_result.authors if search_result.authors else ["Unknown Author"],
        description=search_result.description,
        cover_url=search_result.cover_url,
        page_count=search_result.pages,
        first_publish_year=search_result.release_year,
        isbn_13=isbn_13,
        isbn_10=isbn_10,
        subjects=search_result.genres,
        added_at=datetime.utcnow(),
    )
