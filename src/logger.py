"""Multi-format logging for ring search results."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models import LogEntry, ScoredListing

logger = logging.getLogger(__name__)


class SearchLogger:
    """Multi-format logging: JSON, Markdown summary, checked URLs."""

    def __init__(self, logs_dir: Path):
        """Initialize search logger.

        Args:
            logs_dir: Directory for log files.
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.search_log_path = self.logs_dir / "search_log.json"
        self.daily_results: list[LogEntry] = []

    def log_result(
        self,
        listing: ScoredListing,
        screenshot: Path | None = None,
    ) -> LogEntry:
        """Log a search result.

        Args:
            listing: The scored listing to log.
            screenshot: Path to screenshot if captured.

        Returns:
            The created LogEntry.
        """
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            url=listing.url,
            source=listing.source,
            title=listing.title,
            price=listing.price,
            confidence_score=listing.score,
            confidence=listing.confidence,
            matched_factors=listing.matched_factors,
            screenshot=str(screenshot) if screenshot else None,
            status="new",
        )

        self.daily_results.append(entry)
        self._append_to_json(entry)

        return entry

    def _append_to_json(self, entry: LogEntry) -> None:
        """Append entry to JSON log file.

        Args:
            entry: The log entry to append.
        """
        try:
            # Read existing entries
            entries: list[dict[str, Any]] = []
            if self.search_log_path.exists():
                with open(self.search_log_path) as f:
                    try:
                        entries = json.load(f)
                    except json.JSONDecodeError:
                        entries = []

            # Append new entry
            entries.append(
                {
                    "timestamp": entry.timestamp,
                    "url": entry.url,
                    "source": entry.source,
                    "title": entry.title,
                    "price": entry.price,
                    "confidence_score": entry.confidence_score,
                    "confidence": entry.confidence,
                    "matched_factors": entry.matched_factors,
                    "screenshot": entry.screenshot,
                    "status": entry.status,
                }
            )

            # Write back
            with open(self.search_log_path, "w") as f:
                json.dump(entries, f, indent=2)

        except Exception as e:
            logger.error(f"Error writing to JSON log: {e}")

    def write_daily_summary(self) -> Path:
        """Generate Markdown summary of today's search.

        Returns:
            Path to the summary file.
        """
        date = datetime.now().strftime("%Y-%m-%d")
        summary_path = self.logs_dir / f"daily_summary_{date}.md"

        high = [r for r in self.daily_results if r.confidence == "high"]
        medium = [r for r in self.daily_results if r.confidence == "medium"]
        low = [r for r in self.daily_results if r.confidence == "low"]

        content = self._render_summary(date, high, medium, low)
        summary_path.write_text(content)

        logger.info(f"Daily summary written: {summary_path}")
        return summary_path

    def _render_summary(
        self,
        date: str,
        high: list[LogEntry],
        medium: list[LogEntry],
        low: list[LogEntry],
    ) -> str:
        """Render Markdown summary content.

        Args:
            date: Date string for the summary.
            high: High confidence results.
            medium: Medium confidence results.
            low: Low confidence results.

        Returns:
            Markdown content string.
        """
        total = len(high) + len(medium) + len(low)

        lines = [
            f"# Ring Search Daily Summary - {date}",
            "",
            "## Overview",
            "",
            f"- **Total Listings Checked:** {total}",
            f"- **High Confidence:** {len(high)}",
            f"- **Medium Confidence:** {len(medium)}",
            f"- **Low Confidence:** {len(low)}",
            "",
        ]

        if high:
            lines.extend(
                [
                    "## High Confidence Matches (Score ≥70)",
                    "",
                    "**Action Required:** Review these listings immediately!",
                    "",
                ]
            )
            for entry in high:
                lines.extend(self._format_entry(entry))

        if medium:
            lines.extend(
                [
                    "## Medium Confidence Matches (Score 40-69)",
                    "",
                    "Worth reviewing when time permits.",
                    "",
                ]
            )
            for entry in medium:
                lines.extend(self._format_entry(entry))

        if low:
            lines.extend(
                [
                    "## Low Confidence Matches (Score <40)",
                    "",
                    f"*{len(low)} listings checked but unlikely to match.*",
                    "",
                ]
            )

        # Sources breakdown
        sources: dict[str, int] = {}
        for entry in self.daily_results:
            source = entry.source.split("_")[0]  # Group craigslist regions
            sources[source] = sources.get(source, 0) + 1

        lines.extend(
            [
                "## Sources Breakdown",
                "",
            ]
        )
        for source, count in sorted(sources.items(), key=lambda x: -x[1]):
            lines.append(f"- **{source}:** {count} listings")

        lines.extend(
            [
                "",
                "---",
                f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ]
        )

        return "\n".join(lines)

    def _format_entry(self, entry: LogEntry) -> list[str]:
        """Format a single log entry for Markdown.

        Args:
            entry: The log entry to format.

        Returns:
            List of Markdown lines.
        """
        lines = [
            f"### [{entry.title[:60]}...]({entry.url})"
            if len(entry.title) > 60
            else f"### [{entry.title}]({entry.url})",
            "",
            f"- **Source:** {entry.source}",
            f"- **Price:** {entry.price or 'N/A'}",
            f"- **Score:** {entry.confidence_score}/100",
            f"- **Factors:** {', '.join(entry.matched_factors)}",
        ]

        if entry.screenshot:
            lines.append(f"- **Screenshot:** `{entry.screenshot}`")

        lines.append("")
        return lines

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about logged results.

        Returns:
            Dictionary with statistics.
        """
        high = sum(1 for r in self.daily_results if r.confidence == "high")
        medium = sum(1 for r in self.daily_results if r.confidence == "medium")
        low = sum(1 for r in self.daily_results if r.confidence == "low")

        return {
            "total": len(self.daily_results),
            "high": high,
            "medium": medium,
            "low": low,
            "sources": list(set(r.source for r in self.daily_results)),
        }

    def clear_daily_results(self) -> None:
        """Clear daily results for new search session."""
        self.daily_results.clear()
