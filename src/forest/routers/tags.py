from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from ..models import Tag, TagCreate
from ..db import TagRepository


router = APIRouter(prefix="/api/tags", tags=["tags"])


_tag_repo: Optional[TagRepository] = None


def get_tag_repo() -> TagRepository:
    if _tag_repo is None:
        raise RuntimeError("Tag repository not initialized")
    return _tag_repo


def set_tag_repo(repo: TagRepository):
    global _tag_repo
    _tag_repo = repo


@router.post("", response_model=Tag)
async def create_tag(
    data: TagCreate,
    repo: TagRepository = Depends(get_tag_repo)
):
    """Create a new tag."""
    existing = await repo.get(data.name)
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")
    
    return await repo.create(data)


@router.get("", response_model=list[Tag])
async def list_tags(repo: TagRepository = Depends(get_tag_repo)):
    """List all tags."""
    return await repo.list_all()


@router.delete("/{tag_name}")
async def delete_tag(
    tag_name: str,
    repo: TagRepository = Depends(get_tag_repo)
):
    """Delete a tag."""
    if not await repo.delete(tag_name):
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"status": "deleted"}
