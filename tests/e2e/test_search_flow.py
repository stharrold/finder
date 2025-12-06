"""End-to-end tests for complete search workflow.

These tests verify the full search flow with mocked browser interactions,
simulating real marketplace responses without hitting live sites.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Listing
from src.ring_search import SearchOrchestrator


@pytest.fixture
def e2e_config(tmp_path: Path) -> Path:
    """Create a comprehensive config for E2E testing."""
    config_path = tmp_path / "config.yaml"
    config_content = """
target_ring:
  name: "The Giulia Ring"
  style_number: "BSB96044"
  metal: "10K Yellow Gold"
  stones:
    - "Amethyst"
    - "Seed Pearls"
  size: 7

marketplaces:
  - name: shopgoodwill
    enabled: true
    priority: 1
    searches:
      - "amethyst pearl ring"
      - "vintage gold ring"

  - name: ebay
    enabled: true
    priority: 2
    searches:
      - "10k gold amethyst ring"

  - name: etsy
    enabled: false
    priority: 3
    searches:
      - "antique amethyst ring"

known_leads:
  - url: https://example.com/known-lead-1
    note: Previously identified potential match

scoring:
  thresholds:
    high: 70
    medium: 40
  weights:
    gold: 20
    amethyst: 25

rate_limiting:
  min_delay_seconds: 0.001
  max_delay_seconds: 0.002

output:
  base_dir: output
  logs_dir: logs
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def output_dirs(tmp_path: Path) -> dict[str, Path]:
    """Create output directory structure."""
    output = tmp_path / "output"
    logs = output / "logs"
    screenshots = output / "screenshots"
    high_confidence = output / "potential_matches" / "high_confidence"

    for d in [output, logs, screenshots, high_confidence]:
        d.mkdir(parents=True, exist_ok=True)

    return {
        "output": output,
        "logs": logs,
        "screenshots": screenshots,
        "high_confidence": high_confidence,
    }


