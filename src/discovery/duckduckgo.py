"""DuckDuckGo Search discovery provider."""

import logging
import re
from collections.abc import AsyncGenerator
from urllib.parse import quote_plus, unquote, urlparse

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.discovery.base import DiscoveryResult, SearchDiscovery

logger = logging.getLogger(__name__)


class DuckDuckGoDiscovery(SearchDiscovery):
    """Discover marketplace listings via DuckDuckGo Search.

    DuckDuckGo is preferred for:
    - No API key required
    - Better privacy (less fingerprinting)
    - More lenient rate limiting
    """

    NAME = "duckduckgo"
    BASE_URL = "https://duckduckgo.com"

    async def search(self, page: Page, query: str, site_filter: str | None = None) -> AsyncGenerator[DiscoveryResult, None]:
        """Search DuckDuckGo for marketplace listings.

        Args:
            page: Playwright page instance.
            query: Search query string.
            site_filter: Optional site restriction (e.g., "site:ebay.com").

        Yields:
            DiscoveryResult objects for each search result.
        """
        # Build search query with optional site filter
        full_query = f"{site_filter} {query}" if site_filter else query
        search_url = f"{self.BASE_URL}/?q={quote_plus(full_query)}"

        logger.info(f"DuckDuckGo search: {full_query}")

        try:
            await page.goto(search_url, wait_until="domcontentloaded")
            await self._rate_limit()

            # Wait for search results to load
            # DuckDuckGo uses JavaScript rendering
            await page.wait_for_timeout(2000)

            # Try to wait for results container
            try:
                await page.wait_for_selector("[data-testid='result'], .result, .results", timeout=10000)
            except PlaywrightTimeout:
                logger.warning("No results container found")

            # Extract results using batch JavaScript
            results = await page.evaluate(
                """
                () => {
                    const results = [];

                    // DuckDuckGo result selectors (multiple formats)
                    const selectors = [
                        '[data-testid="result"]',
                        '.result',
                        '.results .result__body',
                        'article[data-testid="result"]'
                    ];

                    let items = [];
                    for (const selector of selectors) {
                        items = document.querySelectorAll(selector);
                        if (items.length > 0) break;
                    }

                    items.forEach(item => {
                        try {
                            // Find the link
                            const linkEl = item.querySelector(
                                'a[href^="http"], a[data-testid="result-title-a"]'
                            );
                            if (!linkEl) return;

                            let href = linkEl.getAttribute('href');
                            if (!href) return;

                            // Skip DuckDuckGo internal links
                            if (href.includes('duckduckgo.com')) return;

                            // Handle DuckDuckGo redirect URLs
                            if (href.includes('//duckduckgo.com/l/')) {
                                const match = href.match(/uddg=([^&]+)/);
                                if (match) {
                                    href = decodeURIComponent(match[1]);
                                }
                            }

                            // Get title
                            const titleEl = item.querySelector(
                                'h2, [data-testid="result-title-a"], .result__title'
                            );
                            const title = titleEl
                                ? titleEl.textContent.trim()
                                : linkEl.textContent.trim();

                            // Get snippet
                            const snippetEl = item.querySelector(
                                '[data-testid="result-snippet"], .result__snippet, p'
                            );
                            const snippet = snippetEl
                                ? snippetEl.textContent.trim()
                                : '';

                            if (href && title) {
                                results.push({
                                    url: href,
                                    title: title,
                                    snippet: snippet
                                });
                            }
                        } catch (e) {
                            // Skip problematic elements
                        }
                    });

                    return results;
                }
                """
            )

            count = 0
            for result in results:
                if count >= self.max_results:
                    break

                url = result.get("url", "")
                # Clean up URL
                url = self._clean_url(url)
                if not url:
                    continue

                yield DiscoveryResult(
                    url=url,
                    title=result.get("title", ""),
                    snippet=result.get("snippet"),
                    source=self.NAME,
                    marketplace=self._detect_marketplace(url),
                )
                count += 1

        except PlaywrightTimeout:
            logger.warning(f"Timeout searching DuckDuckGo for: {query}")
        except Exception as e:
            logger.error(f"Error in DuckDuckGo search: {e}")

    def _clean_url(self, url: str) -> str:
        """Clean and validate URL.

        Args:
            url: Raw URL from search results.

        Returns:
            Cleaned URL or empty string if invalid.
        """
        try:
            # Decode URL-encoded characters
            url = unquote(url)

            # Parse and validate
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ""

            # Skip DuckDuckGo internal URLs
            if "duckduckgo.com" in parsed.netloc:
                return ""

            return url
        except Exception:
            return ""

    def _detect_marketplace(self, url: str) -> str | None:
        """Detect marketplace from URL.

        Args:
            url: URL to analyze.

        Returns:
            Marketplace name or None.
        """
        domain_patterns = {
            "ebay": r"ebay\.(com|co\.uk|de|fr)",
            "etsy": r"etsy\.com",
            "shopgoodwill": r"shopgoodwill\.com",
            "poshmark": r"poshmark\.com",
            "mercari": r"mercari\.com",
            "rubylane": r"rubylane\.com",
            "craigslist": r"craigslist\.org",
            "facebook": r"facebook\.com/marketplace",
            "offerup": r"offerup\.com",
            "depop": r"depop\.com",
        }

        for marketplace, pattern in domain_patterns.items():
            if re.search(pattern, url, re.IGNORECASE):
                return marketplace

        return None
