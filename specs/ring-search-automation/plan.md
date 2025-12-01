# Implementation Plan: Ring Search Automation

**Type:** feature
**Slug:** ring-search-automation
**Date:** 2025-12-01


## Task Breakdown

### Phase 1: Foundation & Data Models

#### Task impl_001: Project Setup & Data Models

**Priority:** High

**Files:**
- `pyproject.toml`
- `src/__init__.py`
- `src/models.py`
- `config.yaml`

**Description:**
Set up project structure, define data models (Listing, ScoredListing, LogEntry), and create configuration schema.

**Steps:**
1. Create pyproject.toml with dependencies (playwright, pyyaml, pydantic, aiofiles)
2. Create src/ package structure
3. Define dataclasses in models.py
4. Create config.yaml with marketplace settings and scoring weights

**Acceptance Criteria:**
- [ ] `uv sync` installs all dependencies
- [ ] `playwright install chromium` succeeds
- [ ] Models can be imported: `from src.models import Listing`
- [ ] Config loads without errors

**Verification:**
```bash
uv sync
uv run python -c "from src.models import Listing, ScoredListing; print('OK')"
```

**Dependencies:** None

---

#### Task impl_002: Deduplication Manager

**Priority:** High

**Files:**
- `src/dedup.py`
- `tests/test_dedup.py`

**Description:**
Implement URL deduplication with persistent storage and URL normalization.

**Steps:**
1. Implement DedupManager class with file-based persistence
2. Add URL normalization (strip query params, normalize scheme)
3. Implement is_new() and mark_checked() methods
4. Write unit tests

**Acceptance Criteria:**
- [ ] URLs are normalized before checking
- [ ] Duplicate URLs are detected
- [ ] State persists across restarts
- [ ] Tests pass

**Verification:**
```bash
uv run pytest tests/test_dedup.py -v
```

**Dependencies:** impl_001

---

### Phase 2: Scoring Engine

#### Task impl_003: Relevance Scorer

**Priority:** High

**Files:**
- `src/scoring.py`
- `tests/test_scoring.py`

**Description:**
Implement scoring engine with configurable weights for ring matching criteria.

**Steps:**
1. Define ScoringWeights dataclass with default values from requirements
2. Implement RelevanceScorer.score() method
3. Add text analysis for metal, stone, pearl, design, era keywords
4. Implement confidence classification (high/medium/low)
5. Write comprehensive unit tests

**Acceptance Criteria:**
- [ ] Scores range 0-100
- [ ] High confidence ≥70, Medium 40-69, Low <40
- [ ] All scoring factors from requirements implemented
- [ ] Tests verify edge cases

**Verification:**
```bash
uv run pytest tests/test_scoring.py -v --cov=src.scoring
```

**Dependencies:** impl_001

---

### Phase 3: Marketplace Adapters

#### Task impl_004: Base Adapter & ShopGoodwill

**Priority:** High

**Files:**
- `src/adapters/__init__.py`
- `src/adapters/base.py`
- `src/adapters/shopgoodwill.py`
- `tests/test_adapters.py`

**Description:**
Implement abstract MarketplaceAdapter base class and ShopGoodwill adapter (highest priority marketplace).

**Steps:**
1. Define abstract base class with search() async generator
2. Implement ShopGoodwillAdapter with Playwright
3. Add search query execution and listing extraction
4. Implement rate limiting between requests
5. Write tests with mocked responses

**Acceptance Criteria:**
- [ ] Adapter yields Listing objects from search results
- [ ] Rate limiting delays 2-5 seconds between requests
- [ ] Handles pagination
- [ ] Tests mock Playwright interactions

**Verification:**
```bash
uv run pytest tests/test_adapters.py::test_shopgoodwill -v
```

**Dependencies:** impl_001, impl_002

---

#### Task impl_005: eBay & Etsy Adapters

**Priority:** Medium

