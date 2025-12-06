# Implementation Plan: Bike Search

**Type:** feature
**Slug:** bike-search
**Date:** 2025-12-06

## Overview

Extend the existing ring-search automation to support searching for a Trek Allant+ 7S electric bike. The implementation reuses the existing adapter pattern, scoring infrastructure, dedup manager, and report generation while adding bike-specific adapters and scoring logic.

**Target Bike:**
- Model: Trek Allant+ 7S (Class 3, 28 mph) - NOT Allant+ 7 (Class 1, 20 mph)
- Battery: 625Wh (not 500Wh) with range extender
- Frame: Large (L)
- Location: Within 300mi of Indianapolis

## Task Breakdown

### Phase 1: Configuration & Models

#### Task T001: Create Bike Configuration

**Priority:** High

**Files:**
- `bike_config.yaml` (new)
- `src/models.py` (extend)

**Description:**
Create bike-specific configuration file with search terms, scoring weights, and marketplace settings for Trek Allant+ 7S.

**Steps:**
1. Create `bike_config.yaml` with target bike details
2. Define bike-specific scoring weights (model: 40%, class: 20%, battery: 20%, range extender: 15%, frame: 5%)
3. Configure marketplaces: eBay, Craigslist (24 regions), Pinkbike, Trek Red Barn Refresh
4. Configure adaptive discovery for Facebook Marketplace, OfferUp, Mercari
5. Add BikeScoringWeights to models.py

**Acceptance Criteria:**
- [ ] bike_config.yaml validates successfully
- [ ] BikeScoringWeights dataclass exists with correct defaults
- [ ] Search terms target Trek Allant+ 7S specifically

**Verification:**
```bash
uv run python -c "import yaml; yaml.safe_load(open('bike_config.yaml'))"
uv run python -c "from src.models import BikeScoringWeights; print(BikeScoringWeights())"
```

**Dependencies:**
- None

---

#### Task T002: Create Bike Scoring Engine

**Priority:** High

**Files:**
- `src/bike_scoring.py` (new)
- `tests/test_bike_scoring.py` (new)

**Description:**
Implement BikeRelevanceScorer class that scores listings based on Trek Allant+ 7S specifications.

**Steps:**
1. Create BikeRelevanceScorer class following RelevanceScorer pattern
2. Implement model validation (Allant+ 7S vs 7)
3. Implement class validation (Class 3 @ 28mph vs Class 1 @ 20mph)
4. Implement battery validation (625Wh requirement)
5. Implement range extender detection
6. Implement frame size detection (Large/L)
7. Write comprehensive unit tests

**Scoring Weights (from requirements):**
- Model match (Allant+ 7S): 40 points
- Class 3 confirmation: 20 points
- 625Wh battery: 20 points
- Range extender present: 15 points
- Large frame: 5 points

**Negative Scoring:**
- Class 1 model: -50 points (hard rejection)
- 500Wh battery: -20 points

**Acceptance Criteria:**
- [ ] BikeRelevanceScorer correctly identifies Allant+ 7S vs 7
- [ ] Class 3 (28 mph) properly differentiated from Class 1 (20 mph)
- [ ] Battery capacity correctly detected (625Wh vs 500Wh)
- [ ] Range extender mentioned earns bonus
- [ ] Frame size L/Large detected
- [ ] Test coverage ≥90%

**Verification:**
```bash
uv run pytest tests/test_bike_scoring.py -v --cov=src.bike_scoring
```

**Dependencies:**
- T001

---

### Phase 2: Marketplace Adapters

#### Task T003: Create Pinkbike Adapter

**Priority:** High

**Files:**
- `src/adapters/pinkbike.py` (new)
- `tests/test_adapters/test_pinkbike.py` (new)
- `src/adapters/__init__.py` (update)

**Description:**
Implement Pinkbike marketplace adapter following the base adapter pattern.

**Steps:**
1. Research Pinkbike buy/sell section URL structure
2. Create PinkbikeAdapter subclassing MarketplaceAdapter
3. Implement search() method with location filtering
4. Implement get_listing_details() for full listing data
5. Handle pagination
6. Register in ADAPTER_MAP
7. Write unit tests with mock responses

**Acceptance Criteria:**
- [ ] PinkbikeAdapter registered in ADAPTER_MAP
- [ ] search() returns list of Listing objects
- [ ] Location filtering works (300mi from Indianapolis)
- [ ] get_listing_details() extracts title, price, description, images
- [ ] Rate limiting respected

**Verification:**
```bash
uv run python -c "from src.adapters import ADAPTER_MAP; print('pinkbike' in ADAPTER_MAP)"
uv run pytest tests/test_adapters/test_pinkbike.py -v
```

**Dependencies:**
- T001

---

#### Task T004: Create Trek Red Barn Refresh Adapter

**Priority:** High

**Files:**
- `src/adapters/trek_redbarn.py` (new)
- `tests/test_adapters/test_trek_redbarn.py` (new)
- `src/adapters/__init__.py` (update)

**Description:**
Implement Trek Red Barn Refresh (certified pre-owned) adapter.

**Steps:**
1. Research Trek Red Barn Refresh website structure
2. Create TrekRedBarnAdapter subclassing MarketplaceAdapter
3. Implement search() for e-bike category with "Allant" filter
4. Implement get_listing_details() with bike specifications
5. Extract battery, class, and frame information from specs
6. Register in ADAPTER_MAP
7. Write unit tests

**Acceptance Criteria:**
- [ ] TrekRedBarnAdapter registered in ADAPTER_MAP
- [ ] Searches within e-bike/Allant category
- [ ] Extracts bike specifications (battery, class, frame)
- [ ] Handles location/shipping availability

