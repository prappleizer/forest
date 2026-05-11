import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from ..models import (
    Book,
    BookUpdate,
    LetterGrade,
    SearchQuery,
    SearchResult,
    Shelf,
    ShelfCreate,
    ShelfUpdate,
    Tag,
    TagCreate,
)
from .base import BookRepository, ShelfRepository, TagRepository


class SQLiteDatabase:
    """SQLite database connection manager"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        await self._create_default_shelves()

    async def disconnect(self):
        if self._connection:
            await self._connection.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected")
        return self._connection

    async def _create_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                open_library_key TEXT,
                hardcover_id TEXT,
                title TEXT NOT NULL,
                authors TEXT NOT NULL,  -- JSON array
                description TEXT,
                cover_url TEXT,
                cover_image TEXT,
                page_count INTEGER,
                first_publish_year INTEGER,
                isbn_13 TEXT,
                isbn_10 TEXT,
                subjects TEXT DEFAULT '[]',  -- JSON array
                shelves TEXT DEFAULT '[]',  -- JSON array
                tags TEXT DEFAULT '[]',  -- JSON array
                starred INTEGER DEFAULT 0,
                added_at TEXT NOT NULL,
                current_page INTEGER,
                started_date TEXT,
                finished_date TEXT,
                rating_overall REAL,
                ratings_custom TEXT DEFAULT '{}',  -- JSON object
                letter_grade TEXT DEFAULT '',
                review TEXT
            );
            
            CREATE TABLE IF NOT EXISTS shelves (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS tags (
                name TEXT PRIMARY KEY,
                color TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_books_letter_grade ON books(letter_grade);
            CREATE INDEX IF NOT EXISTS idx_books_starred ON books(starred);
            CREATE INDEX IF NOT EXISTS idx_books_hardcover_id ON books(hardcover_id);
            CREATE INDEX IF NOT EXISTS idx_books_open_library_key ON books(open_library_key);
        """)
        await self.conn.commit()

        # Run migrations for existing databases
        await self._migrate_add_hardcover_id()

    async def _migrate_add_hardcover_id(self):
        """Add hardcover_id column to existing databases"""
        try:
            # Check if column exists
            cursor = await self.conn.execute("PRAGMA table_info(books)")
            columns = [row[1] for row in await cursor.fetchall()]

            if "hardcover_id" not in columns:
                await self.conn.execute(
                    "ALTER TABLE books ADD COLUMN hardcover_id TEXT"
                )
                await self.conn.commit()
        except Exception:
            pass  # Column might already exist or table doesn't exist yet

    async def _create_default_shelves(self):
        """Create default Owned and TBR shelves if they don't exist"""
        cursor = await self.conn.execute("SELECT COUNT(*) FROM shelves")
        row = await cursor.fetchone()

        if row[0] == 0:
            now = datetime.utcnow().isoformat()
            await self.conn.executemany(
                "INSERT OR IGNORE INTO shelves (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                [
                    (str(uuid.uuid4()), "Owned", "Books I own", now),
                    (str(uuid.uuid4()), "TBR", "To be read", now),
                ],
            )
            await self.conn.commit()


