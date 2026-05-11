# 🌲 Forest

A personal book library manager for tracking your reading journey.

## Features

- **Search & Add Books**: Search Open Library's database to add books to your collection
- **Custom Shelves & Tags**: Organize with shelves (Owned, TBR, etc.) and custom tags
- **Reading Progress**: Track start/finish dates and page progress
- **Flexible Ratings**: 
  - Overall 0-5 rating with 0.1 increments
  - Customizable rating categories (Writing, Characters, Plot, etc.)
  - Letter grades (S/A/B/C/D/E/F/DNF) for tier ranking
- **Tier List View**: Visual tier list of all your rated books
- **Reviews**: Write reviews for each book

## Installation

```bash
pip install forest
```

Or install from source:

```bash
git clone https://github.com/yourusername/forest.git
cd forest
pip install -e .
```

## Usage

Start the app:

```bash
forest
```

This will start the server and open your browser to http://localhost:8000

### Command Line Options

```bash
forest --help                 # Show all options
forest --port 8080           # Use different port
forest --no-browser          # Don't auto-open browser
forest --reload              # Enable auto-reload for development
```

## Data Location

All your data is stored in `~/.forest/`:

- `library.db` - SQLite database with all your books
- `covers/` - Downloaded book cover images
- `settings.json` - Your preferences and rating categories

To use a custom location, set the `FOREST_DATA_DIR` environment variable.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run with auto-reload
forest --reload
```

## License

MIT License
