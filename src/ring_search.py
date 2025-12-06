"""Main search orchestrator coordinating all components."""

import logging
from pathlib import Path
from typing import Any

import yaml
from playwright.async_api import Page, async_playwright

from src.adapters import (
    CraigslistAdapter,
    EbayAdapter,
    EtsyAdapter,
    MarketplaceAdapter,
    MercariAdapter,
    PoshmarkAdapter,
    RubyLaneAdapter,
    ShopGoodwillAdapter,
)
from src.capture import ScreenshotCapture
from src.dedup import DedupManager
from src.logger import SearchLogger
from src.models import Listing
from src.scoring import RelevanceScorer

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Coordinates search across multiple marketplaces."""

    ADAPTER_MAP: dict[str, type[MarketplaceAdapter]] = {
        "shopgoodwill": ShopGoodwillAdapter,
        "ebay": EbayAdapter,
        "etsy": EtsyAdapter,
        "craigslist": CraigslistAdapter,
        "rubylane": RubyLaneAdapter,
        "mercari": MercariAdapter,
        "poshmark": PoshmarkAdapter,
    }

    def __init__(self, config_path: Path):
        """Initialize orchestrator with configuration.

        Args:
            config_path: Path to config.yaml file.
        """
        self.config = self._load_config(config_path)
        self.config_path = config_path

        # Setup output directory
        output_dir = Path(self.config.get("output", {}).get("base_dir", "output"))
        logs_dir = output_dir / self.config.get("output", {}).get("logs_dir", "logs")

        # Initialize components
        self.dedup = DedupManager(logs_dir / "checked_links.txt")
        self.logger = SearchLogger(logs_dir)
        self.scorer = RelevanceScorer()
        self.capture = ScreenshotCapture(output_dir)

        # Rate limiting settings
        rate_config = self.config.get("rate_limiting", {})
        self.min_delay = rate_config.get("min_delay_seconds", 2.0)
        self.max_delay = rate_config.get("max_delay_seconds", 5.0)

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        """Load configuration from YAML file.

        Args:
            config_path: Path to config.yaml.

        Returns:
            Configuration dictionary.

        Raises:
            FileNotFoundError: If config file doesn't exist.
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            config: dict[str, Any] = yaml.safe_load(f)
            return config

    def _create_adapter(self, marketplace: dict[str, Any]) -> MarketplaceAdapter | None:
        """Create adapter for a marketplace configuration.

        Args:
            marketplace: Marketplace configuration dictionary.

        Returns:
            Configured adapter instance, or None if unknown marketplace.
        """
        name = marketplace.get("name", "").lower()

        if name not in self.ADAPTER_MAP:
            logger.warning(f"Unknown marketplace: {name}")
            return None

        adapter_class = self.ADAPTER_MAP[name]

        # Special handling for Craigslist (needs regions)
        if name == "craigslist":
            regions = marketplace.get("regions", CraigslistAdapter.DEFAULT_REGIONS)
            return CraigslistAdapter(
                regions=regions,
                min_delay=self.min_delay,
                max_delay=self.max_delay,
            )

        return adapter_class(
            min_delay=self.min_delay,
            max_delay=self.max_delay,
        )

    async def run_daily_search(self, headless: bool = True) -> dict[str, Any]:
        """Execute search across all configured marketplaces.

        Args:
            headless: Whether to run browser in headless mode.

        Returns:
            Statistics dictionary with search results.
        """
        logger.info("Starting daily ring search")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            try:
                # Check known leads first
                await self._check_known_leads(page)

                # Search each marketplace
                marketplaces = self.config.get("marketplaces", [])

                for marketplace in sorted(marketplaces, key=lambda m: m.get("priority", 99)):
                    if not marketplace.get("enabled", True):
                        logger.info(f"Skipping disabled marketplace: {marketplace['name']}")
                        continue

                    await self._search_marketplace(page, marketplace)

            finally:
                await browser.close()

        # Write daily summary
        self.logger.write_daily_summary()

        return self.logger.get_stats()

    async def _check_known_leads(self, page: Page) -> None:
        """Check known lead URLs first.

        Args:
            page: Playwright page instance.
        """
        known_leads = self.config.get("known_leads", [])

        if not known_leads:
            return

        logger.info(f"Checking {len(known_leads)} known leads")

        for lead in known_leads:
            url = lead.get("url")
            if not url:
                continue

            if not self.dedup.is_new(url):
                logger.debug(f"Known lead already checked: {url}")
                continue

            try:
                logger.info(f"Checking known lead: {url}")
                await page.goto(url, wait_until="domcontentloaded")

                # Create listing from page
                title_element = await page.query_selector("h1, title")
                title = ""
                if title_element:
                    title = await title_element.text_content() or ""
                    title = title.strip()

                listing = Listing(
                    url=url,
                    source="known_lead",
                    title=title or lead.get("note", "Known Lead"),
                    price=None,
                    description=None,
                    image_url=None,
                )

                await self._process_listing(page, listing)
                self.dedup.mark_checked(url)

            except Exception as e:
                logger.error(f"Error checking known lead {url}: {e}")

    async def _search_marketplace(self, page: Page, marketplace: dict[str, Any]) -> None:
        """Search a single marketplace.

        Args:
            page: Playwright page instance.
            marketplace: Marketplace configuration dictionary.
        """
        name = marketplace.get("name", "unknown")
        logger.info(f"Searching marketplace: {name}")

        adapter = self._create_adapter(marketplace)
        if adapter is None:
            return

        searches = marketplace.get("searches", [])
        if not searches:
            logger.warning(f"No search queries configured for {name}")
            return

        try:
            async for listing in adapter.search(page, searches):
                if self.dedup.is_new(listing.url):
                    await self._process_listing(page, listing)
                    self.dedup.mark_checked(listing.url)

        except Exception as e:
            logger.error(f"Error searching {name}: {e}")

    async def _process_listing(self, page: Page, listing: Listing) -> None:
        """Process a single listing: score, screenshot, log.

        Args:
            page: Playwright page instance.
            listing: The listing to process.
        """
        # Score the listing
        scored = self.scorer.score(listing)

        logger.info(f"[{scored.confidence.upper()}] {scored.score}/100 - {scored.title[:50]}...")

        # Capture screenshot for high/medium confidence
        screenshot = None
        if scored.confidence in ("high", "medium"):
            screenshot = await self.capture.capture(page, scored)

            # Copy high confidence to special folder
            if scored.confidence == "high" and screenshot:
                self.capture.copy_to_high_confidence(screenshot)

        # Log result
        self.logger.log_result(scored, screenshot=screenshot)

    async def check_specific_urls(self, urls: list[str], headless: bool = True) -> dict[str, Any]:
        """Check specific URLs without full marketplace search.

        Args:
            urls: List of URLs to check.
            headless: Whether to run browser in headless mode.

        Returns:
            Statistics dictionary.
        """
        logger.info(f"Checking {len(urls)} specific URLs")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            try:
                for url in urls:
                    if not self.dedup.is_new(url):
                        logger.info(f"URL already checked: {url}")
                        continue

                    try:
                        await page.goto(url, wait_until="domcontentloaded")

                        # Extract basic info
                        title_element = await page.query_selector("h1, title")
                        title = ""
                        if title_element:
                            title = await title_element.text_content() or ""
                            title = title.strip()

                        # Determine source from URL
                        source = "unknown"
                        for name in self.ADAPTER_MAP:
                            if name in url.lower():
                                source = name
                                break

                        listing = Listing(
                            url=url,
                            source=source,
                            title=title or url,
                            price=None,
                            description=None,
                            image_url=None,
                        )

                        await self._process_listing(page, listing)
                        self.dedup.mark_checked(url)

                    except Exception as e:
                        logger.error(f"Error checking URL {url}: {e}")

            finally:
                await browser.close()

        self.logger.write_daily_summary()
        return self.logger.get_stats()
