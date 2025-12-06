"""Tests for CLI interface."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli import check_urls, main, run_search, setup_logging, show_report


class TestCLI:
    """Tests for CLI commands."""

    def test_main_no_command(self) -> None:
        """Test that main prints help with no command."""
        with patch.object(sys, "argv", ["ring-search"]):
            result = main()
        assert result == 1

    def test_main_help(self, capsys) -> None:
        """Test help output."""
        with patch.object(sys, "argv", ["ring-search", "--help"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0

        captured = capsys.readouterr()
        assert "Marketplace Search Automation" in captured.out
        assert "run" in captured.out
        assert "check-urls" in captured.out

    def test_setup_logging_default(self) -> None:
        """Test default logging setup."""
        import logging

        # Reset logging to test
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        setup_logging(verbose=False)
        # Verify handlers were added
        assert len(logging.root.handlers) > 0

    def test_setup_logging_verbose(self) -> None:
        """Test verbose logging setup."""
        import logging

        # Reset logging to test
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        setup_logging(verbose=True)
        # Verify handlers were added
        assert len(logging.root.handlers) > 0

    @pytest.fixture
    def config_file(self, tmp_path: Path) -> Path:
        """Create a test config file."""
        config = tmp_path / "config.yaml"
        config.write_text("""
marketplaces:
  - name: shopgoodwill
    enabled: true
    priority: 1
    searches:
      - "test"

rate_limiting:
  min_delay_seconds: 0.01
  max_delay_seconds: 0.02

output:
  base_dir: output
  logs_dir: logs
""")
        return config

    def test_run_search_missing_config(self, tmp_path: Path) -> None:
        """Test run_search with missing config."""
        import argparse

        args = argparse.Namespace(
            config=str(tmp_path / "nonexistent.yaml"),
            headed=False,
        )

        result = run_search(args)
        assert result == 1

    def test_run_search_success(self, config_file: Path) -> None:
        """Test successful run_search."""
        import argparse

        args = argparse.Namespace(
            config=str(config_file),
            headed=False,
        )

        with patch("src.cli.SearchOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.run_daily_search = AsyncMock(
                return_value={
                    "total": 10,
                    "high": 1,
                    "medium": 3,
                    "low": 6,
                    "sources": ["shopgoodwill"],
                }
            )
            mock_orch.return_value = mock_instance

            result = run_search(args)

        assert result == 0
        mock_instance.run_daily_search.assert_called_once()

    def test_check_urls_missing_file(self, config_file: Path, tmp_path: Path) -> None:
        """Test check_urls with missing URL file."""
        import argparse

        args = argparse.Namespace(
            config=str(config_file),
            urls_file=str(tmp_path / "nonexistent.txt"),
            headed=False,
        )

        result = check_urls(args)
        assert result == 1

    def test_check_urls_empty_file(self, config_file: Path, tmp_path: Path) -> None:
        """Test check_urls with empty URL file."""
        import argparse

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("")

        args = argparse.Namespace(
            config=str(config_file),
            urls_file=str(urls_file),
            headed=False,
        )

        result = check_urls(args)
        assert result == 1

    def test_check_urls_success(self, config_file: Path, tmp_path: Path) -> None:
        """Test successful check_urls."""
        import argparse

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://example.com/1\nhttps://example.com/2\n")

        args = argparse.Namespace(
            config=str(config_file),
            urls_file=str(urls_file),
            headed=False,
        )

        with patch("src.cli.SearchOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.check_specific_urls = AsyncMock(
                return_value={
                    "total": 2,
                    "high": 0,
                    "medium": 1,
                    "low": 1,
                    "sources": ["unknown"],
                }
            )
            mock_orch.return_value = mock_instance

            result = check_urls(args)

        assert result == 0

    def test_check_urls_skips_comments(self, config_file: Path, tmp_path: Path) -> None:
        """Test that check_urls skips comment lines."""
        import argparse

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("# Comment line\nhttps://example.com/1\n\n# Another comment\n")

        args = argparse.Namespace(
            config=str(config_file),
            urls_file=str(urls_file),
            headed=False,
        )

        with patch("src.cli.SearchOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.check_specific_urls = AsyncMock(
                return_value={
                    "total": 1,
                    "high": 0,
                    "medium": 0,
                    "low": 1,
                    "sources": [],
                }
            )
            mock_orch.return_value = mock_instance

            result = check_urls(args)

        assert result == 0
        # Should only have one URL (not comments)
        call_args = mock_instance.check_specific_urls.call_args
        assert len(call_args[0][0]) == 1

    def test_show_report_no_summaries(self, config_file: Path, tmp_path: Path) -> None:
        """Test show_report with no summary files."""
        import argparse

        args = argparse.Namespace(
            config=str(config_file),
            date=None,
        )

        with patch("src.cli.SearchOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.config = {"output": {"base_dir": str(tmp_path), "logs_dir": "logs"}}
            mock_orch.return_value = mock_instance

            # Create empty logs dir
            (tmp_path / "logs").mkdir()

            result = show_report(args)

        assert result == 1

    def test_show_report_with_date(self, config_file: Path, tmp_path: Path) -> None:
        """Test show_report with specific date."""
        import argparse

        args = argparse.Namespace(
            config=str(config_file),
            date="2024-11-30",
        )

        with patch("src.cli.SearchOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.config = {"output": {"base_dir": str(tmp_path), "logs_dir": "logs"}}
            mock_orch.return_value = mock_instance

            # Create summary file
            logs_dir = tmp_path / "logs"
            logs_dir.mkdir()
            summary = logs_dir / "daily_summary_2024-11-30.md"
            summary.write_text("# Test Summary")

            result = show_report(args)

        assert result == 0

    def test_show_report_latest(self, config_file: Path, tmp_path: Path) -> None:
        """Test show_report finds latest summary."""
        import argparse

        args = argparse.Namespace(
            config=str(config_file),
            date=None,
        )

        with patch("src.cli.SearchOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.config = {"output": {"base_dir": str(tmp_path), "logs_dir": "logs"}}
            mock_orch.return_value = mock_instance

            # Create multiple summary files
            logs_dir = tmp_path / "logs"
            logs_dir.mkdir()
            (logs_dir / "daily_summary_2024-11-28.md").write_text("# Old")
            (logs_dir / "daily_summary_2024-11-30.md").write_text("# Latest Summary")

            result = show_report(args)

        assert result == 0