**Verification:**
```bash
uv run python -c "from src.adapters import ADAPTER_MAP; print('trek_redbarn' in ADAPTER_MAP)"
uv run pytest tests/test_adapters/test_trek_redbarn.py -v
```

**Dependencies:**
- T001

---

### Phase 3: CLI Integration

#### Task T005: Update CLI for Bike Search Profile

**Priority:** High

**Files:**
- `src/cli.py` (update)
- `src/bike_search.py` (new)

**Description:**
Update CLI to support bike search profile using bike_config.yaml and BikeRelevanceScorer.

**Steps:**
1. Create BikeSearchOrchestrator in bike_search.py (extends SearchOrchestrator pattern)
2. Add --profile option to CLI (ring|bike, default: ring)
3. Profile determines: config file, scorer, adapters
4. Update help text with bike search examples
5. Ensure backward compatibility (ring search unchanged)

**Acceptance Criteria:**
- [ ] `uv run ring-search -c bike_config.yaml run` works
- [ ] BikeSearchOrchestrator uses BikeRelevanceScorer
- [ ] Existing ring search behavior unchanged
- [ ] CLI help shows bike search usage

**Verification:**
```bash
uv run ring-search --help
uv run ring-search -c bike_config.yaml run --dry-run
```

**Dependencies:**
- T002, T003, T004

---

### Phase 4: Testing & Quality

#### Task T006: Integration Tests

**Priority:** High

**Files:**
- `tests/test_bike_integration.py` (new)

**Description:**
End-to-end integration tests for bike search workflow.

**Steps:**
1. Create fixtures for mock bike listings
2. Test full search flow with BikeSearchOrchestrator
3. Test scoring of various bike listings
4. Test report generation with bike results
5. Test dedup behavior

**Acceptance Criteria:**
- [ ] Integration test covers full search flow
- [ ] Mock adapters return realistic bike data
- [ ] Scoring correctly ranks listings
- [ ] Report includes all expected fields

**Verification:**
```bash
uv run pytest tests/test_bike_integration.py -v
```

**Dependencies:**
- T005

---

#### Task T007: Quality Gates

**Priority:** High

**Files:**
- All new files

**Description:**
Ensure code quality standards are met.

**Steps:**
1. Run ruff linting and fix issues
2. Run mypy type checking and fix issues
3. Verify test coverage ≥80%
4. Update docstrings where needed

**Acceptance Criteria:**
- [ ] `uv run ruff check src/` passes
- [ ] `uv run mypy src/` passes
- [ ] Test coverage ≥80% for new code
- [ ] No type errors

**Verification:**
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest --cov=src --cov-fail-under=80
```

**Dependencies:**
- T006

---

### Phase 5: Documentation

#### Task T008: Update Documentation

**Priority:** Medium

**Files:**
- `CLAUDE.md` (update)
- `README.md` (update if exists)

**Description:**
Update documentation to reflect bike search capability.

**Steps:**
1. Add bike search examples to CLAUDE.md Development Commands
2. Document bike_config.yaml structure
3. Add bike scoring weights explanation
4. Update architecture diagram if needed

**Acceptance Criteria:**
- [ ] CLAUDE.md includes bike search commands
- [ ] Configuration options documented
- [ ] Scoring logic explained

**Verification:**
```bash
# Manual review of documentation
cat CLAUDE.md | grep -A5 "bike"
```

**Dependencies:**
- T007

---

## Task Dependencies Graph

```
T001 (Config/Models)
  │
  ├─> T002 (Bike Scoring) ─┐
  │                         │
  ├─> T003 (Pinkbike) ─────┼─> T005 (CLI) ─> T006 (Integration) ─> T007 (Quality) ─> T008 (Docs)
  │                         │
  └─> T004 (Trek RedBarn) ─┘
```

## Parallel Work Opportunities

- T002, T003, T004 can be done in parallel after T001
- Tests can be written alongside each implementation task

## Critical Path

1. T001 → T002 → T005 → T006 → T007 → T008

## Quality Checklist

Before considering this feature complete:

- [ ] All 8 tasks marked complete
- [ ] Test coverage ≥ 80% for new code
- [ ] All tests passing
- [ ] Linting clean (`uv run ruff check src/ tests/`)
- [ ] Type checking clean (`uv run mypy src/`)
- [ ] bike_config.yaml validated
- [ ] Documentation updated
- [ ] Manual test: `uv run ring-search -c bike_config.yaml run --dry-run`

## Risk Assessment

### High Risk Tasks

- **T003/T004 (Adapters)**: Website structure may change or require authentication
  - Mitigation: Use adaptive discovery as fallback

### Medium Risk Tasks

- **T002 (Scoring)**: Model/class distinction may be ambiguous in listings
  - Mitigation: Conservative scoring, flag uncertain matches for manual review

## Notes

### Implementation Tips

- Reuse existing patterns from ring-search adapters
- BikeRelevanceScorer should follow same interface as RelevanceScorer
- Test with real listing data where possible

### Key Model Numbers

- Trek Allant+ 7S (Class 3): Target model
- Trek Allant+ 7 (Class 1): REJECT - wrong class
- 625Wh battery: Required
- 500Wh battery: Insufficient
- Range Extender (second battery): Bonus

### Resources

- [Trek Allant+ 7S Product Page](https://www.trekbikes.com/us/en_US/bikes/hybrid-bikes/electric-hybrid-bikes/allant/allant-7s/p/35026/)
- [Pinkbike Buy/Sell](https://www.pinkbike.com/buysell/)
- [Trek Red Barn Refresh](https://www.trekbikes.com/us/en_US/certified-preowned/)
