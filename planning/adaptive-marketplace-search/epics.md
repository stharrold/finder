# Epics: Adaptive Marketplace Search

**Issue**: #6
**Slug**: adaptive-marketplace-search

## Epic Overview

| Epic | Description | Priority | Effort |
|------|-------------|----------|--------|
| E1 | Fix Poshmark Adapter | P0 (Critical) | Small |
| E2 | Search Discovery | P1 (High) | Medium |
| E3 | Adaptive Extractor | P1 (High) | Medium |
| E4 | Facebook Marketplace | P2 (Medium) | Medium |
| E5 | Integration & Testing | P1 (High) | Small |

---

## E1: Fix Poshmark Adapter

**Priority**: P0 - Critical (blocking daily searches)

### Tasks

- [ ] **E1.1**: Diagnose DOM context error root cause
  - Review `src/adapters/poshmark.py`
  - Identify stale element handle patterns

- [ ] **E1.2**: Refactor to use page.evaluate() for batch extraction
  - Extract all listing data in single JS call
  - Avoid element handle iteration

- [ ] **E1.3**: Add retry logic for transient failures
  - Implement exponential backoff
  - Log retry attempts

- [ ] **E1.4**: Add integration test
  - Test against live Poshmark
  - Verify no DOM errors

### Acceptance Criteria
- Zero `ElementHandle.query_selector: Protocol error` logs
- All Poshmark listings extracted successfully

---

## E2: Search Discovery

**Priority**: P1 - High

### Tasks

- [ ] **E2.1**: Create SearchDiscovery base class
  - Define interface for search providers
  - Implement result aggregation

- [ ] **E2.2**: Implement Google Search provider
  - Use Custom Search API or scraping
  - Handle rate limiting
  - Parse search results

- [ ] **E2.3**: Implement DuckDuckGo provider
  - Use HTML search (no API key needed)
  - Parse results

- [ ] **E2.4**: Add marketplace URL filtering
  - Detect marketplace domains from URLs
  - Prioritize known marketplace patterns

- [ ] **E2.5**: Update config.yaml schema
  - Add discovery provider settings
  - Maintain backwards compatibility

### Acceptance Criteria
- Can query Google and DuckDuckGo for ring keywords
- Returns deduplicated list of marketplace URLs
- Respects rate limits

---

## E3: Adaptive Extractor

**Priority**: P1 - High

### Tasks

- [ ] **E3.1**: Implement StructuredDataExtractor
  - Parse JSON-LD Product schema
  - Parse OpenGraph meta tags
  - Parse Schema.org microdata

- [ ] **E3.2**: Implement GenericListingExtractor
  - Heuristic title detection (h1, largest text)
  - Heuristic price detection (currency patterns)
  - Image extraction

- [ ] **E3.3**: Create LegacyAdapterBridge
  - Map domains to existing adapters
  - Fallback when structured data unavailable

- [ ] **E3.4**: Integrate with RelevanceScorer
  - Ensure extracted data format matches scorer input
  - Handle missing fields gracefully

### Acceptance Criteria
- Can extract listing details from any marketplace URL
- Structured data preferred when available
- Legacy adapters used as fallback

---

## E4: Facebook Marketplace Integration

**Priority**: P2 - Medium

### Tasks

- [ ] **E4.1**: Research Facebook Marketplace access
  - Document authentication requirements
  - Evaluate API vs scraping options

- [ ] **E4.2**: Implement Facebook search via discovery
  - Add `site:facebook.com/marketplace` queries
  - Parse marketplace listing URLs

- [ ] **E4.3**: Handle Facebook authentication
  - Cookie-based session (if needed)
  - Login flow support

- [ ] **E4.4**: Extract Facebook listing details
  - Adapt extractor for Facebook's HTML
  - Handle lazy-loaded content

### Acceptance Criteria
- Can discover Facebook Marketplace listings via search
- Can extract listing details from Facebook URLs
- Handles authentication gracefully

---

## E5: Integration & Testing

**Priority**: P1 - High

### Tasks

- [ ] **E5.1**: Update SearchOrchestrator
  - Integrate SearchDiscovery
  - Integrate AdaptiveExtractor
  - Maintain backwards compatibility flag

- [ ] **E5.2**: Update CLI and config
  - Add `--adaptive` flag
  - Update config.yaml documentation

- [ ] **E5.3**: End-to-end testing
  - Test full search flow
  - Verify deduplication works
  - Check scoring accuracy

- [ ] **E5.4**: Update LaunchAgent
  - Verify scheduled runs work
  - Test failure recovery

- [ ] **E5.5**: Documentation
  - Update CLAUDE.md
  - Add usage examples

### Acceptance Criteria
- Daily search runs successfully with adaptive mode
- Results include listings from discovered marketplaces
- No regression in existing functionality
