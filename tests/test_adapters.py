"""Tests for marketplace adapters."""

from unittest.mock import AsyncMock

import pytest

from src.adapters.shopgoodwill import ShopGoodwillAdapter


class TestMarketplaceAdapter:
    """Tests for base MarketplaceAdapter class."""

    def test_rate_limit_settings(self) -> None:
        """Test that rate limit settings are configurable."""
        adapter = ShopGoodwillAdapter(min_delay=1.0, max_delay=2.0)
        assert adapter.min_delay == 1.0
        assert adapter.max_delay == 2.0

    def test_extract_text_with_value(self) -> None:
        """Test _extract_text with valid text."""
        adapter = ShopGoodwillAdapter()
        result = adapter._extract_text("  test value  ")
        assert result == "test value"

    def test_extract_text_with_none(self) -> None:
        """Test _extract_text with None returns default."""
        adapter = ShopGoodwillAdapter()
        result = adapter._extract_text(None, "default")
        assert result == "default"


class TestShopGoodwillAdapter:
    """Tests for ShopGoodwillAdapter class."""

    def test_base_url(self) -> None:
        """Test that BASE_URL is correct."""
        adapter = ShopGoodwillAdapter()
        assert adapter.BASE_URL == "https://shopgoodwill.com"

    def test_name(self) -> None:
        """Test that NAME is correct."""
        adapter = ShopGoodwillAdapter()
        assert adapter.NAME == "shopgoodwill"

    def test_selectors_defined(self) -> None:
        """Test that required selectors are defined."""
        adapter = ShopGoodwillAdapter()
        required = ["listing", "title", "price", "link"]
        for selector in required:
            assert selector in adapter.SELECTORS

    @pytest.mark.asyncio
    async def test_search_yields_listings(self) -> None:
        """Test that search yields Listing objects."""
        adapter = ShopGoodwillAdapter(min_delay=0.01, max_delay=0.02)

        # Create mock page
        mock_page = AsyncMock()

        # Mock wait_for_selector to succeed
        mock_page.wait_for_selector = AsyncMock()

        # Create mock listing element
        mock_element = AsyncMock()
        mock_link = AsyncMock()
        mock_link.get_attribute = AsyncMock(return_value="/item/12345")
        mock_link.text_content = AsyncMock(return_value="Test Ring")

        mock_title = AsyncMock()
        mock_title.text_content = AsyncMock(return_value="Gold Amethyst Ring")

        mock_price = AsyncMock()
        mock_price.text_content = AsyncMock(return_value="$50.00")

        mock_image = AsyncMock()
        mock_image.get_attribute = AsyncMock(return_value="https://example.com/img.jpg")

        # Setup element query selectors
        async def element_query_selector(selector):
            if "link" in selector or "href" in selector:
                return mock_link
            elif "title" in selector:
                return mock_title
            elif "price" in selector or "bid" in selector:
                return mock_price
            elif "image" in selector or "img" in selector:
                return mock_image
            return None

        mock_element.query_selector = element_query_selector

        # Return one listing element
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])

        # Page-level query_selector needs to return None for no-results check
        # and then return None for has_next_page check
        mock_page.query_selector = AsyncMock(return_value=None)

        # Collect results
        listings = []
        async for listing in adapter.search(mock_page, ["test query"]):
            listings.append(listing)

        # Verify
        assert len(listings) == 1
        assert listings[0].source == "shopgoodwill"
        assert "12345" in listings[0].url
        assert listings[0].title == "Gold Amethyst Ring"
        assert listings[0].price == "$50.00"

    @pytest.mark.asyncio
    async def test_search_handles_no_results(self) -> None:
        """Test that search handles no results gracefully."""
        adapter = ShopGoodwillAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()

        # Mock no_results selector to return an element (indicating no results)
        mock_no_results = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_no_results)

        listings = []
        async for listing in adapter.search(mock_page, ["nonexistent query"]):
            listings.append(listing)

        assert len(listings) == 0

    @pytest.mark.asyncio
    async def test_get_listing_details(self) -> None:
        """Test fetching detailed listing information."""
        adapter = ShopGoodwillAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()

        # Setup mocks for detail page elements
        mock_title = AsyncMock()
        mock_title.text_content = AsyncMock(return_value="Detailed Title")

        mock_price = AsyncMock()
        mock_price.text_content = AsyncMock(return_value="$100.00")

        mock_desc = AsyncMock()
        mock_desc.text_content = AsyncMock(return_value="Full description")

        mock_image = AsyncMock()
        mock_image.get_attribute = AsyncMock(return_value="https://example.com/full.jpg")

        async def query_selector(selector):
            if "h1" in selector:
                return mock_title
            elif "bid" in selector or "price" in selector:
                return mock_price
            elif "description" in selector:
                return mock_desc
            elif "image" in selector:
                return mock_image
            return None

        mock_page.query_selector = query_selector

        result = await adapter.get_listing_details(mock_page, "https://shopgoodwill.com/item/12345")

        assert result is not None
        assert result.title == "Detailed Title"
        assert result.price == "$100.00"
        assert result.description == "Full description"
        assert result.source == "shopgoodwill"

    @pytest.mark.asyncio
    async def test_get_listing_details_handles_error(self) -> None:
        """Test that get_listing_details returns None on error."""
        adapter = ShopGoodwillAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))

        result = await adapter.get_listing_details(mock_page, "https://shopgoodwill.com/item/12345")

        assert result is None

    @pytest.mark.asyncio
    async def test_has_next_page_true(self) -> None:
        """Test _has_next_page returns True when next page exists."""
        adapter = ShopGoodwillAdapter()

        mock_page = AsyncMock()
        mock_button = AsyncMock()
        mock_button.get_attribute = AsyncMock(return_value=None)  # Not disabled

        mock_page.query_selector = AsyncMock(return_value=mock_button)

        result = await adapter._has_next_page(mock_page)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_next_page_false_when_disabled(self) -> None:
        """Test _has_next_page returns False when button disabled."""
        adapter = ShopGoodwillAdapter()

        mock_page = AsyncMock()
        mock_button = AsyncMock()
        mock_button.get_attribute = AsyncMock(side_effect=lambda attr: "true" if attr == "disabled" else "btn disabled")

        mock_page.query_selector = AsyncMock(return_value=mock_button)

        result = await adapter._has_next_page(mock_page)
        assert result is False

    @pytest.mark.asyncio
    async def test_has_next_page_false_when_no_button(self) -> None:
        """Test _has_next_page returns False when no next button."""
        adapter = ShopGoodwillAdapter()

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await adapter._has_next_page(mock_page)
        assert result is False
