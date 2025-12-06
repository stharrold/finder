# Specification: Bike Search

**Type:** feature
**Slug:** bike-search
**Date:** 2025-12-06
**Author:** stharrold

## Overview

This feature extends the existing marketplace search automation to efficiently locate Trek Allant+ 7S electric bikes across multiple online marketplaces. It leverages bike-specific scoring criteria to identify, rank, and report relevant listings, ensuring users can quickly find the best available options matching strict requirements (Class 3, 625Wh battery, range extender, Large frame).

## Implementation Context

<!-- Generated from SpecKit interactive Q&A -->

**BMAD Planning:** See `planning/bike-search/` for complete requirements and architecture.

**Implementation Preferences:**

- **Migration Strategy:** None needed
- **Task Granularity:** Small tasks (1-2 hours each)
- **Follow Epic Order:** True
- **Additional Notes:** Extend existing ring-search adapters for bike search. Reuse scoring, dedup, and reporting infrastructure.

## Requirements Reference

See: `planning/bike-search/requirements.md` in main repository

## Detailed Specification

### Component 1: BikeRelevanceScorer

**File:** `src/bike_scoring.py`

**Purpose:** Scores listings based on Trek Allant+ 7S match criteria with configurable weights.

**Implementation:**

```python
class BikeRelevanceScorer:
    """Scores listings based on match criteria for Trek Allant+ 7S."""

    THRESHOLDS = {"high": 70, "medium": 40}

    def __init__(self, weights: BikeScoringWeights | None = None):
        self.weights = weights or BikeScoringWeights()

    def score(self, listing: Listing) -> ScoredListing:
        """Score a listing based on Trek Allant+ 7S match criteria."""
        # Analyzes: model, class, battery, range extender, frame size
        pass
```

**Scoring Weights:**
- `model_allant_7s`: 40 (exact model match)
- `model_allant_7_penalty`: -30 (wrong model - Class 1)
- `class_3`: 20 (28 mph confirmed)
- `class_1_penalty`: -25 (20 mph - reject)
- `battery_625wh`: 20 (required capacity)
- `battery_500wh_penalty`: -15 (insufficient)
- `range_extender`: 15 (second battery)
- `frame_large`: 5 (correct size)

**Dependencies:**
- `src/models.py` (BikeScoringWeights, Listing, ScoredListing)

### Component 2: BikeSearchOrchestrator

**File:** `src/bike_search.py`

**Purpose:** Coordinates bike search across marketplaces with bike-specific configuration.

**Implementation:**

```python
class BikeSearchOrchestrator(SearchOrchestrator):
    """Orchestrator specialized for Trek Allant+ 7S searches."""

    def __init__(self, config: dict, headed: bool = False):
        super().__init__(config, headed)
        self.scorer = BikeRelevanceScorer(
            weights=BikeScoringWeights(**config.get("scoring", {}).get("weights", {}))
        )


def create_orchestrator(config: dict, headed: bool = False) -> SearchOrchestrator:
    """Factory function to create appropriate orchestrator based on config."""
    if "bike" in config.get("search_type", "ring").lower():
        return BikeSearchOrchestrator(config, headed)
    return SearchOrchestrator(config, headed)
```

**Dependencies:**
- `src/ring_search.py` (SearchOrchestrator base class)
- `src/bike_scoring.py` (BikeRelevanceScorer)

### Component 3: PinkbikeAdapter

**File:** `src/adapters/pinkbike.py`

**Purpose:** Searches Pinkbike Buy/Sell for e-bike listings.

**Implementation:**

```python
class PinkbikeAdapter(MarketplaceAdapter):
    """Adapter for Pinkbike marketplace."""

    BASE_URL = "https://www.pinkbike.com/buysell/list/"

    async def search(self, query: str, location: str | None = None) -> list[str]:
        """Search Pinkbike for e-bike listings."""
        pass

    async def get_listing_details(self, url: str) -> Listing | None:
        """Extract listing details from Pinkbike URL."""
        pass
```

**Dependencies:**
- `src/adapters/base.py` (MarketplaceAdapter)
- Playwright for browser automation

### Component 4: TrekRedBarnAdapter

**File:** `src/adapters/trek_redbarn.py`

**Purpose:** Searches Trek Red Barn Refresh certified pre-owned inventory.

**Implementation:**

