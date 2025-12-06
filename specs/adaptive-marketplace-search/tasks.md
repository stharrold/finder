# Tasks: Adaptive Marketplace Search

**Issue**: #6
**Slug**: adaptive-marketplace-search
**Generated**: 2025-12-06
**Source**: planning/adaptive-marketplace-search/epics.md

## Task Summary

| Category | Count | Priority |
|----------|-------|----------|
| E1: Fix Poshmark | 4 | P0 (Critical) |
| E2: Search Discovery | 5 | P1 (High) |
| E3: Adaptive Extractor | 4 | P1 (High) |
| E4: Facebook Marketplace | 4 | P2 (Medium) |
| E5: Integration & Testing | 5 | P1 (High) |
| **Total** | **22** | |

## Execution Order

Tasks should be executed in epic order (E1 → E2 → E3 → E4 → E5).

**Parallel Opportunities**:
- E2.2 and E2.3 can run in parallel (Google + DuckDuckGo providers)
- E3.1 and E3.2 can run in parallel (StructuredData + Generic extractors)
- E4.1 is research-only (can run in parallel with E3)

---

## E1: Fix Poshmark Adapter [P0 - Critical]

### T001: Diagnose DOM context error root cause
- **ID**: E1.1
- **Files**: `src/adapters/poshmark.py`
- **Steps**:
  1. Review `src/adapters/poshmark.py`
  2. Identify stale element handle patterns
  3. Document root cause
- **Acceptance**: Root cause documented
- **Dependencies**: None

### T002: Refactor to use page.evaluate() for batch extraction
- **ID**: E1.2
- **Files**: `src/adapters/poshmark.py`
- **Steps**:
  1. Extract all listing data in single JS call
  2. Avoid element handle iteration
  3. Test extraction
- **Acceptance**: No element handle iteration in extraction code
- **Dependencies**: T001

### T003: Add retry logic for transient failures
- **ID**: E1.3
- **Files**: `src/adapters/poshmark.py`
- **Steps**:
  1. Implement exponential backoff
  2. Log retry attempts
  3. Test retry behavior
- **Acceptance**: Retry logic with logging in place
- **Dependencies**: T002

### T004: Add Poshmark integration test
- **ID**: E1.4
- **Files**: `tests/test_poshmark.py`
- **Steps**:
  1. Test against live Poshmark
  2. Verify no DOM errors
  3. Validate extraction results
- **Acceptance**: Zero `ElementHandle.query_selector: Protocol error` logs
- **Dependencies**: T003

---

## E2: Search Discovery [P1 - High]

### T005: Create SearchDiscovery base class
- **ID**: E2.1
- **Files**: `src/discovery/base.py`
- **Steps**:
  1. Define interface for search providers
  2. Implement result aggregation
  3. Add typing and docstrings
- **Acceptance**: Base class with abstract methods defined
- **Dependencies**: None

### T006: Implement Google Search provider [P]
- **ID**: E2.2
- **Files**: `src/discovery/google.py`
- **Steps**:
  1. Use Custom Search API or scraping
  2. Handle rate limiting
  3. Parse search results
- **Acceptance**: Can query Google and return marketplace URLs
- **Dependencies**: T005
- **Parallel**: Can run with T007

### T007: Implement DuckDuckGo provider [P]
- **ID**: E2.3
- **Files**: `src/discovery/duckduckgo.py`
- **Steps**:
  1. Use HTML search (no API key needed)
  2. Parse results
  3. Handle errors gracefully
- **Acceptance**: Can query DuckDuckGo and return marketplace URLs
- **Dependencies**: T005
- **Parallel**: Can run with T006

### T008: Add marketplace URL filtering
- **ID**: E2.4
- **Files**: `src/discovery/filters.py`
- **Steps**:
  1. Detect marketplace domains from URLs
  2. Prioritize known marketplace patterns
  3. Add configurable domain list
- **Acceptance**: Filters results to marketplace URLs only
- **Dependencies**: T006, T007

### T009: Update config.yaml schema for discovery
- **ID**: E2.5
- **Files**: `config.yaml`, `src/config.py`
- **Steps**:
  1. Add discovery provider settings
  2. Maintain backwards compatibility
  3. Document new options
- **Acceptance**: Config supports discovery settings without breaking existing configs
- **Dependencies**: T008

---

## E3: Adaptive Extractor [P1 - High]

### T010: Implement StructuredDataExtractor [P]
- **ID**: E3.1
- **Files**: `src/extractors/structured.py`
- **Steps**:
  1. Parse JSON-LD Product schema
  2. Parse OpenGraph meta tags
  3. Parse Schema.org microdata
- **Acceptance**: Extracts product data from JSON-LD, OG, and microdata
- **Dependencies**: None
- **Parallel**: Can run with T011

### T011: Implement GenericListingExtractor [P]
- **ID**: E3.2
- **Files**: `src/extractors/generic.py`
- **Steps**:
  1. Heuristic title detection (h1, largest text)
  2. Heuristic price detection (currency patterns)
  3. Image extraction
