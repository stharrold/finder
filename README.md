# Finder - Ring Search Automation

Automated daily search across online marketplaces to locate a lost antique ring. Captures screenshots of promising matches, maintains a deduplicated log of all checked listings, and generates daily summary reports.

## Features

- **Multi-Marketplace Search**: ShopGoodwill, eBay, Etsy, Craigslist
- **Relevance Scoring**: Configurable weights for metal, stone, pearl, design, era, size
- **Screenshot Capture**: Full-page screenshots of promising matches
- **Deduplication**: Persistent URL tracking to avoid rechecking listings
- **Daily Reports**: Markdown summaries with match statistics

## Installation

```bash
# Clone and install dependencies
git clone https://github.com/stharrold/finder.git
cd finder
uv sync

# Install Playwright browser
uv run playwright install chromium
```

## Usage

```bash
# Run daily search across all marketplaces
uv run ring-search run --config config.yaml

# Check specific URLs from a file
uv run ring-search check-urls urls.txt --config config.yaml

# View most recent daily summary
uv run ring-search report

# Run with visible browser (for debugging)
uv run ring-search run --headed
```

## Configuration

Edit `config.yaml` to customize:
- Marketplace priorities and search keywords
- Scoring weights for relevance calculation
- Output directories and rate limiting
- Known leads to check first

## Output Structure

```
output/
├── screenshots/
│   └── YYYY-MM-DD/
│       └── {confidence}_{source}_{timestamp}.png
├── logs/
│   ├── search_log.json          # Master log of all searches
│   ├── checked_links.txt        # Deduplicated URL list
│   └── daily_summary_YYYY-MM-DD.md
└── potential_matches/
    └── high_confidence/
```

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Type checking
uv run mypy src/
```

## Project Structure

- `src/` - Ring search automation implementation
- `tests/` - Test suite (107 tests, 62% coverage)
- `planning/` - BMAD planning documents
- `specs/` - SpecKit specifications
- `.claude/` - Workflow commands and skills

## License

Private repository for personal use.
