"""Tests for search orchestrator."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ring_search import SearchOrchestrator


class TestSearchOrchestrator:
    """Tests for SearchOrchestrator class."""

    @pytest.fixture
    def config_file(self, tmp_path: Path) -> Path:
        """Create a test config file."""
        config_path = tmp_path / "config.yaml"
        config_content = """
marketplaces:
  - name: shopgoodwill
    enabled: true
    priority: 1
    searches:
      - "amethyst pearl ring"

  - name: ebay
    enabled: true
    priority: 2
    searches:
      - "vintage gold ring"

  - name: etsy
    enabled: false
    priority: 3
    searches:
      - "antique ring"

known_leads:
  - url: https://example.com/lead1
    note: Test lead

scoring:
  thresholds:
    high: 70
    medium: 40

rate_limiting:
  min_delay_seconds: 0.01
  max_delay_seconds: 0.02

output:
  base_dir: output
  logs_dir: logs
"""
        config_path.write_text(config_content)
        return config_path

    def test_init_loads_config(self, config_file: Path) -> None:
        """Test that orchestrator loads configuration."""
        orchestrator = SearchOrchestrator(config_file)

        assert "marketplaces" in orchestrator.config
        assert len(orchestrator.config["marketplaces"]) == 3

    def test_init_creates_components(self, config_file: Path) -> None:
        """Test that orchestrator creates all components."""
        orchestrator = SearchOrchestrator(config_file)

        assert orchestrator.dedup is not None
        assert orchestrator.logger is not None
        assert orchestrator.scorer is not None
        assert orchestrator.capture is not None

    def test_init_raises_on_missing_config(self, tmp_path: Path) -> None:
        """Test that init raises for missing config."""
        with pytest.raises(FileNotFoundError):
            SearchOrchestrator(tmp_path / "nonexistent.yaml")

    def test_create_adapter_shopgoodwill(self, config_file: Path) -> None:
        """Test creating ShopGoodwill adapter."""
        orchestrator = SearchOrchestrator(config_file)
        marketplace = {"name": "shopgoodwill", "searches": ["test"]}

        adapter = orchestrator._create_adapter(marketplace)

        assert adapter is not None
        assert adapter.NAME == "shopgoodwill"

    def test_create_adapter_ebay(self, config_file: Path) -> None:
        """Test creating eBay adapter."""
        orchestrator = SearchOrchestrator(config_file)
        marketplace = {"name": "ebay", "searches": ["test"]}

        adapter = orchestrator._create_adapter(marketplace)

        assert adapter is not None
        assert adapter.NAME == "ebay"

    def test_create_adapter_craigslist_with_regions(self, config_file: Path) -> None:
        """Test creating Craigslist adapter with custom regions."""
        orchestrator = SearchOrchestrator(config_file)
        marketplace = {
            "name": "craigslist",
            "regions": ["indianapolis", "chicago"],
            "searches": ["test"],
        }

        adapter = orchestrator._create_adapter(marketplace)

        assert adapter is not None
        assert adapter.NAME == "craigslist"
        assert adapter.regions == ["indianapolis", "chicago"]

    def test_create_adapter_unknown(self, config_file: Path) -> None:
        """Test that unknown marketplace returns None."""
        orchestrator = SearchOrchestrator(config_file)
        marketplace = {"name": "unknown_site", "searches": ["test"]}

        adapter = orchestrator._create_adapter(marketplace)

        assert adapter is None

    def test_rate_limiting_from_config(self, config_file: Path) -> None:
        """Test that rate limiting is loaded from config."""
        orchestrator = SearchOrchestrator(config_file)

        assert orchestrator.min_delay == 0.01
        assert orchestrator.max_delay == 0.02

    @pytest.mark.asyncio
    async def test_run_daily_search_skips_disabled(self, config_file: Path, tmp_path: Path) -> None:
        """Test that disabled marketplaces are skipped."""
        orchestrator = SearchOrchestrator(config_file)

        # Track which marketplaces were searched
        searched = []

        async def mock_search(page, marketplace):
            searched.append(marketplace["name"])

        orchestrator._search_marketplace = mock_search
        orchestrator._check_known_leads = AsyncMock()

        with patch("src.ring_search.async_playwright") as mock_pw:
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

            await orchestrator.run_daily_search()

        # Etsy should be skipped (enabled: false)
        assert "shopgoodwill" in searched
        assert "ebay" in searched
        assert "etsy" not in searched

    @pytest.mark.asyncio
    async def test_check_specific_urls(self, config_file: Path, tmp_path: Path) -> None:
        """Test checking specific URLs."""
        orchestrator = SearchOrchestrator(config_file)

        urls = ["https://example.com/item1", "https://example.com/item2"]

        with patch("src.ring_search.async_playwright") as mock_pw:
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=None)
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)

            orchestrator._process_listing = AsyncMock()

            result = await orchestrator.check_specific_urls(urls)

        assert "total" in result

    @pytest.mark.asyncio
    async def test_process_listing_scores_and_logs(self, config_file: Path) -> None:
        """Test that process_listing scores and logs."""
        orchestrator = SearchOrchestrator(config_file)

        from src.models import Listing

        listing = Listing(
            url="https://example.com/test",
            source="ebay",
            title="Gold Amethyst Pearl Ring",
            price="$100",
        )

        mock_page = AsyncMock()
        orchestrator.capture.capture = AsyncMock(return_value=None)

        await orchestrator._process_listing(mock_page, listing)

        assert len(orchestrator.logger.daily_results) == 1
        logged = orchestrator.logger.daily_results[0]
        assert logged.url == listing.url
        assert logged.confidence_score > 0

    @pytest.mark.asyncio
    async def test_process_listing_captures_screenshot_for_high(self, config_file: Path, tmp_path: Path) -> None:
        """Test that high confidence listings get screenshots."""
        orchestrator = SearchOrchestrator(config_file)

        from src.models import Listing

        # Create a listing that will score high
        listing = Listing(
            url="https://example.com/test",
            source="ebay",
            title="10K Yellow Gold Amethyst Seed Pearl Victorian Swirl Ring Size 7",
            price="$500",
            description="Beautiful antique ring",
        )

        mock_page = AsyncMock()
        mock_screenshot_path = tmp_path / "screenshot.png"
        orchestrator.capture.capture = AsyncMock(return_value=mock_screenshot_path)
        orchestrator.capture.copy_to_high_confidence = MagicMock(return_value=None)

        await orchestrator._process_listing(mock_page, listing)

        # Screenshot should have been captured
        orchestrator.capture.capture.assert_called_once()
        # High confidence should be copied
        orchestrator.capture.copy_to_high_confidence.assert_called_once()

    @pytest.mark.asyncio
    async def test_dedup_prevents_reprocessing(self, config_file: Path) -> None:
        """Test that duplicate URLs are not reprocessed."""
        orchestrator = SearchOrchestrator(config_file)

        url = "https://example.com/duplicate"

        # Mark as checked
        orchestrator.dedup.mark_checked(url)

        # Should not be new
        assert not orchestrator.dedup.is_new(url)

    def test_adapter_map_contains_all(self, config_file: Path) -> None:
        """Test that adapter map contains expected marketplaces."""
        orchestrator = SearchOrchestrator(config_file)

        expected = ["shopgoodwill", "ebay", "etsy", "craigslist"]
        for name in expected:
            assert name in orchestrator.ADAPTER_MAP
