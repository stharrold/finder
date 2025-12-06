# Architecture: Adaptive Marketplace Search

**Issue**: #6
**Slug**: adaptive-marketplace-search

## Current Architecture

```
SearchOrchestrator
├── MarketplaceAdapter (fixed list)
│   ├── ShopGoodwillAdapter
│   ├── EbayAdapter
│   ├── EtsyAdapter
│   ├── CraigslistAdapter
│   ├── RubyLaneAdapter
│   ├── MercariAdapter
│   └── PoshmarkAdapter (broken)
├── RelevanceScorer
├── ScreenshotCapture
├── DedupManager
└── SearchLogger
```

**Problems**:
- Fixed adapter list requires code changes to add sites
- Adapters break when sites change their HTML structure
- No way to discover new marketplaces

## Proposed Architecture

```
SearchOrchestrator
├── SearchDiscovery (NEW)
│   ├── GoogleSearchProvider
│   ├── DuckDuckGoProvider
│   └── BingProvider
├── AdaptiveExtractor (NEW)
│   ├── StructuredDataExtractor (JSON-LD, OpenGraph)
│   ├── GenericListingExtractor (heuristic-based)
│   └── LegacyAdapterBridge (wraps existing adapters)
├── MarketplaceAdapter (legacy, optional)
│   └── ... existing adapters (fallback only)
├── RelevanceScorer (unchanged)
├── ScreenshotCapture (unchanged)
├── DedupManager (unchanged)
└── SearchLogger (enhanced)
```

## Component Details

### SearchDiscovery

**Purpose**: Query search engines to find marketplace listings

```python
class SearchDiscovery:
    def search(self, keywords: list[str]) -> list[SearchResult]:
        """Query multiple search engines and aggregate results."""

    def filter_marketplace_urls(self, results: list[SearchResult]) -> list[str]:
        """Filter to known/detected marketplace domains."""
```

**Search Query Strategy**:
```
"{ring keywords}" site:facebook.com/marketplace
"{ring keywords}" site:ebay.com OR site:etsy.com OR site:poshmark.com
"{ring keywords}" "for sale" ring amethyst pearl
```

### AdaptiveExtractor

**Purpose**: Extract listing details from any URL without site-specific code

```python
class AdaptiveExtractor:
    def extract(self, url: str, page: Page) -> ListingDetails:
        """Extract listing details using multiple strategies."""

        # 1. Try structured data (most reliable)
        if structured := self.extract_structured_data(page):
            return structured

        # 2. Try legacy adapter if available
        if adapter := self.get_legacy_adapter(url):
            return adapter.extract(page)

        # 3. Fall back to heuristic extraction
        return self.extract_heuristic(page)
```

**Structured Data Sources**:
- JSON-LD `@type: Product`
- OpenGraph meta tags (`og:title`, `og:price:amount`)
- Schema.org microdata

### LegacyAdapterBridge

**Purpose**: Keep existing adapters working as fallbacks

```python
class LegacyAdapterBridge:
    def __init__(self):
        self.adapters = {
            'ebay.com': EbayAdapter(),
            'etsy.com': EtsyAdapter(),
            'poshmark.com': PoshmarkAdapter(),  # fixed
            ...
        }

    def get_adapter(self, url: str) -> MarketplaceAdapter | None:
        domain = urlparse(url).netloc
        return self.adapters.get(domain)
```

## Data Flow

```
1. SearchOrchestrator.run()
   │
2. SearchDiscovery.search(keywords)
   │ → Returns: [SearchResult(url, title, snippet), ...]
   │
3. For each URL:
   │
4. ScreenshotCapture.capture(url)
   │
5. AdaptiveExtractor.extract(url, page)
   │ → Returns: ListingDetails(title, price, description, images)
   │
6. RelevanceScorer.score(listing)
   │ → Returns: score (0-100)
   │
7. DedupManager.check(url)
   │ → Returns: is_new (bool)
   │
8. SearchLogger.log(listing, score)
```

## Configuration Changes

```yaml
# config.yaml
search:
  # NEW: Search engine providers
  discovery:
    providers:
      - google
      - duckduckgo
    max_results_per_provider: 50

  # NEW: Adaptive extraction settings
  extraction:
    prefer_structured_data: true
    use_legacy_adapters: true  # fallback to existing adapters

  # Existing (kept for backwards compatibility)
  marketplaces:
    - shopgoodwill
    - ebay
    # ... legacy adapters, used as hints for search
```

## Poshmark Adapter Fix

**Root Cause**: Page navigation during element iteration causes stale handles

**Fix**:
```python
# Before (broken)
for element in await page.query_selector_all('.listing'):
    title = await element.query_selector('.title')  # Fails if page changed

# After (fixed)
listings_data = await page.evaluate('''
    () => Array.from(document.querySelectorAll('.listing')).map(el => ({
        title: el.querySelector('.title')?.textContent,
        price: el.querySelector('.price')?.textContent,
        url: el.querySelector('a')?.href
    }))
''')
```

## Migration Path

1. **Phase 1**: Fix Poshmark adapter (immediate)
2. **Phase 2**: Add SearchDiscovery component
3. **Phase 3**: Add AdaptiveExtractor with structured data support
4. **Phase 4**: Integrate and test with existing scoring
5. **Phase 5**: Add Facebook Marketplace support via search discovery
