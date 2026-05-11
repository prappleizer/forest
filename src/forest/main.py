from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .db import (
    SQLiteBookRepository,
    SQLiteDatabase,
    SQLiteShelfRepository,
    SQLiteTagRepository,
)
from .routers import books, shelves, tags
from .routers import settings as settings_router

# Database instance
db = SQLiteDatabase(settings.database_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()

    # Initialize repositories
    book_repo = SQLiteBookRepository(db)
    shelf_repo = SQLiteShelfRepository(db)
    tag_repo = SQLiteTagRepository(db)

    # Inject into routers
    books.set_book_repo(book_repo)
    shelves.set_repos(shelf_repo, book_repo)
    tags.set_tag_repo(tag_repo)

    yield

    # Shutdown
    await db.disconnect()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.mount("/covers", StaticFiles(directory=str(settings.covers_dir)), name="covers")

# Templates
templates = Jinja2Templates(directory=str(settings.templates_dir))

# Include API routers
app.include_router(books.router)
app.include_router(shelves.router)
app.include_router(tags.router)
app.include_router(settings_router.router)


# Page routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page - add books"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/library", response_class=HTMLResponse)
async def library(request: Request):
    """Library view - browse books and shelves"""
    return templates.TemplateResponse("library.html", {"request": request})


@app.get("/book/{book_id}", response_class=HTMLResponse)
async def book_detail(request: Request, book_id: str):
    """Single book detail view"""
    return templates.TemplateResponse(
        "book.html", {"request": request, "book_id": book_id}
    )


@app.get("/tierlist", response_class=HTMLResponse)
async def tier_list(request: Request):
    """Tier list view"""
    return templates.TemplateResponse("tierlist.html", {"request": request})


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Reading stats dashboard"""
    return templates.TemplateResponse("stats.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    """Onboarding page for new users"""
    return templates.TemplateResponse("onboarding.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
