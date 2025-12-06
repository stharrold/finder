"""Tests for search discovery module."""

from unittest.mock import AsyncMock

import pytest

from src.discovery.base import AggregatedDiscovery, DiscoveryResult, SearchDiscovery
from src.discovery.duckduckgo import DuckDuckGoDiscovery
from src.discovery.filters import MarketplaceFilter
from src.discovery.google import GoogleDiscovery


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_basic_result(self) -> None:
        """Test creating a basic discovery result."""
        result = DiscoveryResult(
            url="https://ebay.com/itm/12345",
            title="Vintage Ring",
            snippet="Beautiful amethyst ring",
            source="google",
            marketplace="ebay",
        )
        assert result.url == "https://ebay.com/itm/12345"
        assert result.marketplace == "ebay"

    def test_optional_fields(self) -> None:
        """Test that optional fields have defaults."""
        result = DiscoveryResult(url="https://example.com", title="Test")
        assert result.snippet is None
        assert result.source == ""
        assert result.marketplace is None


class TestGoogleDiscovery:
    """Tests for GoogleDiscovery class."""

    def test_name(self) -> None:
        """Test that NAME is correct."""
        discovery = GoogleDiscovery()
        assert discovery.NAME == "google"

    @pytest.mark.asyncio
    async def test_search_uses_batch_js(self) -> None:
        """Test that search uses page.evaluate for extraction."""
        discovery = GoogleDiscovery(rate_limit_delay=0.01, max_results=10)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        mock_page.evaluate = AsyncMock(
            return_value=[
                {
                    "url": "https://ebay.com/itm/12345",
                    "title": "Vintage Ring",
                    "snippet": "Beautiful amethyst ring",
                },
                {
                    "url": "https://etsy.com/listing/67890",
                    "title": "Antique Pearl Ring",
                    "snippet": "Gold with pearls",
                },
            ]
        )

        results = []
        async for result in discovery.search(mock_page, "amethyst ring"):
            results.append(result)

        assert len(results) == 2
        assert results[0].source == "google"
        assert results[0].marketplace == "ebay"
        assert results[1].marketplace == "etsy"

    def test_detect_marketplace(self) -> None:
        """Test marketplace detection from URLs."""
        discovery = GoogleDiscovery()

        assert discovery._detect_marketplace("https://ebay.com/itm/123") == "ebay"
        assert discovery._detect_marketplace("https://etsy.com/listing/123") == "etsy"
        assert discovery._detect_marketplace("https://facebook.com/marketplace/item/123") == "facebook"
        assert discovery._detect_marketplace("https://unknown.com/page") is None


class TestDuckDuckGoDiscovery:
    """Tests for DuckDuckGoDiscovery class."""

    def test_name(self) -> None:
        """Test that NAME is correct."""
        discovery = DuckDuckGoDiscovery()
        assert discovery.NAME == "duckduckgo"

    @pytest.mark.asyncio
    async def test_search_yields_results(self) -> None:
        """Test that search yields discovery results."""
        discovery = DuckDuckGoDiscovery(rate_limit_delay=0.01, max_results=5)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        mock_page.evaluate = AsyncMock(
            return_value=[
                {
                    "url": "https://poshmark.com/listing/ring123",
                    "title": "Gold Ring",
                    "snippet": "Vintage gold ring",
                }
            ]
        )

        results = []
        async for result in discovery.search(mock_page, "gold ring"):
            results.append(result)

        assert len(results) == 1
        assert results[0].source == "duckduckgo"
        assert results[0].marketplace == "poshmark"


class TestMarketplaceFilter:
    """Tests for MarketplaceFilter class."""

    def test_detect_marketplace(self) -> None:
        """Test marketplace detection."""
        filter = MarketplaceFilter()

        assert filter.detect_marketplace("https://ebay.com/itm/123") == "ebay"
        assert filter.detect_marketplace("https://www.etsy.com/listing/123") == "etsy"
        assert filter.detect_marketplace("https://shopgoodwill.com/item/123") == "shopgoodwill"
        assert filter.detect_marketplace("https://unknown-site.com/page") is None

    def test_is_listing_url(self) -> None:
        """Test listing URL detection."""
        filter = MarketplaceFilter()

        assert filter.is_listing_url("https://ebay.com/itm/123", "ebay") is True
        assert filter.is_listing_url("https://ebay.com/seller/store", "ebay") is False
        assert filter.is_listing_url("https://etsy.com/listing/123", "etsy") is True

    def test_filter_results(self) -> None:
        """Test filtering discovery results."""
        filter = MarketplaceFilter()

        results = [
            DiscoveryResult(url="https://ebay.com/itm/123", title="Ring 1"),
            DiscoveryResult(url="https://unknown.com/page", title="Unknown"),
            DiscoveryResult(url="https://etsy.com/listing/456", title="Ring 2"),
        ]

        filtered = filter.filter_results(results)

        # Should filter out unknown domain
        assert len(filtered) == 2
        assert all(r.marketplace in ["ebay", "etsy"] for r in filtered)

    def test_filter_results_include_unknown(self) -> None:
        """Test including unknown domains."""
        filter = MarketplaceFilter(include_unknown=True)

        results = [
            DiscoveryResult(url="https://ebay.com/itm/123", title="Ring 1"),
            DiscoveryResult(url="https://unknown.com/page", title="Unknown"),
        ]

        filtered = filter.filter_results(results, listings_only=False)

        assert len(filtered) == 2

    def test_get_site_filters(self) -> None:
        """Test generating site filter strings."""
        filter = MarketplaceFilter()

        filters = filter.get_site_filters(["ebay", "etsy"])

        assert len(filters) == 2
        assert any("ebay" in f for f in filters)
        assert any("etsy" in f for f in filters)


class TestAggregatedDiscovery:
    """Tests for AggregatedDiscovery class."""

    @pytest.mark.asyncio
    async def test_aggregates_from_multiple_providers(self) -> None:
        """Test that results are aggregated from all providers."""

        # Create mock providers
        class MockProvider(SearchDiscovery):
            NAME = "mock"

            def __init__(self, results: list[DiscoveryResult]):
                super().__init__(rate_limit_delay=0.01)
                self.results = results

            async def search(self, page, query, site_filter=None):
                for r in self.results:
                    yield r

        provider1 = MockProvider([DiscoveryResult(url="https://ebay.com/1", title="Ring 1")])
        provider1.NAME = "provider1"

        provider2 = MockProvider([DiscoveryResult(url="https://etsy.com/2", title="Ring 2")])
        provider2.NAME = "provider2"

        aggregator = AggregatedDiscovery([provider1, provider2])

        mock_page = AsyncMock()
        results = []
        async for result in aggregator.discover_all(mock_page, ["test"]):
            results.append(result)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_deduplicates_results(self) -> None:
        """Test that duplicate URLs are filtered."""

        class MockProvider(SearchDiscovery):
            NAME = "mock"

            def __init__(self, results: list[DiscoveryResult]):
                super().__init__(rate_limit_delay=0.01)
                self.results = results

            async def search(self, page, query, site_filter=None):
                for r in self.results:
                    yield r

        # Both providers return same URL
        same_url = "https://ebay.com/itm/123"
        provider1 = MockProvider([DiscoveryResult(url=same_url, title="Ring 1")])
        provider2 = MockProvider([DiscoveryResult(url=same_url, title="Ring 2")])

        aggregator = AggregatedDiscovery([provider1, provider2])

        mock_page = AsyncMock()
        results = []
        async for result in aggregator.discover_all(mock_page, ["test"]):
            results.append(result)

        # Should deduplicate to single result
        assert len(results) == 1
