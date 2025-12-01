"""Tests for URL deduplication manager."""

from pathlib import Path

from src.dedup import DedupManager


class TestDedupManager:
    """Tests for DedupManager class."""

    def test_new_url_returns_true(self, tmp_path: Path) -> None:
        """Test that a new URL returns True for is_new."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        assert dedup.is_new("https://example.com/listing/123")

    def test_duplicate_url_returns_false(self, tmp_path: Path) -> None:
        """Test that a duplicate URL returns False for is_new."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        url = "https://example.com/listing/123"
        dedup.mark_checked(url)
        assert not dedup.is_new(url)

    def test_url_normalization_strips_query_params(self, tmp_path: Path) -> None:
        """Test that query params are stripped for dedup check."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        dedup.mark_checked("https://example.com/item/456?tracking=abc")
        # Same URL without query params should be detected as duplicate
        assert not dedup.is_new("https://example.com/item/456")
        # Same URL with different query params should also be duplicate
        assert not dedup.is_new("https://example.com/item/456?ref=search")

    def test_url_normalization_strips_fragments(self, tmp_path: Path) -> None:
        """Test that fragments are stripped for dedup check."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        dedup.mark_checked("https://example.com/item/789#details")
        assert not dedup.is_new("https://example.com/item/789")
        assert not dedup.is_new("https://example.com/item/789#photos")

    def test_url_normalization_strips_trailing_slash(self, tmp_path: Path) -> None:
        """Test that trailing slashes are normalized."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        dedup.mark_checked("https://example.com/item/")
        assert not dedup.is_new("https://example.com/item")

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """Test that state persists when creating new instance."""
        log_path = tmp_path / "checked_links.txt"

        # First instance marks URL
        dedup1 = DedupManager(log_path)
        dedup1.mark_checked("https://example.com/persisted")

        # Second instance should see it
        dedup2 = DedupManager(log_path)
        assert not dedup2.is_new("https://example.com/persisted")

    def test_count_returns_correct_number(self, tmp_path: Path) -> None:
        """Test that count returns correct number of checked URLs."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        assert dedup.count() == 0

        dedup.mark_checked("https://example.com/1")
        dedup.mark_checked("https://example.com/2")
        dedup.mark_checked("https://example.com/3")

        assert dedup.count() == 3

    def test_mark_checked_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that mark_checked creates parent directories."""
        log_path = tmp_path / "nested" / "dirs" / "checked_links.txt"
        dedup = DedupManager(log_path)

        dedup.mark_checked("https://example.com/test")
        assert log_path.exists()

    def test_clear_removes_all_entries(self, tmp_path: Path) -> None:
        """Test that clear removes all entries and deletes file."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        dedup.mark_checked("https://example.com/1")
        dedup.mark_checked("https://example.com/2")
        assert dedup.count() == 2
        assert log_path.exists()

        dedup.clear()
        assert dedup.count() == 0
        assert not log_path.exists()
        assert dedup.is_new("https://example.com/1")

    def test_different_paths_are_unique(self, tmp_path: Path) -> None:
        """Test that different paths are treated as unique URLs."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        dedup.mark_checked("https://example.com/item/1")
        assert dedup.is_new("https://example.com/item/2")
        assert dedup.is_new("https://example.com/other/1")

    def test_different_hosts_are_unique(self, tmp_path: Path) -> None:
        """Test that different hosts are treated as unique URLs."""
        log_path = tmp_path / "checked_links.txt"
        dedup = DedupManager(log_path)

        dedup.mark_checked("https://ebay.com/item/123")
        assert dedup.is_new("https://etsy.com/item/123")
