"""Screenshot capture for promising listings."""

import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import Page

from src.models import ScoredListing

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """Captures full-page screenshots of listings with organized output."""

    def __init__(self, output_dir: Path):
        """Initialize screenshot capture.

        Args:
            output_dir: Base directory for screenshot output.
        """
        self.output_dir = Path(output_dir)

    def _get_date_folder(self) -> Path:
        """Get or create today's screenshot folder.

        Returns:
            Path to today's date-based folder.
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_folder = self.output_dir / "screenshots" / date_str
        date_folder.mkdir(parents=True, exist_ok=True)
        return date_folder

    def _generate_filename(self, listing: ScoredListing) -> str:
        """Generate filename for screenshot.

        Format: {confidence}_{source}_{timestamp}.png

        Args:
            listing: The scored listing being captured.

        Returns:
            Filename string.
        """
        timestamp = datetime.now().strftime("%H%M%S")
        # Clean source name (remove special chars)
        source = listing.source.replace("/", "_").replace(":", "")
        return f"{listing.confidence}_{source}_{timestamp}.png"

    async def capture(self, page: Page, listing: ScoredListing) -> Path | None:
        """Capture full-page screenshot of a listing.

        Args:
            page: Playwright page instance.
            listing: The scored listing to capture.

        Returns:
            Path to saved screenshot, or None if capture failed.
        """
        try:
            # Navigate to listing URL
            await page.goto(listing.url, wait_until="domcontentloaded")

            # Wait for content to load
            await page.wait_for_load_state("networkidle", timeout=15000)

            # Set viewport for consistent captures
            await page.set_viewport_size({"width": 1920, "height": 1080})

            # Generate path
            date_folder = self._get_date_folder()
            filename = self._generate_filename(listing)
            filepath = date_folder / filename

            # Capture full page screenshot
            await page.screenshot(path=str(filepath), full_page=True)

            logger.info(f"Screenshot saved: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error capturing screenshot for {listing.url}: {e}")
            return None

    async def capture_with_existing_page(self, page: Page, listing: ScoredListing) -> Path | None:
        """Capture screenshot from page already showing the listing.

        Use this when the page is already on the listing (no navigation needed).

        Args:
            page: Playwright page instance already on the listing.
            listing: The scored listing being captured.

        Returns:
            Path to saved screenshot, or None if capture failed.
        """
        try:
            # Set viewport for consistent captures
            await page.set_viewport_size({"width": 1920, "height": 1080})

            # Generate path
            date_folder = self._get_date_folder()
            filename = self._generate_filename(listing)
            filepath = date_folder / filename

            # Capture full page screenshot
            await page.screenshot(path=str(filepath), full_page=True)

            logger.info(f"Screenshot saved: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None

    def copy_to_high_confidence(self, screenshot_path: Path) -> Path | None:
        """Copy high-confidence screenshot to special folder.

        Args:
            screenshot_path: Path to the original screenshot.

        Returns:
            Path to the copy in high_confidence folder, or None if failed.
        """
        try:
            import shutil

            high_conf_dir = self.output_dir / "potential_matches" / "high_confidence"
            high_conf_dir.mkdir(parents=True, exist_ok=True)

            dest_path = high_conf_dir / screenshot_path.name
            shutil.copy2(screenshot_path, dest_path)

            logger.info(f"Copied to high confidence: {dest_path}")
            return dest_path

        except Exception as e:
            logger.error(f"Error copying to high confidence: {e}")
            return None

    def get_screenshots_for_date(self, date_str: str | None = None) -> list[Path]:
        """Get all screenshots for a specific date.

        Args:
            date_str: Date string in YYYY-MM-DD format. Defaults to today.

        Returns:
            List of screenshot paths for that date.
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        date_folder = self.output_dir / "screenshots" / date_str

        if not date_folder.exists():
            return []

        return sorted(date_folder.glob("*.png"))