**Files:**
- `src/adapters/ebay.py`
- `src/adapters/etsy.py`

**Description:**
Implement eBay and Etsy marketplace adapters.

**Steps:**
1. Implement EbayAdapter with appropriate selectors
2. Implement EtsyAdapter with appropriate selectors
3. Add marketplace-specific pagination handling
4. Write tests for each adapter

**Acceptance Criteria:**
- [ ] Both adapters extract listings correctly
- [ ] Pagination works for multi-page results
- [ ] Tests pass

**Verification:**
```bash
uv run pytest tests/test_adapters.py -v
```

**Dependencies:** impl_004

---

#### Task impl_006: Craigslist Adapter

**Priority:** Medium

**Files:**
- `src/adapters/craigslist.py`

**Description:**
Implement Craigslist adapter with multi-region support (Indianapolis, Bloomington, Fort Wayne, Louisville, Cincinnati).

**Steps:**
1. Implement CraigslistAdapter with region configuration
2. Handle Craigslist's specific page structure
3. Support searching multiple regions
4. Add tests

**Acceptance Criteria:**
- [ ] Searches configured regions
- [ ] Handles Craigslist's layout
- [ ] Tests pass

**Dependencies:** impl_004

---

### Phase 4: Screenshot & Logging

#### Task impl_007: Screenshot Capture

**Priority:** High

**Files:**
- `src/capture.py`
- `tests/test_capture.py`

**Description:**
Implement Playwright-based screenshot capture with organized output.

**Steps:**
1. Implement ScreenshotCapture class
2. Create date-based output directories
3. Name files: `{confidence}_{source}_{timestamp}.png`
4. Handle full-page captures
5. Write tests

**Acceptance Criteria:**
- [ ] Screenshots saved to `output/screenshots/YYYY-MM-DD/`
- [ ] Filename format correct
- [ ] Full page captured
- [ ] Tests pass

**Verification:**
```bash
uv run pytest tests/test_capture.py -v
```

**Dependencies:** impl_001

---

#### Task impl_008: Search Logger

**Priority:** High

**Files:**
- `src/logger.py`
- `tests/test_logger.py`

**Description:**
Implement multi-format logging (JSON, Markdown summary, checked URLs).

**Steps:**
1. Implement SearchLogger class
2. Add JSON append logging to search_log.json
3. Generate daily Markdown summaries
4. Write tests

**Acceptance Criteria:**
- [ ] JSON log appends without data loss
- [ ] Daily summary generated with stats
- [ ] High/medium confidence listings highlighted
- [ ] Tests pass

**Verification:**
```bash
uv run pytest tests/test_logger.py -v
```

**Dependencies:** impl_001

---

### Phase 5: Orchestration & CLI

#### Task impl_009: Search Orchestrator

**Priority:** High

**Files:**
- `src/ring_search.py`
- `tests/test_ring_search.py`

**Description:**
Implement main orchestrator that coordinates all components.

**Steps:**
1. Implement SearchOrchestrator class
2. Load config and initialize components
3. Implement run_daily_search() workflow
4. Add known leads checking at startup
5. Write integration tests

**Acceptance Criteria:**
- [ ] Orchestrates full search workflow
- [ ] Checks known leads first
- [ ] Handles errors gracefully
- [ ] Tests pass

**Verification:**
```bash
uv run pytest tests/test_ring_search.py -v
```

**Dependencies:** impl_002, impl_003, impl_004, impl_007, impl_008

---

#### Task impl_010: CLI Interface

**Priority:** Medium

**Files:**
- `src/cli.py`

**Description:**
Implement command-line interface for running searches and generating reports.

**Steps:**
1. Add argparse-based CLI
2. Implement `run` command for daily search
3. Implement `check-urls` command for specific URLs
4. Implement `report` command for generating summaries

**Acceptance Criteria:**
- [ ] `ring-search run --config config.yaml` executes search
- [ ] `ring-search check-urls urls.txt` checks specific URLs
- [ ] Help text is clear

