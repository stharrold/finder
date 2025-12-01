# Architecture: Lost Ring Search Automation

**Version:** 1.0.0
**Date:** 2024-11-30

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Ring Search Automation                    │
├─────────────────────────────────────────────────────────────┤
│  Scheduler (cron)                                           │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   Search    │───▶│   Scoring    │───▶│  Screenshot   │  │
│  │  Orchestrator│    │    Engine    │    │   Capture     │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│       │                    │                    │           │
│       ▼                    ▼                    ▼           │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Marketplace │    │  Dedup       │    │    Logger     │  │
│  │  Adapters   │    │  Manager     │    │               │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Search Orchestrator (`ring_search.py`)

Main entry point that coordinates the search workflow:

```python
class SearchOrchestrator:
    def __init__(self, config_path: Path):
        self.config = load_config(config_path)
        self.dedup = DedupManager()
        self.logger = SearchLogger()
        self.scorer = RelevanceScorer()

    async def run_daily_search(self):
        """Execute search across all marketplaces."""
        for marketplace in self.config.marketplaces:
            adapter = MarketplaceAdapterFactory.create(marketplace)
            async for listing in adapter.search():
                if self.dedup.is_new(listing.url):
                    score = self.scorer.score(listing)
                    await self.process_listing(listing, score)
                    self.dedup.mark_checked(listing.url)

        self.logger.write_daily_summary()
```

### 2. Marketplace Adapters

Abstract base class with concrete implementations per site:

```python
class MarketplaceAdapter(ABC):
    @abstractmethod
    async def search(self) -> AsyncIterator[Listing]:
        """Yield listings matching search criteria."""
        pass

    @abstractmethod
    def get_listing_details(self, url: str) -> ListingDetails:
        """Extract structured data from listing page."""
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

class EtsyAdapter(MarketplaceAdapter):
    BASE_URL = "https://www.etsy.com"
    SELECTORS = {
        'listing': '.v2-listing-card',
        'title': '.v2-listing-card__title',
        'price': '.currency-value'
    }
```

### 3. Relevance Scorer

Configurable scoring engine:

```python
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
    size_exact: int = 10
    size_close: int = 5

class RelevanceScorer:
    THRESHOLDS = {
        'high': 70,
        'medium': 40
    }

    def score(self, listing: Listing) -> ScoredListing:
        score = 0
        factors = []

        # Metal analysis
        if 'gold' in listing.title.lower():
            score += self.weights.metal_yellow_gold
            factors.append('gold')
        if '10k' in listing.title.lower():
            score += self.weights.metal_10k
            factors.append('10k')

        # ... additional scoring logic

        confidence = self._classify(score)
        return ScoredListing(listing, score, confidence, factors)
```

### 4. Deduplication Manager

Persistent URL tracking:

```python
class DedupManager:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._cache: Set[str] = set()
        self._load()

    def _normalize_url(self, url: str) -> str:
        """Strip tracking params, normalize case."""
        parsed = urlparse(url)
        # Keep only essential query params
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def is_new(self, url: str) -> bool:
        return self._normalize_url(url) not in self._cache

    def mark_checked(self, url: str):
        normalized = self._normalize_url(url)
        self._cache.add(normalized)
        with open(self.log_path, 'a') as f:
            f.write(f"{normalized}\n")
```

### 5. Screenshot Capture

Playwright-based capture:

```python
class ScreenshotCapture:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    async def capture(self, page: Page, listing: ScoredListing) -> Path:
        date_folder = self.output_dir / datetime.now().strftime("%Y-%m-%d")
        date_folder.mkdir(parents=True, exist_ok=True)

        filename = f"{listing.confidence}_{listing.source}_{timestamp()}.png"
        filepath = date_folder / filename

        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.goto(listing.url)
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path=str(filepath), full_page=True)

        return filepath
```

### 6. Search Logger

Multi-format logging:

