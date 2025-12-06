# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Automated daily search across online marketplaces (ShopGoodwill, eBay, Etsy, Craigslist, Ruby Lane, Mercari, Poshmark) to locate a lost antique ring. Captures screenshots of promising matches, maintains deduplicated URL tracking, and generates daily summary reports.

**Configuration**: Edit `config.yaml` to customize search keywords, scoring weights, and marketplace priorities.

## Development Commands

```bash
# Install dependencies
uv sync --extra dev
uv run playwright install chromium

# Run CLI (note: global options before subcommand)
uv run ring-search -c config.yaml run              # Daily search
uv run ring-search -c config.yaml run --headed     # With visible browser
uv run ring-search -c config.yaml run --adaptive   # With adaptive discovery
uv run ring-search -c config.yaml check-urls urls.txt  # Check specific URLs
uv run ring-search report                          # View most recent summary

# Testing
uv run pytest                    # Run all tests
uv run pytest tests/test_scoring.py  # Run single test file
uv run pytest -k "test_high"     # Run tests matching pattern
uv run pytest --cov=src          # With coverage

# Linting and type checking
uv run ruff check src/           # Lint
uv run ruff format src/          # Format
uv run mypy src/                 # Type check
```

## Architecture

```
SearchOrchestrator (src/ring_search.py)
├── MarketplaceAdapter (src/adapters/base.py) - Abstract interface
│   ├── ShopGoodwillAdapter, EbayAdapter, EtsyAdapter, CraigslistAdapter
│   ├── RubyLaneAdapter, MercariAdapter, PoshmarkAdapter
├── SearchDiscovery (src/discovery/base.py) - Search engine discovery [NEW]
│   ├── GoogleDiscovery, DuckDuckGoDiscovery
│   └── MarketplaceFilter - URL filtering and prioritization
├── AdaptiveExtractor (src/extractors/base.py) - Universal listing extraction [NEW]
│   ├── StructuredDataExtractor - JSON-LD, OpenGraph, microdata
│   ├── LegacyAdapterBridge - Routes to existing adapters
│   └── GenericListingExtractor - Heuristic fallback
├── RelevanceScorer (src/scoring.py) - Configurable weights for ring attributes
├── ScreenshotCapture (src/capture.py) - Full-page screenshots via Playwright
├── DedupManager (src/dedup.py) - Persistent URL tracking
└── SearchLogger (src/logger.py) - JSON logs and markdown summaries
```

**Adding a new marketplace**: Subclass `MarketplaceAdapter`, implement `search()` and `get_listing_details()`, register in `src/adapters/__init__.py` and add to `ADAPTER_MAP`.

**Adaptive mode**: Enable with `--adaptive` flag or set `discovery.enabled: true` in config.yaml. Discovers listings via search engines and extracts data using structured markup or heuristics.

## Data Directory Structure

```
finder/
└── YYYYMMDD_type_description/
    ├── input/    # Source materials (PDFs, images)
    └── output/   # Processed/generated files
```

### Naming Conventions

**Item folders**: `YYYYMMDD_type_description` (e.g., `20251201_ring_vintage-amethyst-pearl-gold`)

**Input files**:
- Product PDFs: Full product page title from source
- Product images: `ProductName_view.ext` where view is `top`, `side`, `hand_zi`, `hand_zo`
- Order confirmations: `YYYYMMDD_source - subject.pdf`

## Branch Structure

```
main                           ← Production (tagged vX.Y.Z)
  ↑
develop                        ← Integration branch
  ↑
contrib/<gh-user>             ← Personal contribution branch
```

### Branch Protection Policy

**Protected branches** (merge via PR only):
- `main` - Production branch
- `develop` - Integration branch

**Editable branches** (direct commits allowed):
- `contrib/*` - Personal contribution branches

### PR Flow

All changes flow: `contrib/<user>` → `develop` → `main`

## Critical Guidelines

- **ALWAYS prefer editing existing files** over creating new ones
- **End on editable branch**: All work should end on `contrib/*` (never `develop` or `main`)
- **Follow naming conventions** for item folders and files
