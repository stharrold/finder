"""Marketplace URL filtering for search discovery."""

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from src.discovery.base import DiscoveryResult

logger = logging.getLogger(__name__)


@dataclass
class MarketplaceConfig:
    """Configuration for a known marketplace."""

    name: str
    domain_patterns: list[str]
    listing_patterns: list[str] = field(default_factory=list)
    priority: int = 1  # Higher = more relevant


# Default marketplace configurations
DEFAULT_MARKETPLACES = [
    MarketplaceConfig(
        name="ebay",
        domain_patterns=[r"ebay\.(com|co\.uk|de|fr|ca|au)"],
        listing_patterns=[r"/itm/", r"/p/"],
        priority=2,
    ),
    MarketplaceConfig(
        name="etsy",
        domain_patterns=[r"etsy\.com"],
        listing_patterns=[r"/listing/"],
        priority=2,
    ),
    MarketplaceConfig(
        name="shopgoodwill",
        domain_patterns=[r"shopgoodwill\.com"],
        listing_patterns=[r"/item/"],
        priority=2,
    ),
    MarketplaceConfig(
        name="poshmark",
        domain_patterns=[r"poshmark\.com"],
        listing_patterns=[r"/listing/"],
        priority=2,
    ),
    MarketplaceConfig(
        name="mercari",
        domain_patterns=[r"mercari\.com"],
        listing_patterns=[r"/item/", r"/product/"],
        priority=2,
    ),
    MarketplaceConfig(
        name="rubylane",
        domain_patterns=[r"rubylane\.com"],
        listing_patterns=[r"/item/"],
        priority=2,
    ),
    MarketplaceConfig(
        name="craigslist",
        domain_patterns=[r"craigslist\.org"],
        listing_patterns=[r"\.html$"],
        priority=1,
    ),
    MarketplaceConfig(
        name="facebook",
        domain_patterns=[r"facebook\.com/marketplace"],
        listing_patterns=[r"/item/"],
        priority=2,
    ),
    MarketplaceConfig(
        name="offerup",
        domain_patterns=[r"offerup\.com"],
        listing_patterns=[r"/item/"],
        priority=1,
    ),
    MarketplaceConfig(
        name="depop",
        domain_patterns=[r"depop\.com"],
        listing_patterns=[r"/products/"],
        priority=1,
    ),
    MarketplaceConfig(
        name="1stdibs",
        domain_patterns=[r"1stdibs\.com"],
        listing_patterns=[r"/jewelry/", r"/id-"],
        priority=2,
    ),
    MarketplaceConfig(
        name="chairish",
        domain_patterns=[r"chairish\.com"],
        listing_patterns=[r"/product/"],
        priority=1,
    ),
    MarketplaceConfig(
        name="liveauctioneers",
        domain_patterns=[r"liveauctioneers\.com"],
        listing_patterns=[r"/item/"],
        priority=2,
    ),
]


class MarketplaceFilter:
    """Filters and prioritizes marketplace URLs from discovery results."""

    def __init__(
        self,
        marketplaces: list[MarketplaceConfig] | None = None,
        include_unknown: bool = False,
    ):
        """Initialize filter with marketplace configurations.

        Args:
            marketplaces: List of marketplace configs. Defaults to built-in list.
            include_unknown: Whether to include URLs from unknown domains.
        """
        self.marketplaces = marketplaces or DEFAULT_MARKETPLACES
        self.include_unknown = include_unknown

        # Compile regex patterns for efficiency
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        for mp in self.marketplaces:
            self._compiled_patterns[mp.name] = [re.compile(pattern, re.IGNORECASE) for pattern in mp.domain_patterns]

    def detect_marketplace(self, url: str) -> str | None:
        """Detect which marketplace a URL belongs to.

        Args:
            url: URL to analyze.

        Returns:
            Marketplace name or None if unknown.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            for mp in self.marketplaces:
                for pattern in self._compiled_patterns[mp.name]:
                    if pattern.search(domain) or pattern.search(url):
                        return mp.name

            return None
        except Exception:
            return None

    def is_listing_url(self, url: str, marketplace: str) -> bool:
        """Check if URL appears to be a product listing.

        Args:
            url: URL to check.
            marketplace: Marketplace name.

        Returns:
            True if URL matches listing patterns.
        """
        mp_config = next((mp for mp in self.marketplaces if mp.name == marketplace), None)
        if not mp_config or not mp_config.listing_patterns:
            return True  # If no patterns defined, assume it's a listing

        for pattern in mp_config.listing_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        return False

    def get_priority(self, marketplace: str) -> int:
        """Get priority score for a marketplace.

        Args:
            marketplace: Marketplace name.

        Returns:
            Priority score (higher = more relevant).
        """
        mp_config = next((mp for mp in self.marketplaces if mp.name == marketplace), None)
        return mp_config.priority if mp_config else 0

    def filter_results(
        self,
        results: list[DiscoveryResult],
        listings_only: bool = True,
    ) -> list[DiscoveryResult]:
        """Filter and prioritize discovery results.

        Args:
            results: List of discovery results to filter.
            listings_only: Only include URLs that look like product listings.

        Returns:
            Filtered and sorted list of results.
        """
        filtered = []

        for result in results:
            marketplace = result.marketplace or self.detect_marketplace(result.url)

            if marketplace:
                # Check if it's a listing URL
                if listings_only and not self.is_listing_url(result.url, marketplace):
                    logger.debug(f"Skipping non-listing URL: {result.url}")
                    continue

                # Update result with detected marketplace
                result.marketplace = marketplace
                filtered.append(result)

            elif self.include_unknown:
                # Include unknown domains if configured
                filtered.append(result)

        # Sort by marketplace priority (higher first)
        filtered.sort(
            key=lambda r: self.get_priority(r.marketplace or ""),
            reverse=True,
        )

        return filtered

    def get_site_filters(self, marketplaces: list[str] | None = None) -> list[str]:
        """Generate site filter strings for search queries.

        Args:
            marketplaces: List of marketplace names to include.
                         If None, includes all configured marketplaces.

        Returns:
            List of site filter strings (e.g., ["site:ebay.com", "site:etsy.com"]).
        """
        filters = []

        target_mps = marketplaces or [mp.name for mp in self.marketplaces]

        for mp in self.marketplaces:
            if mp.name in target_mps:
                for pattern in mp.domain_patterns:
                    domains = self._expand_domain_pattern(pattern)
                    for domain in domains:
                        filters.append(f"site:{domain}")

        return filters

    def _expand_domain_pattern(self, pattern: str) -> list[str]:
        """Expand a regex domain pattern into all possible domain strings.

        Args:
            pattern: Regex pattern like r"ebay\\.(com|co\\.uk|de|fr)"

        Returns:
            List of expanded domains like ["ebay.com", "ebay.co.uk", "ebay.de", "ebay.fr"]
        """
        # Match base domain and alternation group: ebay\.(com|co\.uk|de|fr)
        m = re.match(r"^([a-z0-9]+)\\\.\(([^)]+)\)$", pattern, re.IGNORECASE)
        if m:
            base = m.group(1)
            alts = m.group(2).split("|")
            domains = []
            for alt in alts:
                # Replace escaped dots with real dots
                domain = base + "." + alt.replace("\\.", ".")
                domains.append(domain)
            return domains

        # Fallback: try to remove regex escapes and return as-is
        domain = re.sub(r"\\\\", "", pattern)  # Remove double escapes
        domain = re.sub(r"\\.", ".", domain)  # Replace \. with .
        domain = re.sub(r"[^a-z0-9.]", "", domain)  # Remove remaining special chars
        return [domain] if domain else []
