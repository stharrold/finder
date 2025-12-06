# Finder - Marketplace Search Automation

Automated daily search across online marketplaces to locate specific items. Supports multiple search profiles with configurable scoring, captures screenshots of promising matches, and generates daily summary reports.

## Search Profiles

- **Ring Search** (`config.yaml`): Lost antique ring - 10K yellow gold with amethyst and seed pearls
- **Bike Search** (`bike_config.yaml`): Trek Allant+ 7S e-bike - Class 3, 625Wh battery, range extender, Large frame

## Features

- **Multi-Marketplace Search**: ShopGoodwill, eBay, Etsy, Craigslist, Poshmark, Mercari, Ruby Lane, Pinkbike, Trek Red Barn
- **Adaptive Discovery**: Search engine discovery via DuckDuckGo for any marketplace
- **Relevance Scoring**: Configurable weights per search profile
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
# Ring search
uv run ring-search -c config.yaml run
uv run ring-search -c config.yaml run --headed     # Visible browser
uv run ring-search -c config.yaml run --adaptive   # With adaptive discovery

# Bike search (Trek Allant+ 7S)
uv run ring-search -c bike_config.yaml run
uv run ring-search -c bike_config.yaml run --headed

# Check specific URLs
uv run ring-search -c config.yaml check-urls urls.txt

# View most recent daily summary
uv run ring-search report
```

## Configuration

Edit `config.yaml` (ring) or `bike_config.yaml` (bike) to customize:
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

- `src/` - Marketplace search automation implementation
- `tests/` - Test suite (189 tests)
- `planning/` - BMAD planning documents
- `specs/` - SpecKit specifications
- `.claude/` - Workflow commands and skills

## License

Private repository for personal use.