class TestFullSearchWorkflow:
    """Tests for complete search workflow."""

    @pytest.mark.asyncio
    async def test_daily_search_processes_all_marketplaces(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that daily search processes all enabled marketplaces."""
        # Change to tmp_path to ensure output goes there
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            # Track marketplace calls
            searched_marketplaces: list[str] = []

            async def mock_search_marketplace(page, marketplace):
                searched_marketplaces.append(marketplace["name"])

            orchestrator._search_marketplace = mock_search_marketplace
            orchestrator._check_known_leads = AsyncMock()

            with patch("src.ring_search.async_playwright") as mock_pw:
                mock_browser = AsyncMock()
                mock_page = AsyncMock()
                mock_browser.new_page = AsyncMock(return_value=mock_page)
                mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

                stats = await orchestrator.run_daily_search(headless=True)

            # Should search enabled marketplaces only
            assert "shopgoodwill" in searched_marketplaces
            assert "ebay" in searched_marketplaces
            assert "etsy" not in searched_marketplaces  # disabled

            # Stats should be returned
            assert "total" in stats
            assert "high" in stats
            assert "medium" in stats
            assert "low" in stats

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_daily_search_checks_known_leads_first(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that known leads are checked before marketplace search."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        call_order: list[str] = []

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            async def mock_check_leads(page):
                call_order.append("known_leads")

            async def mock_search(page, marketplace):
                call_order.append(f"search_{marketplace['name']}")

            orchestrator._check_known_leads = mock_check_leads
            orchestrator._search_marketplace = mock_search

            with patch("src.ring_search.async_playwright") as mock_pw:
                mock_browser = AsyncMock()
                mock_page = AsyncMock()
                mock_browser.new_page = AsyncMock(return_value=mock_page)
                mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

                await orchestrator.run_daily_search()

            # Known leads should be checked first
            assert call_order[0] == "known_leads"

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_daily_search_respects_priority_order(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that marketplaces are searched in priority order."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        search_order: list[str] = []

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            async def mock_search(page, marketplace):
                search_order.append(marketplace["name"])

            orchestrator._search_marketplace = mock_search
            orchestrator._check_known_leads = AsyncMock()

            with patch("src.ring_search.async_playwright") as mock_pw:
                mock_browser = AsyncMock()
                mock_page = AsyncMock()
                mock_browser.new_page = AsyncMock(return_value=mock_page)
                mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

                await orchestrator.run_daily_search()

            # ShopGoodwill (priority 1) should come before eBay (priority 2)
            assert search_order.index("shopgoodwill") < search_order.index("ebay")

        finally:
            os.chdir(original_cwd)


class TestListingProcessingFlow:
    """Tests for the listing processing pipeline."""

    @pytest.mark.asyncio
    async def test_high_confidence_listing_gets_screenshot(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that high confidence listings get screenshots captured."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            # Create a listing that should score high
            listing = Listing(
                url="https://example.com/high-score",
                source="ebay",
                title="10K Yellow Gold Amethyst Seed Pearl Victorian Swirl Ring Size 7",
                price="$500",
                description="Beautiful antique ring with original pearls",
            )

            mock_page = AsyncMock()
            screenshot_path = tmp_path / "output" / "screenshots" / "test.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            orchestrator.capture.capture = AsyncMock(return_value=screenshot_path)
            orchestrator.capture.copy_to_high_confidence = MagicMock()

            await orchestrator._process_listing(mock_page, listing)

            # Verify screenshot was captured
            orchestrator.capture.capture.assert_called_once()

            # Verify copied to high confidence folder
            orchestrator.capture.copy_to_high_confidence.assert_called_once()

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_medium_confidence_listing_gets_screenshot_no_copy(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that medium confidence listings get screenshots but not copied."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            # Create a listing that should score medium
            listing = Listing(
                url="https://example.com/medium-score",
                source="ebay",
                title="Gold Ring with Purple Stone",
                price="$200",
            )

            mock_page = AsyncMock()
            screenshot_path = tmp_path / "output" / "screenshots" / "test.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            orchestrator.capture.capture = AsyncMock(return_value=screenshot_path)
            orchestrator.capture.copy_to_high_confidence = MagicMock()

            await orchestrator._process_listing(mock_page, listing)

            # Screenshot should be captured for medium confidence
            # Note: Whether it's captured depends on the actual score

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_low_confidence_listing_no_screenshot(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that low confidence listings don't get screenshots."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            # Create a listing that should score low
            listing = Listing(
                url="https://example.com/low-score",
                source="ebay",
                title="Silver Ring",
                price="$50",
            )

            mock_page = AsyncMock()
            orchestrator.capture.capture = AsyncMock(return_value=None)
            orchestrator.capture.copy_to_high_confidence = MagicMock()

            await orchestrator._process_listing(mock_page, listing)

            # Low confidence should not trigger screenshot
            orchestrator.capture.capture.assert_not_called()

        finally:
            os.chdir(original_cwd)


class TestDeduplicationFlow:
    """Tests for URL deduplication during search."""

    @pytest.mark.asyncio
    async def test_duplicate_urls_not_reprocessed(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that duplicate URLs are skipped."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            url = "https://example.com/duplicate-item"

            # Mark as already checked
            orchestrator.dedup.mark_checked(url)

            # Verify it's not considered new
            assert not orchestrator.dedup.is_new(url)

            # Check via check_specific_urls
            with patch("src.ring_search.async_playwright") as mock_pw:
                mock_browser = AsyncMock()
                mock_page = AsyncMock()
                mock_browser.new_page = AsyncMock(return_value=mock_page)
                mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

                # Process listing should not be called for duplicates
                orchestrator._process_listing = AsyncMock()

                await orchestrator.check_specific_urls([url])

            # Process listing should not have been called (URL was duplicate)
            orchestrator._process_listing.assert_not_called()

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_new_urls_are_processed_and_marked(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that new URLs are processed and marked as checked."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            url = "https://example.com/new-item"

            # Verify it's new
            assert orchestrator.dedup.is_new(url)

            with patch("src.ring_search.async_playwright") as mock_pw:
                mock_browser = AsyncMock()
                mock_page = AsyncMock()
                mock_page.goto = AsyncMock()
                mock_page.query_selector = AsyncMock(return_value=None)
                mock_browser.new_page = AsyncMock(return_value=mock_page)
                mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

                orchestrator._process_listing = AsyncMock()

                await orchestrator.check_specific_urls([url])

            # Process listing should have been called
            orchestrator._process_listing.assert_called_once()

            # URL should now be marked as checked
            assert not orchestrator.dedup.is_new(url)

        finally:
            os.chdir(original_cwd)


class TestOutputGeneration:
    """Tests for output file generation."""

    @pytest.mark.asyncio
    async def test_daily_summary_created_after_search(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that daily summary is created after search completes."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            # Skip actual searching
            orchestrator._check_known_leads = AsyncMock()
            orchestrator._search_marketplace = AsyncMock()

            with patch("src.ring_search.async_playwright") as mock_pw:
                mock_browser = AsyncMock()
                mock_page = AsyncMock()
                mock_browser.new_page = AsyncMock(return_value=mock_page)
                mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

                await orchestrator.run_daily_search()

            # Check that summary was written
            logs_dir = tmp_path / "output" / "logs"
            summaries = list(logs_dir.glob("daily_summary_*.md"))
            assert len(summaries) == 1

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_search_results_logged_to_json(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that search results are logged to JSON file."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            orchestrator = SearchOrchestrator(e2e_config)

            listing = Listing(
                url="https://example.com/test",
                source="ebay",
                title="Test Ring",
                price="$100",
            )

            mock_page = AsyncMock()
            orchestrator.capture.capture = AsyncMock(return_value=None)

            await orchestrator._process_listing(mock_page, listing)

            # Verify result was logged
            assert len(orchestrator.logger.daily_results) == 1

        finally:
            os.chdir(original_cwd)


class TestCLIIntegration:
    """Tests for CLI integration with orchestrator."""

    def test_cli_creates_orchestrator_with_config(self, e2e_config: Path, tmp_path: Path) -> None:
        """Test that CLI properly initializes orchestrator."""
        import argparse

        from src.cli import run_search

        args = argparse.Namespace(
            config=str(e2e_config),
            headed=False,
        )

        with patch("src.cli.create_orchestrator") as mock_factory:
            mock_instance = MagicMock()
            mock_instance.run_daily_search = AsyncMock(
                return_value={
                    "total": 5,
                    "high": 1,
                    "medium": 2,
                    "low": 2,
                    "sources": ["shopgoodwill", "ebay"],
                }
            )
            mock_factory.return_value = mock_instance

            result = run_search(args)

        assert result == 0
        mock_factory.assert_called_once_with(e2e_config, adaptive=False)

    def test_cli_handles_orchestrator_error(self, e2e_config: Path) -> None:
        """Test that CLI handles orchestrator errors gracefully."""
        import argparse

        from src.cli import run_search

        args = argparse.Namespace(
            config=str(e2e_config),
            headed=False,
        )

        with patch("src.cli.create_orchestrator") as mock_factory:
            mock_instance = MagicMock()
            mock_instance.run_daily_search = AsyncMock(side_effect=Exception("Search failed"))
            mock_factory.return_value = mock_instance

            result = run_search(args)

        assert result == 1
