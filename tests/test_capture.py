"""Tests for screenshot capture."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.capture import ScreenshotCapture
from src.models import ScoredListing


class TestScreenshotCapture:
    """Tests for ScreenshotCapture class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test initialization with output directory."""
        capture = ScreenshotCapture(tmp_path)
        assert capture.output_dir == tmp_path

    def test_get_date_folder_creates_directory(self, tmp_path: Path) -> None:
        """Test that date folder is created."""
        capture = ScreenshotCapture(tmp_path)
        date_folder = capture._get_date_folder()

        assert date_folder.exists()
        assert "screenshots" in str(date_folder)
        assert datetime.now().strftime("%Y-%m-%d") in str(date_folder)

    def test_generate_filename_format(self, tmp_path: Path) -> None:
        """Test filename generation format."""
        capture = ScreenshotCapture(tmp_path)
        listing = ScoredListing(
            url="https://example.com/item/123",
            source="ebay",
            title="Test Ring",
            price="$100",
            score=75,
            confidence="high",
            matched_factors=["gold"],
        )

        filename = capture._generate_filename(listing)

        assert filename.startswith("high_ebay_")
        assert filename.endswith(".png")

    def test_generate_filename_cleans_source(self, tmp_path: Path) -> None:
        """Test that special characters in source are cleaned."""
        capture = ScreenshotCapture(tmp_path)
        listing = ScoredListing(
            url="https://example.com/item/123",
            source="craigslist_indianapolis",
            title="Test Ring",
            price="$100",
            score=45,
            confidence="medium",
            matched_factors=["gold"],
        )

        filename = capture._generate_filename(listing)

        assert "craigslist_indianapolis" in filename
        assert "/" not in filename
        assert ":" not in filename

    @pytest.mark.asyncio
    async def test_capture_saves_screenshot(self, tmp_path: Path) -> None:
        """Test that capture saves screenshot to correct location."""
        capture = ScreenshotCapture(tmp_path)

        mock_page = AsyncMock()

        listing = ScoredListing(
            url="https://example.com/item/123",
            source="shopgoodwill",
            title="Gold Amethyst Ring",
            price="$50",
            score=80,
            confidence="high",
            matched_factors=["gold", "amethyst"],
        )

        result = await capture.capture(mock_page, listing)

        # Verify page interactions
        mock_page.goto.assert_called_once()
        mock_page.wait_for_load_state.assert_called_once()
        mock_page.set_viewport_size.assert_called_once_with({"width": 1920, "height": 1080})
        mock_page.screenshot.assert_called_once()

        # Verify result path
        assert result is not None
        assert "screenshots" in str(result)
        assert "high_shopgoodwill" in str(result)
        assert result.suffix == ".png"

    @pytest.mark.asyncio
    async def test_capture_handles_error(self, tmp_path: Path) -> None:
        """Test that capture returns None on error."""
        capture = ScreenshotCapture(tmp_path)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))

        listing = ScoredListing(
            url="https://example.com/item/123",
            source="ebay",
            title="Test Ring",
            price="$100",
            score=75,
            confidence="high",
            matched_factors=["gold"],
        )

        result = await capture.capture(mock_page, listing)
        assert result is None

    @pytest.mark.asyncio
    async def test_capture_with_existing_page(self, tmp_path: Path) -> None:
        """Test capture from page already on listing."""
        capture = ScreenshotCapture(tmp_path)

        mock_page = AsyncMock()

        listing = ScoredListing(
            url="https://example.com/item/123",
            source="etsy",
            title="Test Ring",
            price="$100",
            score=50,
            confidence="medium",
            matched_factors=["gold"],
        )

        result = await capture.capture_with_existing_page(mock_page, listing)

        # Should not navigate
        mock_page.goto.assert_not_called()
        # Should capture screenshot
        mock_page.screenshot.assert_called_once()

        assert result is not None

    def test_copy_to_high_confidence(self, tmp_path: Path) -> None:
        """Test copying screenshot to high confidence folder."""
        capture = ScreenshotCapture(tmp_path)

        # Create a test screenshot file
        screenshots_dir = tmp_path / "screenshots" / "2024-11-30"
        screenshots_dir.mkdir(parents=True)
        test_screenshot = screenshots_dir / "high_ebay_120000.png"
        test_screenshot.write_bytes(b"fake image data")

        result = capture.copy_to_high_confidence(test_screenshot)

        assert result is not None
        assert result.exists()
        assert "high_confidence" in str(result)
        assert result.name == test_screenshot.name

    def test_copy_to_high_confidence_handles_error(self, tmp_path: Path) -> None:
        """Test that copy returns None on error."""
        capture = ScreenshotCapture(tmp_path)

        # Try to copy non-existent file
        fake_path = tmp_path / "nonexistent.png"
        result = capture.copy_to_high_confidence(fake_path)

        assert result is None

    def test_get_screenshots_for_date_today(self, tmp_path: Path) -> None:
        """Test getting screenshots for today."""
        capture = ScreenshotCapture(tmp_path)

        # Create today's screenshot folder with some files
        today = datetime.now().strftime("%Y-%m-%d")
        screenshots_dir = tmp_path / "screenshots" / today
        screenshots_dir.mkdir(parents=True)

        # Create test files
        (screenshots_dir / "high_ebay_100000.png").write_bytes(b"img1")
        (screenshots_dir / "medium_etsy_110000.png").write_bytes(b"img2")
        (screenshots_dir / "low_craigslist_120000.png").write_bytes(b"img3")

        result = capture.get_screenshots_for_date()

        assert len(result) == 3
        assert all(p.suffix == ".png" for p in result)

    def test_get_screenshots_for_date_specific(self, tmp_path: Path) -> None:
        """Test getting screenshots for specific date."""
        capture = ScreenshotCapture(tmp_path)

        # Create screenshot folder for specific date
        screenshots_dir = tmp_path / "screenshots" / "2024-11-01"
        screenshots_dir.mkdir(parents=True)
        (screenshots_dir / "high_ebay_100000.png").write_bytes(b"img")

        result = capture.get_screenshots_for_date("2024-11-01")

        assert len(result) == 1

    def test_get_screenshots_for_date_empty(self, tmp_path: Path) -> None:
        """Test getting screenshots for date with no screenshots."""
        capture = ScreenshotCapture(tmp_path)

        result = capture.get_screenshots_for_date("2020-01-01")

        assert len(result) == 0
