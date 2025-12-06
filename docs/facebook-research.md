# Facebook Marketplace Research

**Date**: 2025-12-06
**Status**: Research Complete

## Summary

Facebook Marketplace presents significant technical and legal challenges for automated scraping. The recommended approach is to use search engine discovery (Google/DuckDuckGo) to find Facebook Marketplace listings rather than direct API access or scraping.

## Authentication Requirements

### No Public API
- Facebook does not provide a public API for Marketplace
- Graph API access requires app review and is not available for scraping use cases
- Commercial access requires partnership agreements

### Login Requirements
- Most Marketplace content requires a Facebook login
- Public listings may be visible without login, but with limited data
- Login sessions require cookies and may trigger 2FA

### Anti-Automation Measures
- Rate limiting and CAPTCHA challenges
- Browser fingerprinting
- Behavioral analysis to detect bots

## Legal Considerations

### Terms of Service
- Facebook ToS prohibits automated data collection
- May result in account suspension
- Potential legal liability

### Recommendation
- **Do not scrape Facebook directly**
- Use search engine discovery instead (compliant with ToS)

## Recommended Approach

### Search Engine Discovery
Use DuckDuckGo or Google with site filters:
```python
# Search for Facebook Marketplace listings via search engines
site_filter = "site:facebook.com/marketplace"
query = f"{site_filter} amethyst ring"
```

### Benefits
- No Facebook authentication needed
- Public listings indexed by search engines
- Compliant with Facebook ToS
- Works with existing discovery infrastructure

### Limitations
- Only finds indexed/public listings
- May miss recent listings (indexing delay)
- Limited metadata from search snippets

## Implementation

### Integrated via Discovery Providers
The search discovery module already supports site filters. To search Facebook Marketplace:

```yaml
# config.yaml
discovery:
  enabled: true
  providers:
    - duckduckgo
  site_filters:
    - "site:facebook.com/marketplace"
```

### Extraction
When a Facebook Marketplace URL is discovered:
1. GenericListingExtractor attempts heuristic extraction
2. If Facebook requires login, extraction will return limited data
3. Screenshots are captured for manual review

## Future Considerations

If Facebook provides a legitimate API or partnership opportunity:
1. Implement OAuth 2.0 authentication flow
2. Handle access tokens and refresh logic
3. Map API responses to Listing model
4. Respect rate limits

## Conclusion

The search engine discovery approach is the most practical and compliant method for finding Facebook Marketplace listings. Direct Facebook integration is not recommended due to ToS restrictions and technical challenges.
