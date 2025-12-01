# Requirements: Lost Ring Search Automation

**Version:** 1.0.0
**Date:** 2024-11-30
**Item:** 20251201_ring_vintage-amethyst-pearl-gold

## Mission Statement

Automate daily searches across online marketplaces to locate a lost antique ring. Capture screenshots of promising matches, maintain a deduplicated log of all checked listings, and generate searchable records of findings.

## Background

### Ring Identification

**Product Details (Brilliant Earth, October 2015):**
- Product Name: The Giulia Ring
- Style Number: BSB96044
- Metal: 10K Yellow Gold
- Stones: Amethyst (deep purple/magenta) + Seed Pearls
- Size: 7
- Original Price: $960.00
- Era: Antique/Vintage style

**Visual Characteristics:**
- Flowing infinity/figure-8 swirl pattern in yellow gold
- 5 larger round amethyst stones (deep magenta/raspberry, NOT pale lavender)
- 8-10 small white/cream seed pearls integrated into swirl design
- Asymmetric design (not symmetrical left-to-right)
- Victorian/Edwardian aesthetic
- Face width: ~15-18mm, shank: ~2mm
- Profile height: ~5-7mm above band

**Location Lost:** Indianapolis, IN - Goodwill, approximately October 2025

## Functional Requirements

### FR-1: Marketplace Search
- **FR-1.1:** Search ShopGoodwill.com (priority - lost near Indianapolis Goodwill)
- **FR-1.2:** Search eBay.com
- **FR-1.3:** Search Etsy.com
- **FR-1.4:** Search Craigslist (Indianapolis and surrounding: Bloomington, Fort Wayne, Louisville, Cincinnati)
- **FR-1.5:** Search Ruby Lane
- **FR-1.6:** Search 1stDibs
- **FR-1.7:** Support configurable search keywords per marketplace

### FR-2: Deduplication
- **FR-2.1:** Maintain persistent log of all checked URLs
- **FR-2.2:** Skip previously checked listings automatically
- **FR-2.3:** Support URL normalization to catch duplicates with different query params

### FR-3: Relevance Scoring
- **FR-3.1:** Score listings 0-100 based on match criteria
- **FR-3.2:** Scoring factors:
  - Metal match (yellow gold = +20, 10k specifically = +10)
  - Stone type (amethyst = +25, purple stone = +15)
  - Pearl presence (seed pearls = +20, any pearl = +10)
  - Design similarity (swirl/cluster = +15, floral = +5)
  - Era/style (Victorian/Edwardian/antique = +10)
  - Size (size 7 = +10, 6-8 = +5)
- **FR-3.3:** Confidence thresholds:
  - HIGH (≥70): Screenshot + save to high_confidence folder
  - MEDIUM (40-69): Screenshot + log for review
  - LOW (<40): Log URL only, no screenshot

### FR-4: Screenshot Capture
- **FR-4.1:** Capture full-page screenshots of promising listings
- **FR-4.2:** Organize screenshots by date: `output/screenshots/YYYY-MM-DD/`
- **FR-4.3:** Naming: `{confidence}_{source}_{timestamp}.png`

### FR-5: Logging
- **FR-5.1:** Master search log in JSON format (`search_log.json`)
- **FR-5.2:** Checked links file (`checked_links.txt`) - one URL per line
- **FR-5.3:** Daily summary in Markdown (`daily_summary_YYYY-MM-DD.md`)

### FR-6: Scheduling
- **FR-6.1:** Support cron/scheduled execution
- **FR-6.2:** Default: daily at 6 AM
- **FR-6.3:** Support manual on-demand execution

## Non-Functional Requirements

### NFR-1: Rate Limiting
- 2-5 second delays between requests to avoid blocks
- Respect robots.txt where applicable

### NFR-2: Error Handling
- Continue execution on individual listing failures
- Log all errors with timestamps
- CAPTCHA detection: log and skip, flag for manual review

### NFR-3: Storage
- All outputs in `output/` directory within item folder
- Screenshots organized by date
- JSON logs append-only (no data loss)

### NFR-4: Dependencies
- Python 3.11+
- Playwright for browser automation
- Minimal external dependencies

## Output Directory Structure

```
20251201_ring_vintage-amethyst-pearl-gold/
├── input/                          # Existing reference materials
└── output/
    ├── reference/                  # Copied reference images
    ├── screenshots/
    │   └── YYYY-MM-DD/
    │       └── {confidence}_{source}_{timestamp}.png
    ├── logs/
    │   ├── search_log.json
    │   ├── checked_links.txt
    │   └── daily_summary_YYYY-MM-DD.md
    └── potential_matches/
        └── high_confidence/
```

## Search Keywords

**Primary:**
- `amethyst pearl ring gold vintage`
- `antique amethyst seed pearl ring`
- `Victorian amethyst pearl ring`
- `10k gold amethyst pearl ring`
- `Giulia ring Brilliant Earth`
- `BSB96044`

**Secondary:**
- `purple stone pearl gold ring antique`
- `magenta gemstone pearl ring`
- `swirl design amethyst ring`

## Success Criteria

A listing is a STRONG MATCH (escalate immediately) if it has 5+ of:
- [ ] Yellow gold (10k preferred, 9k/14k acceptable)
- [ ] Deep purple/magenta amethyst stones (not pale)
- [ ] Multiple seed pearls integrated in design
- [ ] Swirl or infinity-like pattern
- [ ] Victorian/Edwardian aesthetic
- [ ] Size 7 (or resizable)

## Known Leads (Check First)

1. Etsy UK: `https://www.etsy.com/uk/listing/1895838715/`
2. Pittsburgh Craigslist: `https://pittsburgh.craigslist.org/jwl/d/new-fancy-10k-gold-amethyst-ring/7893523856.html`
3. eBay: `https://www.ebay.com/itm/397177063712`
4. ShopGoodwill rings: `https://shopgoodwill.com/categories/rings`
