from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from ..models import Shelf, ShelfCreate, ShelfUpdate
from ..db import ShelfRepository, BookRepository


router = APIRouter(prefix="/api/shelves", tags=["shelves"])


_shelf_repo: Optional[ShelfRepository] = None
_book_repo: Optional[BookRepository] = None


def get_shelf_repo() -> ShelfRepository:
    if _shelf_repo is None:
        raise RuntimeError("Shelf repository not initialized")
    return _shelf_repo


def set_repos(shelf_repo: ShelfRepository, book_repo: BookRepository):
    global _shelf_repo, _book_repo
    _shelf_repo = shelf_repo
    _book_repo = book_repo


@router.post("", response_model=Shelf)
async def create_shelf(
    data: ShelfCreate,
    repo: ShelfRepository = Depends(get_shelf_repo)
):
    """Create a new shelf."""
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=409, detail="Shelf already exists")
    
    return await repo.create(data)


@router.get("", response_model=list[Shelf])
async def list_shelves(repo: ShelfRepository = Depends(get_shelf_repo)):
    """List all shelves."""
    return await repo.list_all()


@router.get("/{shelf_id}", response_model=Shelf)
async def get_shelf(
    shelf_id: str,
    repo: ShelfRepository = Depends(get_shelf_repo)
):
    """Get a specific shelf."""
    shelf = await repo.get(shelf_id)
    if not shelf:
        raise HTTPException(status_code=404, detail="Shelf not found")
    return shelf


@router.patch("/{shelf_id}", response_model=Shelf)
async def update_shelf(
    shelf_id: str,
    data: ShelfUpdate,
    repo: ShelfRepository = Depends(get_shelf_repo)
):
    """Update a shelf."""
    shelf = await repo.update(shelf_id, data)
    if not shelf:
        raise HTTPException(status_code=404, detail="Shelf not found")
    return shelf


@router.delete("/{shelf_id}")
async def delete_shelf(
    shelf_id: str,
    repo: ShelfRepository = Depends(get_shelf_repo)
):
    """Delete a shelf."""
    if not await repo.delete(shelf_id):
        raise HTTPException(status_code=404, detail="Shelf not found")
    return {"status": "deleted"}
