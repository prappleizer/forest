#!/usr/bin/env python3
"""
Cleanup script to remove orphaned shelf and tag references from books.
Run this once after updating to fix any existing orphaned data.

Usage: python cleanup_orphans.py
"""

import asyncio
import json
from pathlib import Path

import aiosqlite

DATABASE_PATH = Path.home() / ".forest" / "library.db"


async def cleanup():
    if not DATABASE_PATH.exists():
        print(f"Database not found at {DATABASE_PATH}")
        return

    print(f"Using database: {DATABASE_PATH}")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get all valid shelf IDs
        cursor = await db.execute("SELECT id FROM shelves")
        valid_shelves = {row[0] for row in await cursor.fetchall()}
        print(f"Found {len(valid_shelves)} valid shelves")

        # Get all valid tag names
        cursor = await db.execute("SELECT name FROM tags")
        valid_tags = {row[0] for row in await cursor.fetchall()}
        print(f"Found {len(valid_tags)} valid tags")

        # Get all books
        cursor = await db.execute("SELECT id, shelves, tags FROM books")
        books = await cursor.fetchall()

        shelf_cleanup_count = 0
        tag_cleanup_count = 0

        for book in books:
            book_id = book["id"]

            # Parse shelves JSON
            try:
                shelves = json.loads(book["shelves"] or "[]")
            except json.JSONDecodeError:
                shelves = []

            # Parse tags JSON
            try:
                tags = json.loads(book["tags"] or "[]")
            except json.JSONDecodeError:
                tags = []

            # Filter to only valid shelves/tags
            new_shelves = [s for s in shelves if s in valid_shelves]
            new_tags = [t for t in tags if t in valid_tags]

            # Update if changed
            shelves_changed = len(new_shelves) != len(shelves)
            tags_changed = len(new_tags) != len(tags)

            if shelves_changed:
                shelf_cleanup_count += len(shelves) - len(new_shelves)
            if tags_changed:
                tag_cleanup_count += len(tags) - len(new_tags)

            if shelves_changed or tags_changed:
                await db.execute(
                    "UPDATE books SET shelves = ?, tags = ? WHERE id = ?",
                    (json.dumps(new_shelves), json.dumps(new_tags), book_id),
                )

        await db.commit()

        print(f"Cleaned up {shelf_cleanup_count} orphaned shelf reference(s)")
        print(f"Cleaned up {tag_cleanup_count} orphaned tag reference(s)")


if __name__ == "__main__":
    asyncio.run(cleanup())