- **Acceptance**: Extracts title, price, images from unknown pages
- **Dependencies**: None
- **Parallel**: Can run with T010

### T012: Create LegacyAdapterBridge
- **ID**: E3.3
- **Files**: `src/extractors/bridge.py`
- **Steps**:
  1. Map domains to existing adapters
  2. Fallback when structured data unavailable
  3. Unify output format
- **Acceptance**: Routes known domains to legacy adapters
- **Dependencies**: T010, T011

### T013: Integrate with RelevanceScorer
- **ID**: E3.4
- **Files**: `src/extractors/base.py`, `src/scoring.py`
- **Steps**:
  1. Ensure extracted data format matches scorer input
  2. Handle missing fields gracefully
  3. Test scoring with extracted data
- **Acceptance**: Extracted listings score correctly
- **Dependencies**: T012

---

## E4: Facebook Marketplace Integration [P2 - Medium]

### T014: Research Facebook Marketplace access [P]
- **ID**: E4.1
- **Files**: `docs/facebook-research.md`
- **Steps**:
  1. Document authentication requirements
  2. Evaluate API vs scraping options
  3. Identify legal/ToS considerations
- **Acceptance**: Research document with recommendations
- **Dependencies**: None
- **Parallel**: Can run during E3

### T015: Implement Facebook search via discovery
- **ID**: E4.2
- **Files**: `src/discovery/google.py`, `src/discovery/duckduckgo.py`
- **Steps**:
  1. Add `site:facebook.com/marketplace` queries
  2. Parse marketplace listing URLs
  3. Test discovery
- **Acceptance**: Discovers Facebook Marketplace listings via search
- **Dependencies**: T014, T009

### T016: Handle Facebook authentication
- **ID**: E4.3
- **Files**: `src/adapters/facebook.py`
- **Steps**:
  1. Cookie-based session (if needed)
  2. Login flow support
  3. Session persistence
- **Acceptance**: Can access Facebook pages requiring auth
- **Dependencies**: T015

### T017: Extract Facebook listing details
- **ID**: E4.4
- **Files**: `src/adapters/facebook.py`
- **Steps**:
  1. Adapt extractor for Facebook's HTML
  2. Handle lazy-loaded content
  3. Test extraction
- **Acceptance**: Extracts listing details from Facebook URLs
- **Dependencies**: T016

---

## E5: Integration & Testing [P1 - High]

### T018: Update SearchOrchestrator
- **ID**: E5.1
- **Files**: `src/ring_search.py`
- **Steps**:
  1. Integrate SearchDiscovery
  2. Integrate AdaptiveExtractor
  3. Maintain backwards compatibility flag
- **Acceptance**: Orchestrator supports adaptive mode
- **Dependencies**: T013, T017

### T019: Update CLI and config
- **ID**: E5.2
- **Files**: `src/cli.py`, `config.yaml`
- **Steps**:
  1. Add `--adaptive` flag
  2. Update config.yaml documentation
  3. Add usage examples
- **Acceptance**: CLI supports `--adaptive` flag
- **Dependencies**: T018

### T020: End-to-end testing
- **ID**: E5.3
- **Files**: `tests/test_e2e.py`
- **Steps**:
  1. Test full search flow
  2. Verify deduplication works
  3. Check scoring accuracy
- **Acceptance**: E2E tests pass with adaptive mode
- **Dependencies**: T019

### T021: Update LaunchAgent
- **ID**: E5.4
- **Files**: `com.stharrold.ring-search.plist`
- **Steps**:
  1. Verify scheduled runs work
  2. Test failure recovery
  3. Update configuration
- **Acceptance**: Scheduled runs work with adaptive mode
- **Dependencies**: T020

### T022: Documentation
- **ID**: E5.5
- **Files**: `CLAUDE.md`, `README.md`
- **Steps**:
  1. Update CLAUDE.md with adaptive mode
  2. Add usage examples
  3. Document new configuration options
- **Acceptance**: Documentation complete
- **Dependencies**: T021

---

## Dependencies Graph

```
T001 → T002 → T003 → T004
                          \
T005 → T006 ─┐              \
       T007 ─┼→ T008 → T009 ─┐
                              \
T010 ─┐                        \
T011 ─┼→ T012 → T013 ───────────┼→ T018 → T019 → T020 → T021 → T022
                                /
T014 → T015 → T016 → T017 ─────┘
```

## Verification Commands

```bash
# After E1 (Poshmark fix)
uv run pytest tests/test_poshmark.py -v

# After E2 (Search Discovery)
uv run pytest tests/test_discovery.py -v

# After E3 (Adaptive Extractor)
uv run pytest tests/test_extractors.py -v

# After E5 (Integration)
uv run ring-search -c config.yaml run --adaptive --headed
uv run pytest --cov=src --cov-report=term
```
