# Requirements: Adaptive Marketplace Search

**Issue**: #6
**Slug**: adaptive-marketplace-search
**Created**: 2025-12-06

## Problem Statement

The current ring search system uses a fixed list of marketplace adapters, which:
1. Limits discovery to pre-configured sites only
2. Misses potential matches on unlisted marketplaces (e.g., Facebook Marketplace)
3. Has reliability issues (Poshmark adapter DOM errors, 6 marketplaces returning no results)
4. Requires code changes to add new marketplaces

## Goals

1. **Fix immediate issues**: Resolve Poshmark adapter DOM context errors
2. **Implement adaptive search**: Use general search engines to discover marketplace listings dynamically
3. **Expand coverage**: Support Facebook Marketplace and any marketplace discovered through search
4. **Improve reliability**: Handle site changes gracefully without requiring adapter updates

## User Stories

### US-1: Adaptive Search Discovery
As a user searching for a lost ring, I want the system to discover relevant listings from any marketplace via general search, so that I don't miss potential matches on sites I didn't know to search.

**Acceptance Criteria**:
- System queries search engines (Google, DuckDuckGo) with ring keywords
- Extracts marketplace URLs from search results
- Prioritizes results by relevance score
- Deduplicates across sources

### US-2: Dynamic Marketplace Support
As a user, I want the system to handle any marketplace URL without pre-built adapters, so that new sites are automatically supported.

**Acceptance Criteria**:
- Generic scraper extracts listing details from any page
- Falls back to structured data (JSON-LD, OpenGraph) when available
- Captures screenshots of all potential matches
- Scores listings using existing relevance algorithm

### US-3: Facebook Marketplace Integration
As a user, I want to search Facebook Marketplace, so that I can find rings listed locally.

**Acceptance Criteria**:
- Discovers Facebook Marketplace listings via search
- Extracts listing details (title, price, location, images)
- Handles Facebook's authentication requirements
- Respects rate limits

### US-4: Fixed Adapter Reliability
As a user, I want the existing Poshmark adapter to work without errors, so that I get complete results.

**Acceptance Criteria**:
- No DOM context errors during extraction
- Graceful handling of stale elements
- Retry logic for transient failures

## Non-Functional Requirements

- **Performance**: Complete search in under 10 minutes
- **Reliability**: Handle site changes without crashing
- **Rate Limiting**: Respect robots.txt and implement polite delays
- **Logging**: Track which sources provided results

## Out of Scope

- User authentication management (beyond what's needed for Facebook)
- Mobile app marketplace support
- Real-time notifications
