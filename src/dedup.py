"""URL deduplication manager with persistent storage."""

from pathlib import Path
from urllib.parse import urlparse


class DedupManager:
    """Manages URL deduplication with file-based persistence."""

    def __init__(self, log_path: Path):
        """Initialize dedup manager.

        Args:
            log_path: Path to the checked_links.txt file for persistence.
        """
        self.log_path = Path(log_path)
        self._cache: set[str] = set()
        self._load()

    def _load(self) -> None:
        """Load previously checked URLs from file."""
        if self.log_path.exists():
            with open(self.log_path) as f:
                for line in f:
                    url = line.strip()
                    if url:
                        self._cache.add(url)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by stripping query params and fragments.

        Args:
            url: The URL to normalize.

        Returns:
            Normalized URL with scheme, host, and path only.
        """
        parsed = urlparse(url)
        # Keep only scheme, netloc, and path
        # Strip trailing slashes for consistency
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def is_new(self, url: str) -> bool:
        """Check if URL has not been seen before.

        Args:
            url: The URL to check.

        Returns:
            True if URL is new (not in cache), False otherwise.
        """
        normalized = self._normalize_url(url)
        return normalized not in self._cache

    def mark_checked(self, url: str) -> None:
        """Mark URL as checked and persist to file.

        Args:
            url: The URL to mark as checked.
        """
        normalized = self._normalize_url(url)
        if normalized not in self._cache:
            self._cache.add(normalized)
            # Ensure parent directory exists
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a") as f:
                f.write(f"{normalized}\n")

    def count(self) -> int:
        """Return the number of checked URLs.

        Returns:
            Count of URLs in the cache.
        """
        return len(self._cache)

    def clear(self) -> None:
        """Clear the cache and delete the log file."""
        self._cache.clear()
        if self.log_path.exists():
            self.log_path.unlink()
