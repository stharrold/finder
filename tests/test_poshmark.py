"""Tests for Poshmark marketplace adapter.

Tests the batch JavaScript extraction and retry logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.poshmark import MAX_RETRIES, PoshmarkAdapter


class TestPoshmarkAdapter:
    """Tests for PoshmarkAdapter class."""

    def test_base_url(self) -> None:
        """Test that BASE_URL is correct."""
        adapter = PoshmarkAdapter()
        assert adapter.BASE_URL == "https://poshmark.com"

    def test_name(self) -> None:
        """Test that NAME is correct."""
        adapter = PoshmarkAdapter()
        assert adapter.NAME == "poshmark"

    def test_selectors_defined(self) -> None:
        """Test that required selectors are defined."""
        adapter = PoshmarkAdapter()
        required = ["listing", "title", "price", "link", "image"]
        for selector in required:
            assert selector in adapter.SELECTORS

    @pytest.mark.asyncio
    async def test_extract_listings_uses_batch_js(self) -> None:
        """Test that _extract_listings uses page.evaluate for batch extraction.

        This verifies the fix for DOM context errors - we should NOT be using
        element.query_selector() in a loop, but instead a single page.evaluate().
        """
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        # Mock the batch JavaScript extraction
        mock_page.evaluate = AsyncMock(
            return_value=[
                {
                    "href": "/listing/test-ring-123",
                    "title": "Vintage Amethyst Ring",
                    "price": "$45.00",
                    "imageUrl": "https://poshmark.com/img.jpg",
                },
                {
                    "href": "https://poshmark.com/listing/gold-ring-456",
                    "title": "Gold Pearl Ring",
                    "price": "$75.00",
                    "imageUrl": None,
                },
            ]
        )

        listings = []
        async for listing in adapter._extract_listings(mock_page):
            listings.append(listing)

        # Verify page.evaluate was called (batch extraction)
        mock_page.evaluate.assert_called_once()

        # Verify results
        assert len(listings) == 2
        assert listings[0].source == "poshmark"
        assert listings[0].url == "https://poshmark.com/listing/test-ring-123"
        assert listings[0].title == "Vintage Amethyst Ring"
        assert listings[0].price == "$45.00"

        assert listings[1].url == "https://poshmark.com/listing/gold-ring-456"
        assert listings[1].title == "Gold Pearl Ring"

    @pytest.mark.asyncio
    async def test_extract_listings_no_element_handle_iteration(self) -> None:
        """Verify we don't use query_selector_all + element iteration pattern.

        This was the root cause of Protocol errors. The new implementation
        should only use page.evaluate(), not query_selector_all + loop.
        """
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[])

        async for _ in adapter._extract_listings(mock_page):
            pass

        # Should NOT call query_selector_all for listing elements
        mock_page.query_selector_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_handles_no_results(self) -> None:
        """Test that search handles no results gracefully."""
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()
        # Mock no_results selector to return an element (indicating no results)
        mock_no_results = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_no_results)

        listings = []
        async for listing in adapter.search(mock_page, ["nonexistent query"]):
            listings.append(listing)

        assert len(listings) == 0

    @pytest.mark.asyncio
    async def test_get_listing_details_uses_batch_js(self) -> None:
        """Test that get_listing_details uses page.evaluate for extraction."""
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        # Mock the batch JavaScript extraction
        mock_page.evaluate = AsyncMock(
            return_value={
                "title": "Vintage Gold Ring",
                "price": "$125.00",
                "description": "Beautiful antique ring with amethyst stone.",
                "imageUrl": "https://poshmark.com/full-img.jpg",
            }
        )

        result = await adapter.get_listing_details(mock_page, "https://poshmark.com/listing/12345")

        assert result is not None
        assert result.title == "Vintage Gold Ring"
        assert result.price == "$125.00"
        assert result.description == "Beautiful antique ring with amethyst stone."
        assert result.source == "poshmark"

        # Verify page.evaluate was called
        mock_page.evaluate.assert_called_once()


class TestPoshmarkRetryLogic:
    """Tests for retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self) -> None:
        """Test that get_listing_details retries on timeout."""
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        from playwright.async_api import TimeoutError as PlaywrightTimeout

        # Fail twice, succeed on third attempt
        call_count = 0

        async def goto_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PlaywrightTimeout("Timeout")

        mock_page.goto = goto_with_failures
        mock_page.evaluate = AsyncMock(
            return_value={
                "title": "Success",
                "price": "$50.00",
                "description": None,
                "imageUrl": None,
            }
        )

        with patch("src.adapters.poshmark.asyncio.sleep", new_callable=AsyncMock):
            result = await adapter.get_listing_details(mock_page, "https://poshmark.com/listing/12345")

        assert result is not None
        assert result.title == "Success"
        assert call_count == 3  # Two failures + one success

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(self) -> None:
        """Test that get_listing_details gives up after MAX_RETRIES."""
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()

        from playwright.async_api import TimeoutError as PlaywrightTimeout

        # Always fail
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeout("Timeout"))

        with patch("src.adapters.poshmark.asyncio.sleep", new_callable=AsyncMock):
            result = await adapter.get_listing_details(mock_page, "https://poshmark.com/listing/12345")

        assert result is None
        assert mock_page.goto.call_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self) -> None:
        """Test that retry delays follow exponential backoff."""
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()

        from playwright.async_api import TimeoutError as PlaywrightTimeout

        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeout("Timeout"))

        sleep_delays = []

        async def capture_sleep(delay):
            sleep_delays.append(delay)

        with patch("src.adapters.poshmark.asyncio.sleep", side_effect=capture_sleep):
            await adapter.get_listing_details(mock_page, "https://poshmark.com/listing/12345")

        # Should have MAX_RETRIES - 1 delays (no delay after final attempt)
        assert len(sleep_delays) == MAX_RETRIES - 1

        # Delays should follow exponential backoff: 1, 2, 4, ...
        for i, delay in enumerate(sleep_delays):
            expected = 1.0 * (2**i)  # RETRY_BASE_DELAY * 2^attempt
            assert delay == expected


class TestPoshmarkSearchFlow:
    """Integration-style tests for full search flow."""

    @pytest.mark.asyncio
    async def test_search_yields_listings(self) -> None:
        """Test that search yields Listing objects."""
        adapter = PoshmarkAdapter(min_delay=0.01, max_delay=0.02)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        # No "no results" indicator
        mock_page.query_selector = AsyncMock(return_value=None)

        # Mock batch extraction
        mock_page.evaluate = AsyncMock(
            return_value=[
                {
                    "href": "/listing/ring-123",
                    "title": "Amethyst Ring",
                    "price": "$35.00",
                    "imageUrl": "https://poshmark.com/img.jpg",
                }
            ]
        )

        listings = []
        async for listing in adapter.search(mock_page, ["amethyst ring"]):
            listings.append(listing)

        assert len(listings) == 1
        assert listings[0].source == "poshmark"
        assert "ring-123" in listings[0].url
        assert listings[0].title == "Amethyst Ring"
        assert listings[0].price == "$35.00"