**Verification:**
```bash
uv run ring-search --help
```

**Dependencies:** impl_009

---

### Phase 6: Testing & Quality

#### Task test_001: Unit Tests

**Priority:** High

**Files:**
- `tests/conftest.py`
- `tests/test_*.py`

**Description:**
Comprehensive unit tests for all modules with ≥80% coverage.

**Acceptance Criteria:**
- [ ] Coverage ≥80%
- [ ] All edge cases tested
- [ ] Mocked external dependencies

**Verification:**
```bash
uv run pytest --cov=src --cov-report=term --cov-fail-under=80
```

**Dependencies:** All impl_* tasks

---

#### Task test_002: E2E Tests

**Priority:** Medium

**Files:**
- `tests/e2e/test_search_flow.py`

**Description:**
End-to-end tests with real browser automation against live sites (rate-limited).

**Acceptance Criteria:**
- [ ] Tests run against real marketplaces
- [ ] Respects rate limiting
- [ ] Can be skipped in CI with marker

**Verification:**
```bash
uv run pytest tests/e2e/ -v -m "not slow"
```

**Dependencies:** impl_009, test_001

---

## Task Dependencies Graph

```
impl_001 ──┬──> impl_002 ──┬──> impl_004 ──> impl_005
           │               │               ──> impl_006
           ├──> impl_003 ──┤
           ├──> impl_007 ──┼──> impl_009 ──> impl_010 ──> test_001 ──> test_002
           └──> impl_008 ──┘
```

## Critical Path

1. impl_001 (Foundation)
2. impl_002 (Dedup) + impl_003 (Scoring) + impl_007 (Screenshots) + impl_008 (Logger) [parallel]
3. impl_004 (ShopGoodwill adapter)
4. impl_009 (Orchestrator)
5. impl_010 (CLI)
6. test_001 (Unit tests)

## Parallel Work Opportunities

- impl_002, impl_003, impl_007, impl_008 can all be done in parallel after impl_001
- impl_005 and impl_006 can be done in parallel after impl_004
- test_001 can start as soon as individual modules are complete

## Quality Checklist

Before considering this feature complete:

- [ ] All tasks marked as complete
- [ ] Test coverage ≥ 80%
- [ ] All tests passing (unit + E2E)
- [ ] Linting clean (`uv run ruff check src/ tests/`)
- [ ] Type checking clean (`uv run mypy src/`)
- [ ] Manual test: run search and verify screenshot output
- [ ] Known leads checked successfully
- [ ] Daily summary markdown renders correctly

## Risk Assessment

### High Risk Tasks

- **impl_004 (ShopGoodwill)**: Site structure may change, CAPTCHA may block
  - Mitigation: Use robust selectors, implement CAPTCHA detection

- **impl_005/impl_006 (Other adapters)**: Each site has different anti-scraping measures
  - Mitigation: Implement per-site rate limiting, handle gracefully

### Medium Risk Tasks

- **impl_009 (Orchestrator)**: Complex async coordination
  - Mitigation: Comprehensive integration tests

## Notes

### Implementation Tips

- Use Playwright's `wait_for_selector` with timeouts to handle slow-loading pages
- Store reference images from `finder/20251201_ring_vintage-amethyst-pearl-gold/input/` for future image comparison
- Test with `--headed` flag during development to see browser actions

### Common Pitfalls

- **Rate limiting**: Too fast = blocked. Use random delays 2-5 seconds.
- **Stale selectors**: Sites update frequently. Use data attributes when possible.
- **CAPTCHA**: Don't try to solve. Log and skip, flag for manual review.

### Resources

- [Playwright Python docs](https://playwright.dev/python/)
- [ShopGoodwill](https://shopgoodwill.com) - Priority marketplace
- Planning docs: `planning/ring-search-automation/`
