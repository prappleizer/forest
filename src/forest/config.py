from pydantic_settings import BaseSettings
from pathlib import Path
import os


def get_data_dir() -> Path:
    """
    Get the data directory for Forest.
    Uses ~/.forest by default, or FOREST_DATA_DIR env var.
    """
    if env_dir := os.environ.get("FOREST_DATA_DIR"):
        return Path(env_dir)
    return Path.home() / ".forest"


class Settings(BaseSettings):
    app_name: str = "Forest"
    debug: bool = False
    
    # Package directory (where code lives)
    package_dir: Path = Path(__file__).parent
    
    # Data directory (where user data lives)
    data_dir: Path = get_data_dir()
    
    @property
    def database_path(self) -> Path:
        return self.data_dir / "library.db"
    
    @property
    def covers_dir(self) -> Path:
        return self.data_dir / "covers"
    
    @property
    def templates_dir(self) -> Path:
        return self.package_dir / "frontend" / "templates"
    
    @property
    def static_dir(self) -> Path:
        return self.package_dir / "frontend" / "static"
    
    # Database
    db_type: str = "sqlite"
    
    # Open Library API
    open_library_search_url: str = "https://openlibrary.org/search.json"
    open_library_works_url: str = "https://openlibrary.org/works"
    open_library_covers_url: str = "https://covers.openlibrary.org/b"
    
    class Config:
        env_file = ".env"


settings = Settings()

# Ensure data directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.covers_dir.mkdir(parents=True, exist_ok=True)
