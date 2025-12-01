# Specification: Ring Search Automation

**Type:** feature
**Slug:** ring-search-automation
**Date:** 2025-12-01
**Author:** stharrold

## Overview

Automated daily search system to locate a lost antique ring (The Giulia Ring, BSB96044) across online marketplaces. The system uses Playwright browser automation to search ShopGoodwill (priority), eBay, Etsy, Craigslist, Ruby Lane, and 1stDibs. It scores listings based on match criteria (yellow gold, amethyst, seed pearls, Victorian/Edwardian style), captures screenshots of promising matches, and maintains a deduplicated log of all checked listings.


## Implementation Context

<!-- Generated from SpecKit interactive Q&A -->

**BMAD Planning:** See `planning/ring-search-automation/` for complete requirements and architecture.

**Implementation Preferences:**

- **Include E2E Tests:** True
- **Task Granularity:** Small tasks (1-2 hours each)
- **Additional Notes:** Focus on Playwright browser automation for marketplace scraping. Priority is ShopGoodwill due to loss location near Indianapolis Goodwill.

## Requirements Reference

See: `planning/ring-search-automation/requirements.md` in main repository

## Detailed Specification

### Component 1: Search Orchestrator

**File:** `src/ring_search.py`

**Purpose:** Main entry point that coordinates the search workflow across all marketplaces.

**Implementation:**

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class SearchConfig:
    marketplaces: list[dict]
    scoring: dict
    rate_limiting: dict
    output_dir: Path

class SearchOrchestrator:
    """Coordinates search across multiple marketplaces."""

    def __init__(self, config_path: Path):
        self.config = self._load_config(config_path)
        self.dedup = DedupManager(self.config.output_dir / "logs" / "checked_links.txt")
        self.logger = SearchLogger(self.config.output_dir / "logs")
        self.scorer = RelevanceScorer()

    async def run_daily_search(self) -> None:
        """Execute search across all configured marketplaces."""
        for marketplace in self.config.marketplaces:
            if not marketplace.get("enabled", True):
                continue
            adapter = MarketplaceAdapterFactory.create(marketplace["name"])
            async for listing in adapter.search(marketplace["searches"]):
                if self.dedup.is_new(listing.url):
                    scored = self.scorer.score(listing)
                    await self._process_listing(scored)
                    self.dedup.mark_checked(listing.url)
        self.logger.write_daily_summary()
```

**Dependencies:**
- `playwright` - Browser automation
- `pyyaml` - Configuration loading
- `pydantic` - Data validation

### Component 2: Marketplace Adapters

**File:** `src/adapters/base.py`, `src/adapters/shopgoodwill.py`, etc.

**Purpose:** Abstract interface and concrete implementations for each marketplace.

**Implementation:**

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass

@dataclass
class Listing:
    url: str
    source: str
    title: str
    price: str | None
    description: str | None
    image_url: str | None

class MarketplaceAdapter(ABC):
    """Base class for marketplace-specific scrapers."""

    @abstractmethod
    async def search(self, queries: list[str]) -> AsyncIterator[Listing]:
        """Yield listings matching search queries."""
        pass

class ShopGoodwillAdapter(MarketplaceAdapter):
    BASE_URL = "https://shopgoodwill.com"
    SELECTORS = {
        'listing': '.product-card',
        'title': '.product-title',
        'price': '.current-price',
        'link': 'a.product-link'
    }

class EbayAdapter(MarketplaceAdapter):
    BASE_URL = "https://www.ebay.com"
    SELECTORS = {
        'listing': '.s-item',
        'title': '.s-item__title',
        'price': '.s-item__price',
        'link': '.s-item__link'
    }
```

### Component 3: Relevance Scorer

**File:** `src/scoring.py`

**Purpose:** Score listings 0-100 based on match criteria for the target ring.

**Implementation:**

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class ScoringWeights:
    metal_yellow_gold: int = 20
    metal_10k: int = 10
    stone_amethyst: int = 25
    stone_purple: int = 15
    pearl_seed: int = 20
    pearl_any: int = 10
    design_swirl: int = 15
    design_floral: int = 5
    era_victorian: int = 10
    size_exact: int = 10  # Size 7
    size_close: int = 5   # Size 6-8

@dataclass
class ScoredListing:
    listing: Listing
    score: int
    confidence: Literal['high', 'medium', 'low']
    matched_factors: list[str]

class RelevanceScorer:
    THRESHOLDS = {'high': 70, 'medium': 40}

    def score(self, listing: Listing) -> ScoredListing:
        """Score listing based on match criteria."""
        score = 0
        factors = []
        text = f"{listing.title} {listing.description or ''}".lower()

        # Metal analysis
        if 'gold' in text:
            score += 20; factors.append('gold')
        if '10k' in text:
            score += 10; factors.append('10k')

        # Stone analysis
        if 'amethyst' in text:
            score += 25; factors.append('amethyst')
        elif 'purple' in text:
            score += 15; factors.append('purple stone')

        # Pearl analysis
        if 'seed pearl' in text:
            score += 20; factors.append('seed pearl')
        elif 'pearl' in text:
            score += 10; factors.append('pearl')

        # Design/era
        if any(w in text for w in ['swirl', 'infinity', 'figure-8']):
            score += 15; factors.append('swirl design')
        if any(w in text for w in ['victorian', 'edwardian', 'antique']):
            score += 10; factors.append('vintage era')

        confidence = 'high' if score >= 70 else ('medium' if score >= 40 else 'low')
        return ScoredListing(listing, score, confidence, factors)