```python
class TrekRedBarnAdapter(MarketplaceAdapter):
    """Adapter for Trek Red Barn Refresh certified pre-owned bikes."""

    BASE_URL = "https://www.trekbikes.com/us/en_US/certified-used-bikes/"

    async def search(self, query: str, location: str | None = None) -> list[str]:
        """Search Trek Red Barn for Allant+ models."""
        pass

    async def get_listing_details(self, url: str) -> Listing | None:
        """Extract listing details from Trek Red Barn URL."""
        pass
```

**Dependencies:**
- `src/adapters/base.py` (MarketplaceAdapter)
- Playwright for browser automation

## Data Models

### Model: BikeScoringWeights

**File:** `src/models.py`

```python
@dataclass
class BikeScoringWeights:
    """Configurable weights for bike relevance scoring."""

    model_allant_7s: int = 40
    model_allant_7_penalty: int = -30
    model_allant_plus: int = 10
    class_3: int = 20
    class_1_penalty: int = -25
    battery_625wh: int = 20
    battery_500wh_penalty: int = -15
    range_extender: int = 15
    frame_large: int = 5
```

## Configuration

### bike_config.yaml

```yaml
search_type: bike

target:
  brand: Trek
  model: Allant+ 7S
  class: 3
  max_speed_mph: 28
  battery_wh: 625
  range_extender: required
  frame_size: Large

location:
  center: "Indianapolis, IN 46220"
  radius_miles: 300

scoring:
  weights:
    model_allant_7s: 40
    class_3: 20
    battery_625wh: 20
    range_extender: 15
    frame_large: 5

marketplaces:
  - name: ebay
    enabled: true
  - name: craigslist
    enabled: true
  - name: pinkbike
    enabled: true
  - name: trek_redbarn
    enabled: true
```

## Testing Requirements

### Unit Tests

**File:** `tests/test_bike_scoring.py`

```python
def test_allant_7s_full_match():
    """Test perfect match for Allant+ 7S with all requirements."""
    scorer = BikeRelevanceScorer()
    listing = Listing(
        url="https://example.com/bike",
        source="test",
        title="Trek Allant+ 7S Large 625Wh with Range Extender",
        description="Class 3 28mph e-bike"
    )
    result = scorer.score(listing)
    assert result.score >= 70
    assert result.confidence == "high"

def test_allant_7_rejection():
    """Test that Allant+ 7 (Class 1) is penalized."""
    scorer = BikeRelevanceScorer()
    listing = Listing(
        url="https://example.com/bike",
        source="test",
        title="Trek Allant+ 7 Class 1 20mph"
    )
    result = scorer.score(listing)
    assert result.score < 40
    assert "WRONG" in str(result.matched_factors)
```

### Integration Tests

**File:** `tests/test_bike_integration.py`

```python
def test_create_orchestrator_bike():
    """Test factory creates BikeSearchOrchestrator for bike config."""
    config = {"search_type": "bike"}
    orchestrator = create_orchestrator(config)
    assert isinstance(orchestrator, BikeSearchOrchestrator)

def test_create_orchestrator_ring():
    """Test factory creates SearchOrchestrator for ring config."""
    config = {"search_type": "ring"}
    orchestrator = create_orchestrator(config)
    assert isinstance(orchestrator, SearchOrchestrator)
```

## Quality Gates

- [x] Test coverage >= 80%
- [x] All tests passing
- [x] Linting clean (ruff check)
- [x] Type checking clean (mypy)
- [x] CLI works with both ring and bike configs

## Implementation Notes

### Key Considerations

- Allant+ 7S vs Allant+ 7 distinction is critical (Class 3 vs Class 1)
- Battery capacity validation requires parsing "625Wh" patterns
- Range extender detection uses multiple synonyms (dual battery, second battery, etc.)
- Frame size matching avoids false positives from single-letter "L" patterns

### Error Handling

- Per-adapter error isolation (one failing marketplace doesn't stop others)
- Graceful degradation if marketplace unavailable
- Retry with exponential backoff for transient failures

### Validation Rules

- **REJECT:** Allant+ 7 (non-S) models
- **REJECT:** 500Wh battery only (no upgrade)
- **REJECT:** Class 1 (20 mph) confirmed
- **PARTIAL:** 625Wh without range extender (flag for follow-up)

## References

- [Trek Allant+ 7S Specs](https://www.trekbikes.com/us/en_US/bikes/hybrid-bikes/electric-hybrid-bikes/allant/allant-7s/p/35017/)
- [planning/bike-search/requirements.md](../../planning/bike-search/requirements.md)
- [planning/bike-search/architecture.md](../../planning/bike-search/architecture.md)
