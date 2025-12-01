"""Tests for search logger."""

import json
from pathlib import Path

from src.logger import SearchLogger
from src.models import ScoredListing


class TestSearchLogger:
    """Tests for SearchLogger class."""

    def test_init_creates_directory(self, tmp_path: Path) -> None:
        """Test that init creates logs directory."""
        logs_dir = tmp_path / "logs"
        logger = SearchLogger(logs_dir)

        assert logs_dir.exists()
        assert logger.search_log_path == logs_dir / "search_log.json"

    def test_log_result_creates_entry(self, tmp_path: Path) -> None:
        """Test that log_result creates LogEntry."""
        logger = SearchLogger(tmp_path)
        listing = ScoredListing(
            url="https://example.com/1",
            source="ebay",
            title="Test Ring",
            price="$100",
            score=75,
            confidence="high",
            matched_factors=["gold", "amethyst"],
        )

        entry = logger.log_result(listing)

        assert entry.url == listing.url
        assert entry.source == listing.source
        assert entry.confidence_score == 75
        assert entry.confidence == "high"
        assert entry.status == "new"

    def test_log_result_with_screenshot(self, tmp_path: Path) -> None:
        """Test logging result with screenshot path."""
        logger = SearchLogger(tmp_path)
        listing = ScoredListing(
            url="https://example.com/1",
            source="ebay",
            title="Test Ring",
            price="$100",
            score=75,
            confidence="high",
            matched_factors=["gold"],
        )
        screenshot = tmp_path / "screenshot.png"

        entry = logger.log_result(listing, screenshot=screenshot)

        assert entry.screenshot == str(screenshot)

    def test_log_result_appends_to_daily_results(self, tmp_path: Path) -> None:
        """Test that results are tracked in daily_results."""
        logger = SearchLogger(tmp_path)

        for i in range(3):
            listing = ScoredListing(
                url=f"https://example.com/{i}",
                source="ebay",
                title=f"Ring {i}",
                price="$100",
                score=50,
                confidence="medium",
                matched_factors=["gold"],
            )
            logger.log_result(listing)

        assert len(logger.daily_results) == 3

    def test_json_log_appends(self, tmp_path: Path) -> None:
        """Test that JSON log file appends entries."""
        logger = SearchLogger(tmp_path)

        # Log multiple entries
        for i in range(3):
            listing = ScoredListing(
                url=f"https://example.com/{i}",
                source="etsy",
                title=f"Ring {i}",
                price="$100",
                score=50,
                confidence="medium",
                matched_factors=["gold"],
            )
            logger.log_result(listing)

        # Read JSON file
        with open(logger.search_log_path) as f:
            entries = json.load(f)

        assert len(entries) == 3
        assert entries[0]["url"] == "https://example.com/0"
        assert entries[2]["url"] == "https://example.com/2"

    def test_json_log_handles_existing_file(self, tmp_path: Path) -> None:
        """Test appending to existing JSON log."""
        # Create initial log
        logger1 = SearchLogger(tmp_path)
        listing1 = ScoredListing(
            url="https://example.com/1",
            source="ebay",
            title="Ring 1",
            price="$100",
            score=50,
            confidence="medium",
            matched_factors=["gold"],
        )
        logger1.log_result(listing1)

        # Create new logger and add more
        logger2 = SearchLogger(tmp_path)
        listing2 = ScoredListing(
            url="https://example.com/2",
            source="etsy",
            title="Ring 2",
            price="$200",
            score=60,
            confidence="medium",
            matched_factors=["pearl"],
        )
        logger2.log_result(listing2)

        # Check combined results
        with open(logger2.search_log_path) as f:
            entries = json.load(f)

        assert len(entries) == 2

    def test_write_daily_summary(self, tmp_path: Path) -> None:
        """Test daily summary generation."""
        logger = SearchLogger(tmp_path)

        # Add various confidence levels
        listings = [
            ("High match", 80, "high"),
            ("Medium match", 50, "medium"),
            ("Low match", 20, "low"),
        ]

        for title, score, conf in listings:
            listing = ScoredListing(
                url=f"https://example.com/{title}",
                source="ebay",
                title=title,
                price="$100",
                score=score,
                confidence=conf,
                matched_factors=["gold"],
            )
            logger.log_result(listing)

        summary_path = logger.write_daily_summary()

        assert summary_path.exists()
        content = summary_path.read_text()

        assert "Ring Search Daily Summary" in content
        assert "High Confidence Matches" in content
        assert "Medium Confidence Matches" in content
        assert "High match" in content
        assert "**Total Listings Checked:** 3" in content

    def test_write_daily_summary_no_results(self, tmp_path: Path) -> None:
        """Test summary with no results."""
        logger = SearchLogger(tmp_path)
        summary_path = logger.write_daily_summary()

        assert summary_path.exists()
        content = summary_path.read_text()
        assert "**Total Listings Checked:** 0" in content

    def test_get_stats(self, tmp_path: Path) -> None:
        """Test statistics calculation."""
        logger = SearchLogger(tmp_path)

        # Add mixed results
        results = [
            ("high", "ebay"),
            ("high", "etsy"),
            ("medium", "ebay"),
            ("low", "shopgoodwill"),
        ]

        for conf, source in results:
            listing = ScoredListing(
                url=f"https://example.com/{conf}_{source}",
                source=source,
                title="Test",
                price="$100",
                score={"high": 80, "medium": 50, "low": 20}[conf],
                confidence=conf,
                matched_factors=["gold"],
            )
            logger.log_result(listing)

        stats = logger.get_stats()

        assert stats["total"] == 4
        assert stats["high"] == 2
        assert stats["medium"] == 1
        assert stats["low"] == 1
        assert set(stats["sources"]) == {"ebay", "etsy", "shopgoodwill"}

    def test_clear_daily_results(self, tmp_path: Path) -> None:
        """Test clearing daily results."""
        logger = SearchLogger(tmp_path)

        # Add some results
        listing = ScoredListing(
            url="https://example.com/1",
            source="ebay",
            title="Test",
            price="$100",
            score=50,
            confidence="medium",
            matched_factors=["gold"],
        )
        logger.log_result(listing)
        assert len(logger.daily_results) == 1

        logger.clear_daily_results()
        assert len(logger.daily_results) == 0

    def test_summary_sources_breakdown(self, tmp_path: Path) -> None:
        """Test that summary includes source breakdown."""
        logger = SearchLogger(tmp_path)

        # Add results from different sources
        for source in ["ebay", "etsy", "shopgoodwill", "craigslist_indianapolis"]:
            listing = ScoredListing(
                url=f"https://example.com/{source}",
                source=source,
                title="Test Ring",
                price="$100",
                score=50,
                confidence="medium",
                matched_factors=["gold"],
            )
            logger.log_result(listing)

        summary_path = logger.write_daily_summary()
        content = summary_path.read_text()

        assert "Sources Breakdown" in content
        assert "**ebay:**" in content
        assert "**etsy:**" in content

    def test_format_long_title(self, tmp_path: Path) -> None:
        """Test that long titles are truncated in summary."""
        logger = SearchLogger(tmp_path)

        listing = ScoredListing(
            url="https://example.com/1",
            source="ebay",
            title="A" * 100,  # Very long title
            price="$100",
            score=80,
            confidence="high",
            matched_factors=["gold"],
        )
        logger.log_result(listing)

        summary_path = logger.write_daily_summary()
        content = summary_path.read_text()

        # Title should be truncated
        assert "..." in content
