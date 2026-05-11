from abc import ABC, abstractmethod
from typing import Optional

from ..models import (
    Book, BookUpdate,
    Shelf, ShelfCreate, ShelfUpdate,
    Tag, TagCreate,
    SearchQuery, SearchResult
)


class BookRepository(ABC):
    """Abstract interface for book storage"""
    
    @abstractmethod
    async def create(self, book: Book) -> Book:
        pass
    
    @abstractmethod
    async def get(self, book_id: str) -> Optional[Book]:
        pass
    
    @abstractmethod
    async def get_by_open_library_key(self, key: str) -> Optional[Book]:
        pass
    
    @abstractmethod
    async def get_by_hardcover_id(self, hardcover_id: str) -> Optional[Book]:
        pass
    
    @abstractmethod
    async def update(self, book_id: str, data: BookUpdate) -> Optional[Book]:
        pass
    
    @abstractmethod
    async def delete(self, book_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Book]:
        pass
    
    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResult:
        pass
    
    @abstractmethod
    async def exists(self, open_library_key: str) -> bool:
        pass
    
    @abstractmethod
    async def set_cover(self, book_id: str, filename: Optional[str]) -> Optional[Book]:
        pass
    
    @abstractmethod
    async def get_by_letter_grade(self, grade: str) -> list[Book]:
        pass


class ShelfRepository(ABC):
    """Abstract interface for shelf storage"""
    
    @abstractmethod
    async def create(self, shelf: ShelfCreate) -> Shelf:
        pass
    
    @abstractmethod
    async def get(self, shelf_id: str) -> Optional[Shelf]:
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Shelf]:
        pass
    
    @abstractmethod
    async def update(self, shelf_id: str, data: ShelfUpdate) -> Optional[Shelf]:
        pass
    
    @abstractmethod
    async def delete(self, shelf_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_all(self) -> list[Shelf]:
        pass


class TagRepository(ABC):
    """Abstract interface for tag storage"""
    
    @abstractmethod
    async def create(self, tag: TagCreate) -> Tag:
        pass
    
    @abstractmethod
    async def get(self, name: str) -> Optional[Tag]:
        pass
    
    @abstractmethod
    async def delete(self, name: str) -> bool:
        pass
    
    @abstractmethod
    async def list_all(self) -> list[Tag]:
        pass