```python
class SearchLogger:
    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.search_log = logs_dir / "search_log.json"
        self.daily_results: List[LogEntry] = []

    def log_result(self, listing: ScoredListing, screenshot: Optional[Path]):
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            url=listing.url,
            source=listing.source,
            title=listing.title,
            price=listing.price,
            confidence_score=listing.score,
            screenshot=str(screenshot) if screenshot else None,
            status="new"
        )
        self.daily_results.append(entry)
        self._append_to_json(entry)

    def write_daily_summary(self):
        """Generate markdown summary of today's search."""
        date = datetime.now().strftime("%Y-%m-%d")
        summary_path = self.logs_dir / f"daily_summary_{date}.md"

        content = self._render_summary_template(
            date=date,
            total=len(self.daily_results),
            high=[r for r in self.daily_results if r.confidence == 'high'],
            medium=[r for r in self.daily_results if r.confidence == 'medium']
        )
        summary_path.write_text(content)
```

## Data Models

```python
@dataclass
class Listing:
    url: str
    source: str
    title: str
    price: Optional[str]
    description: Optional[str]
    image_url: Optional[str]

@dataclass
class ScoredListing(Listing):
    score: int
    confidence: Literal['high', 'medium', 'low']
    matched_factors: List[str]

@dataclass
class LogEntry:
    timestamp: str
    url: str
    source: str
    title: str
    price: Optional[str]
    confidence_score: int
    screenshot: Optional[str]
    status: str
```

## Configuration

```yaml
# config.yaml
marketplaces:
  - name: shopgoodwill
    enabled: true
    priority: 1
    searches:
      - "amethyst pearl ring"
      - "vintage gold ring"

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

## File Structure

```
20251201_ring_vintage-amethyst-pearl-gold/
├── input/                              # Reference materials (existing)
│   ├── Brilliant_Earth_*.jpg           # Original ring photos
│   └── *.pdf                           # Order documentation
│
├── output/                             # Generated outputs
│   ├── reference/                      # Copied reference images
│   ├── screenshots/
│   │   └── 2024-11-30/
│   │       ├── high_ebay_20241130_060512.png
│   │       └── medium_etsy_20241130_061023.png
│   ├── logs/
│   │   ├── search_log.json
│   │   ├── checked_links.txt
│   │   └── daily_summary_2024-11-30.md
│   └── potential_matches/
│       └── high_confidence/
│
├── src/                                # Source code
│   ├── __init__.py
│   ├── ring_search.py                  # Main orchestrator
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── shopgoodwill.py
│   │   ├── ebay.py
│   │   ├── etsy.py
│   │   └── craigslist.py
│   ├── scoring.py
│   ├── dedup.py
│   ├── capture.py
│   └── logger.py
│
├── config.yaml
├── requirements.txt
└── README.md
```

## Dependencies

```
# requirements.txt
playwright>=1.40.0
pyyaml>=6.0
pydantic>=2.0
aiofiles>=23.0
```

## Execution Flow

1. **Initialization**
   - Load configuration
   - Initialize dedup manager (load checked_links.txt)
   - Initialize logger
   - Create output directories

2. **Per Marketplace**
   - Create adapter instance
   - For each search query:
     - Navigate to search page
     - Paginate through results
     - Extract listing URLs

3. **Per Listing**
   - Check dedup (skip if seen)
   - Extract listing details
   - Score relevance
   - If high/medium: capture screenshot
   - Log result
   - Mark as checked

4. **Finalization**
   - Write daily summary
   - Copy high-confidence to potential_matches/
   - Log completion status

## Error Handling

| Error Type | Response |
|------------|----------|
| Network timeout | Retry 3x with backoff, then skip |
| CAPTCHA detected | Log, skip listing, continue |
| Rate limited | Wait 60s, reduce request rate |
| Parse error | Log error, skip listing, continue |
| Screenshot fail | Log error, continue without screenshot |

## Future Enhancements

1. **Image Similarity** - Compare listing images to reference photos
2. **Email Alerts** - Send notification on high-confidence matches
3. **Browser Session** - Persist cookies for sites requiring login
4. **Proxy Rotation** - Avoid IP-based rate limiting
5. **ML Scoring** - Train model on visual ring characteristics