```

### Component 4: Deduplication Manager

**File:** `src/dedup.py`

**Purpose:** Persistent URL tracking to avoid rechecking listings.

### Component 5: Screenshot Capture

**File:** `src/capture.py`

**Purpose:** Playwright-based full-page screenshot capture for promising listings.

### Component 6: Search Logger

**File:** `src/logger.py`

**Purpose:** Multi-format logging (JSON, Markdown daily summary, checked URLs).

## Data Models

### Model: Listing

**File:** `src/models.py`

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class Listing:
    """Raw listing from marketplace."""
    url: str
    source: str  # 'shopgoodwill', 'ebay', 'etsy', etc.
    title: str
    price: str | None
    description: str | None
    image_url: str | None

@dataclass
class ScoredListing:
    """Listing with relevance score."""
    url: str
    source: str
    title: str
    price: str | None
    score: int  # 0-100
    confidence: Literal['high', 'medium', 'low']
    matched_factors: list[str]

@dataclass
class LogEntry:
    """Entry in search_log.json."""
    timestamp: str  # ISO format
    url: str
    source: str
    title: str
    price: str | None
    confidence_score: int
    screenshot: str | None  # Path to screenshot
    status: str  # 'new', 'reviewed', 'dismissed'
```

## Configuration

**File:** `config.yaml`

```yaml
# Target ring details for reference
target_ring:
  name: "The Giulia Ring"
  style_number: "BSB96044"
  metal: "10K Yellow Gold"
  stones: ["Amethyst", "Seed Pearls"]
  size: 7
  lost_location: "Indianapolis, IN - Goodwill"

marketplaces:
  - name: shopgoodwill
    enabled: true
    priority: 1  # Highest priority (lost near Goodwill)
    searches:
      - "amethyst pearl ring"
      - "vintage gold ring amethyst"

  - name: ebay
    enabled: true
    priority: 2
    searches:
      - "amethyst pearl ring vintage gold"
      - "antique amethyst pearl ring 10k"

  - name: etsy
    enabled: true
    priority: 3
    searches:
      - "amethyst pearl gold vintage ring"

  - name: craigslist
    enabled: true
    priority: 4
    regions:
      - indianapolis
      - bloomington
      - fort-wayne
      - louisville
      - cincinnati

scoring:
  thresholds:
    high: 70
    medium: 40

rate_limiting:
  min_delay_seconds: 2
  max_delay_seconds: 5

output:
  base_dir: "output"
  screenshot_format: "png"
```

## CLI Interface

**Usage:**
```bash
# Run daily search
python -m ring_search run --config config.yaml

# Check specific URLs
python -m ring_search check-urls urls.txt --config config.yaml

# Generate report
python -m ring_search report --date 2024-11-30 --config config.yaml
```

## Testing Requirements

### Unit Tests

**File:** `tests/test_scoring.py`

```python
import pytest
from src.scoring import RelevanceScorer
from src.models import Listing

def test_score_high_confidence():
    """Test high confidence match (score >= 70)."""
    scorer = RelevanceScorer()
    listing = Listing(
        url="https://example.com/1",
        source="ebay",
        title="10K Yellow Gold Amethyst Seed Pearl Victorian Ring Size 7",
        price="$450",
        description="Beautiful antique swirl design",
        image_url=None
    )
    result = scorer.score(listing)
    assert result.confidence == "high"
    assert result.score >= 70
    assert "gold" in result.matched_factors
    assert "amethyst" in result.matched_factors

def test_score_low_confidence():
    """Test low confidence match (score < 40)."""
    scorer = RelevanceScorer()
    listing = Listing(
        url="https://example.com/2",
        source="ebay",
        title="Silver Ring with Blue Stone",
        price="$50",
        description=None,
        image_url=None
    )
    result = scorer.score(listing)
    assert result.confidence == "low"
    assert result.score < 40
```

### E2E Tests

**File:** `tests/e2e/test_search_flow.py`

```python
import pytest
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_shopgoodwill_search():
    """E2E test for ShopGoodwill search."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://shopgoodwill.com")
        # Test search functionality
        await browser.close()
```

## Quality Gates

- [ ] Test coverage ≥ 80%
- [ ] All tests passing
- [ ] Linting clean (ruff check)
- [ ] Type checking clean (mypy)
- [ ] API documentation complete

## Container Specifications

This is a CLI tool, not a web service. No containerization needed for MVP.

## Dependencies

**pyproject.toml:**

```toml
[project]
name = "ring-search-automation"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.40.0",
    "pyyaml>=6.0",
    "pydantic>=2.5.0",
    "aiofiles>=23.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-playwright>=0.4.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[project.scripts]
ring-search = "ring_search.cli:main"
```

## Implementation Notes

### Key Considerations

- **Rate limiting**: 2-5 second delays between requests to avoid blocks
- **CAPTCHA handling**: Log and skip, flag for manual review
- **URL normalization**: Strip tracking params to avoid duplicate checks
- **Screenshot storage**: Organize by date, confidence level, source

### Error Handling

- Network timeout: Retry 3x with exponential backoff, then skip
- Rate limited (429): Wait 60s, reduce request rate
- Parse error: Log error, skip listing, continue
- CAPTCHA detected: Log, skip listing, continue

### Known Leads (Check First)

These URLs should be checked at startup before general search:
1. Etsy UK: `https://www.etsy.com/uk/listing/1895838715/`
2. Pittsburgh Craigslist: `https://pittsburgh.craigslist.org/jwl/d/new-fancy-10k-gold-amethyst-ring/7893523856.html`
3. eBay: `https://www.ebay.com/itm/397177063712`

## References

- Planning: `planning/ring-search-automation/requirements.md`
- Architecture: `planning/ring-search-automation/architecture.md`
- Original ring info in `finder/20251201_ring_vintage-amethyst-pearl-gold/input/`
