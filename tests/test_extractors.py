"""Tests for adaptive extractors."""

from unittest.mock import AsyncMock

import pytest

from src.extractors.base import AdaptiveExtractor, ExtractedListing
from src.extractors.bridge import LegacyAdapterBridge
from src.extractors.generic import GenericListingExtractor
from src.extractors.structured import StructuredDataExtractor
from src.models import Listing


class TestExtractedListing:
    """Tests for ExtractedListing dataclass."""

    def test_to_listing(self) -> None:
        """Test conversion to Listing model."""
        extracted = ExtractedListing(
            url="https://ebay.com/itm/123",
            title="Vintage Ring",
            price="$50.00",
            description="Beautiful ring",
            image_url="https://example.com/img.jpg",
            source="ebay",
        )

        listing = extracted.to_listing()

        assert isinstance(listing, Listing)
        assert listing.url == "https://ebay.com/itm/123"
        assert listing.title == "Vintage Ring"
        assert listing.price == "$50.00"
        assert listing.source == "ebay"


class TestStructuredDataExtractor:
    """Tests for StructuredDataExtractor."""

    def test_name(self) -> None:
        """Test extractor name."""
        extractor = StructuredDataExtractor()
        assert extractor.NAME == "structured"

    @pytest.mark.asyncio
    async def test_can_extract_with_json_ld(self) -> None:
        """Test detection of JSON-LD structured data."""
        extractor = StructuredDataExtractor()
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=True)

        result = await extractor.can_extract(mock_page, "https://example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_extract_json_ld(self) -> None:
        """Test extraction from JSON-LD Product schema."""
        extractor = StructuredDataExtractor()
        mock_page = AsyncMock()

        mock_page.evaluate = AsyncMock(
            return_value={
                "jsonLd": {
                    "@type": "Product",
                    "name": "Vintage Amethyst Ring",
                    "description": "Beautiful antique ring",
                    "offers": {"price": "125.00", "priceCurrency": "$"},
                    "image": "https://example.com/ring.jpg",
                },
                "openGraph": {},
                "microdata": {},
            }
        )

        result = await extractor.extract(mock_page, "https://example.com/listing")

        assert result is not None
        assert result.title == "Vintage Amethyst Ring"
        assert result.price == "$125.00"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_extract_open_graph(self) -> None:
        """Test extraction from OpenGraph meta tags."""
        extractor = StructuredDataExtractor()
        mock_page = AsyncMock()

        mock_page.evaluate = AsyncMock(
            return_value={
                "jsonLd": None,
                "openGraph": {
                    "title": "Gold Pearl Ring",
                    "description": "Elegant ring with pearls",
                    "image": "https://example.com/pearl.jpg",
                },
                "microdata": {},
            }
        )

        result = await extractor.extract(mock_page, "https://example.com/listing")

        assert result is not None
        assert result.title == "Gold Pearl Ring"
        assert result.confidence == 0.7


class TestGenericListingExtractor:
    """Tests for GenericListingExtractor."""

    def test_name(self) -> None:
        """Test extractor name."""
        extractor = GenericListingExtractor()
        assert extractor.NAME == "generic"

    @pytest.mark.asyncio
    async def test_can_extract_always_true(self) -> None:
        """Test that generic extractor always returns True."""
        extractor = GenericListingExtractor()
        mock_page = AsyncMock()

        result = await extractor.can_extract(mock_page, "https://example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_extract_with_h1_title(self) -> None:
        """Test extraction using h1 as title."""
        extractor = GenericListingExtractor()
        mock_page = AsyncMock()

        mock_page.evaluate = AsyncMock(
            return_value={
                "title": "Antique Ring for Sale",
                "description": "A beautiful vintage ring",
                "priceText": "$75.00",
                "imageUrl": "https://example.com/ring.jpg",
                "allText": "",
            }
        )

        result = await extractor.extract(mock_page, "https://example.com/item")

        assert result is not None
        assert result.title == "Antique Ring for Sale"
        assert result.price == "$75.00"
        assert result.confidence == 0.5

    def test_extract_price_usd(self) -> None:
        """Test price extraction for USD format."""
        extractor = GenericListingExtractor()

        assert extractor._extract_price("$123.45") == "$123.45"
        assert extractor._extract_price("$1,234.56") == "$1,234.56"
        assert extractor._extract_price("Price: $50") == "$50"

    def test_extract_price_other_currencies(self) -> None:
        """Test price extraction for other currencies."""
        extractor = GenericListingExtractor()

        assert extractor._extract_price("£99.99") == "£99.99"
        assert extractor._extract_price("€50.00") == "€50.00"

    def test_extract_price_no_match(self) -> None:
        """Test price extraction returns None when no price found."""
        extractor = GenericListingExtractor()

        assert extractor._extract_price("No price here") is None
        assert extractor._extract_price("") is None


class TestLegacyAdapterBridge:
    """Tests for LegacyAdapterBridge."""

    def test_name(self) -> None:
        """Test extractor name."""
        bridge = LegacyAdapterBridge()
        assert bridge.NAME == "legacy"

    def test_detect_adapter_ebay(self) -> None:
        """Test adapter detection for eBay URLs."""
        bridge = LegacyAdapterBridge()

        assert bridge._detect_adapter("https://ebay.com/itm/123") == "ebay"
        assert bridge._detect_adapter("https://www.ebay.co.uk/itm/123") == "ebay"

    def test_detect_adapter_etsy(self) -> None:
        """Test adapter detection for Etsy URLs."""
        bridge = LegacyAdapterBridge()

        assert bridge._detect_adapter("https://etsy.com/listing/123") == "etsy"
        assert bridge._detect_adapter("https://www.etsy.com/uk/listing/123") == "etsy"

    def test_detect_adapter_unknown(self) -> None:
        """Test adapter detection for unknown URLs."""
        bridge = LegacyAdapterBridge()

        assert bridge._detect_adapter("https://unknown-site.com/page") is None

    @pytest.mark.asyncio
    async def test_can_extract_known_domain(self) -> None:
        """Test that can_extract returns True for known domains."""
        bridge = LegacyAdapterBridge()
        mock_page = AsyncMock()

        result = await bridge.can_extract(mock_page, "https://ebay.com/itm/123")
        assert result is True

    @pytest.mark.asyncio
    async def test_can_extract_unknown_domain(self) -> None:
        """Test that can_extract returns False for unknown domains."""
        bridge = LegacyAdapterBridge()
        mock_page = AsyncMock()

        result = await bridge.can_extract(mock_page, "https://unknown.com/page")
        assert result is False


class TestAdaptiveExtractor:
    """Tests for AdaptiveExtractor chain."""

    @pytest.mark.asyncio
    async def test_uses_first_successful_extractor(self) -> None:
        """Test that first successful extractor is used."""

        class FailingExtractor:
            NAME = "failing"

            async def can_extract(self, page, url):
                return True

            async def extract(self, page, url):
                return None  # Fails

        class SuccessfulExtractor:
            NAME = "successful"

            async def can_extract(self, page, url):
                return True

            async def extract(self, page, url):
                return ExtractedListing(url=url, title="Found it!")

        extractor = AdaptiveExtractor([FailingExtractor(), SuccessfulExtractor()])
        mock_page = AsyncMock()

        result = await extractor.extract(mock_page, "https://example.com")

        assert result is not None
        assert result.title == "Found it!"
        assert result.extraction_method == "successful"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_fail(self) -> None:
        """Test that None is returned when all extractors fail."""

        class FailingExtractor:
            NAME = "failing"

            async def can_extract(self, page, url):
                return True

            async def extract(self, page, url):
                return None

        extractor = AdaptiveExtractor([FailingExtractor()])
        mock_page = AsyncMock()

        result = await extractor.extract(mock_page, "https://example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_skips_extractors_that_cannot_extract(self) -> None:
        """Test that extractors that return False for can_extract are skipped."""

        class CannotExtract:
            NAME = "cannot"

            async def can_extract(self, page, url):
                return False

            async def extract(self, page, url):
                raise Exception("Should not be called")

        class CanExtract:
            NAME = "can"

            async def can_extract(self, page, url):
                return True

            async def extract(self, page, url):
                return ExtractedListing(url=url, title="Success")

        extractor = AdaptiveExtractor([CannotExtract(), CanExtract()])
        mock_page = AsyncMock()

        result = await extractor.extract(mock_page, "https://example.com")

        assert result is not None
        assert result.title == "Success"