class SQLiteBookRepository(BookRepository):
    def __init__(self, db: SQLiteDatabase):
        self.db = db

    def _row_to_book(self, row: aiosqlite.Row) -> Book:
        return Book(
            id=row["id"],
            open_library_key=row["open_library_key"],
            hardcover_id=row["hardcover_id"] if "hardcover_id" in row.keys() else None,
            title=row["title"],
            authors=json.loads(row["authors"]),
            description=row["description"],
            cover_url=row["cover_url"],
            cover_image=row["cover_image"],
            page_count=row["page_count"],
            first_publish_year=row["first_publish_year"],
            isbn_13=row["isbn_13"],
            isbn_10=row["isbn_10"],
            subjects=json.loads(row["subjects"]) if row["subjects"] else [],
            shelves=json.loads(row["shelves"]) if row["shelves"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            starred=bool(row["starred"]),
            added_at=datetime.fromisoformat(row["added_at"]),
            current_page=row["current_page"],
            started_date=date.fromisoformat(row["started_date"])
            if row["started_date"]
            else None,
            finished_date=date.fromisoformat(row["finished_date"])
            if row["finished_date"]
            else None,
            rating_overall=row["rating_overall"],
            ratings_custom=json.loads(row["ratings_custom"])
            if row["ratings_custom"]
            else {},
            letter_grade=LetterGrade(row["letter_grade"])
            if row["letter_grade"]
            else LetterGrade.UNSET,
            review=row["review"],
        )

    async def create(self, book: Book) -> Book:
        await self.db.conn.execute(
            """INSERT INTO books (
                id, open_library_key, hardcover_id, title, authors, description, cover_url, cover_image,
                page_count, first_publish_year, isbn_13, isbn_10, subjects,
                shelves, tags, starred, added_at, current_page, started_date, finished_date,
                rating_overall, ratings_custom, letter_grade, review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                book.id,
                book.open_library_key,
                book.hardcover_id,
                book.title,
                json.dumps(book.authors),
                book.description,
                book.cover_url,
                book.cover_image,
                book.page_count,
                book.first_publish_year,
                book.isbn_13,
                book.isbn_10,
                json.dumps(book.subjects),
                json.dumps(book.shelves),
                json.dumps(book.tags),
                int(book.starred),
                book.added_at.isoformat(),
                book.current_page,
                book.started_date.isoformat() if book.started_date else None,
                book.finished_date.isoformat() if book.finished_date else None,
                book.rating_overall,
                json.dumps(book.ratings_custom),
                book.letter_grade.value,
                book.review,
            ),
        )
        await self.db.conn.commit()
        return book

    async def get(self, book_id: str) -> Optional[Book]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_book(row) if row else None

    async def get_by_open_library_key(self, key: str) -> Optional[Book]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM books WHERE open_library_key = ?", (key,)
        )
        row = await cursor.fetchone()
        return self._row_to_book(row) if row else None

    async def get_by_hardcover_id(self, hardcover_id: str) -> Optional[Book]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM books WHERE hardcover_id = ?", (hardcover_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_book(row) if row else None

    async def update(self, book_id: str, data: BookUpdate) -> Optional[Book]:
        book = await self.get(book_id)
        if not book:
            return None

        updates = []
        params = []

        if data.shelves is not None:
            updates.append("shelves = ?")
            params.append(json.dumps(data.shelves))

        if data.tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(data.tags))

        if data.starred is not None:
            updates.append("starred = ?")
            params.append(int(data.starred))

        if data.current_page is not None:
            updates.append("current_page = ?")
            params.append(data.current_page)

        if data.started_date is not None:
            updates.append("started_date = ?")
            params.append(data.started_date.isoformat())

        if data.finished_date is not None:
            updates.append("finished_date = ?")
            params.append(data.finished_date.isoformat())

        if data.rating_overall is not None:
            updates.append("rating_overall = ?")
            params.append(data.rating_overall)

        if data.ratings_custom is not None:
            # Merge with existing
            merged = {**book.ratings_custom, **data.ratings_custom}
            updates.append("ratings_custom = ?")
            params.append(json.dumps(merged))

        if data.letter_grade is not None:
            updates.append("letter_grade = ?")
            params.append(data.letter_grade.value)

        if data.review is not None:
            updates.append("review = ?")
            params.append(data.review)

        if updates:
            params.append(book_id)
            await self.db.conn.execute(
                f"UPDATE books SET {', '.join(updates)} WHERE id = ?", params
            )
            await self.db.conn.commit()

        return await self.get(book_id)

    async def delete(self, book_id: str) -> bool:
        cursor = await self.db.conn.execute(
            "DELETE FROM books WHERE id = ?", (book_id,)
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Book]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM books ORDER BY added_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._row_to_book(row) for row in rows]

    async def search(self, query: SearchQuery) -> SearchResult:
        conditions = ["1=1"]
        params = []

        if query.q:
            conditions.append("(title LIKE ? OR authors LIKE ? OR review LIKE ?)")
            search_term = f"%{query.q}%"
            params.extend([search_term, search_term, search_term])

        if query.shelves:
            shelf_conditions = []
            for shelf in query.shelves:
                shelf_conditions.append("shelves LIKE ?")
                params.append(f'%"{shelf}"%')
            conditions.append(f"({' OR '.join(shelf_conditions)})")

        if query.tags:
            tag_conditions = []
            for tag in query.tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            conditions.append(f"({' AND '.join(tag_conditions)})")

        if query.letter_grade:
            conditions.append("letter_grade = ?")
            params.append(query.letter_grade.value)

        where_clause = " AND ".join(conditions)

        # Get total count
        cursor = await self.db.conn.execute(
            f"SELECT COUNT(*) FROM books WHERE {where_clause}", params
        )
        total = (await cursor.fetchone())[0]

        # Get paginated results
        cursor = await self.db.conn.execute(
            f"SELECT * FROM books WHERE {where_clause} ORDER BY added_at DESC LIMIT ? OFFSET ?",
            params + [query.limit, query.offset],
        )
        rows = await cursor.fetchall()

        return SearchResult(books=[self._row_to_book(row) for row in rows], total=total)

    async def exists(self, open_library_key: str) -> bool:
        cursor = await self.db.conn.execute(
            "SELECT 1 FROM books WHERE open_library_key = ?", (open_library_key,)
        )
        return await cursor.fetchone() is not None

    async def set_cover(self, book_id: str, filename: Optional[str]) -> Optional[Book]:
        await self.db.conn.execute(
            "UPDATE books SET cover_image = ? WHERE id = ?", (filename, book_id)
        )
        await self.db.conn.commit()
        return await self.get(book_id)

    async def get_by_letter_grade(self, grade: str) -> list[Book]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM books WHERE letter_grade = ? ORDER BY title", (grade,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_book(row) for row in rows]


class SQLiteShelfRepository(ShelfRepository):
    def __init__(self, db: SQLiteDatabase):
        self.db = db

    async def _get_book_count(self, shelf_id: str) -> int:
        cursor = await self.db.conn.execute(
            "SELECT COUNT(*) FROM books WHERE shelves LIKE ?", (f'%"{shelf_id}"%',)
        )
        return (await cursor.fetchone())[0]

    async def create(self, shelf: ShelfCreate) -> Shelf:
        shelf_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        await self.db.conn.execute(
            "INSERT INTO shelves (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (shelf_id, shelf.name, shelf.description, now),
        )
        await self.db.conn.commit()

        return Shelf(
            id=shelf_id,
            name=shelf.name,
            description=shelf.description,
            created_at=datetime.fromisoformat(now),
            book_count=0,
        )

    async def get(self, shelf_id: str) -> Optional[Shelf]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM shelves WHERE id = ?", (shelf_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return Shelf(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            book_count=await self._get_book_count(row["id"]),
        )

    async def get_by_name(self, name: str) -> Optional[Shelf]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM shelves WHERE name = ?", (name,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return Shelf(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            book_count=await self._get_book_count(row["id"]),
        )

    async def update(self, shelf_id: str, data: ShelfUpdate) -> Optional[Shelf]:
        shelf = await self.get(shelf_id)
        if not shelf:
            return None

        updates = []
        params = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)

        if data.description is not None:
            updates.append("description = ?")
            params.append(data.description)

        if updates:
            params.append(shelf_id)
            await self.db.conn.execute(
                f"UPDATE shelves SET {', '.join(updates)} WHERE id = ?", params
            )
            await self.db.conn.commit()

        return await self.get(shelf_id)

    async def delete(self, shelf_id: str) -> bool:
        # First remove from all books' shelves JSON arrays
        cursor = await self.db.conn.execute("SELECT id, shelves FROM books")
        rows = await cursor.fetchall()

        for row in rows:
            shelves = json.loads(row["shelves"] or "[]")
            if shelf_id in shelves:
                shelves.remove(shelf_id)
                await self.db.conn.execute(
                    "UPDATE books SET shelves = ? WHERE id = ?",
                    (json.dumps(shelves), row["id"]),
                )

        # Then delete the shelf itself
        cursor = await self.db.conn.execute(
            "DELETE FROM shelves WHERE id = ?", (shelf_id,)
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0

    async def list_all(self) -> list[Shelf]:
        cursor = await self.db.conn.execute("SELECT * FROM shelves ORDER BY created_at")
        rows = await cursor.fetchall()

        shelves = []
        for row in rows:
            shelves.append(
                Shelf(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    book_count=await self._get_book_count(row["id"]),
                )
            )
        return shelves


class SQLiteTagRepository(TagRepository):
    def __init__(self, db: SQLiteDatabase):
        self.db = db

    async def _get_book_count(self, tag_name: str) -> int:
        cursor = await self.db.conn.execute(
            "SELECT COUNT(*) FROM books WHERE tags LIKE ?", (f'%"{tag_name}"%',)
        )
        return (await cursor.fetchone())[0]

    async def create(self, tag: TagCreate) -> Tag:
        await self.db.conn.execute(
            "INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)",
            (tag.name, tag.color),
        )
        await self.db.conn.commit()

        return Tag(name=tag.name, color=tag.color, book_count=0)

    async def get(self, name: str) -> Optional[Tag]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM tags WHERE name = ?", (name,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return Tag(
            name=row["name"],
            color=row["color"],
            book_count=await self._get_book_count(row["name"]),
        )

    async def delete(self, name: str) -> bool:
        # First remove from all books' tags JSON arrays
        cursor = await self.db.conn.execute("SELECT id, tags FROM books")
        rows = await cursor.fetchall()

        for row in rows:
            tags = json.loads(row["tags"] or "[]")
            if name in tags:
                tags.remove(name)
                await self.db.conn.execute(
                    "UPDATE books SET tags = ? WHERE id = ?",
                    (json.dumps(tags), row["id"]),
                )

        # Then delete the tag itself
        cursor = await self.db.conn.execute("DELETE FROM tags WHERE name = ?", (name,))
        await self.db.conn.commit()
        return cursor.rowcount > 0

    async def list_all(self) -> list[Tag]:
        cursor = await self.db.conn.execute("SELECT * FROM tags ORDER BY name")
        rows = await cursor.fetchall()

        tags = []
        for row in rows:
            tags.append(
                Tag(
                    name=row["name"],
                    color=row["color"],
                    book_count=await self._get_book_count(row["name"]),
                )
            )
        return tags
