"""Command-line interface for ring search automation."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.ring_search import SearchOrchestrator


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_search(args: argparse.Namespace) -> int:
    """Execute daily search command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        orchestrator = SearchOrchestrator(config_path)
        stats = asyncio.run(orchestrator.run_daily_search(headless=not args.headed))

        print("\n" + "=" * 50)
        print("Search Complete!")
        print("=" * 50)
        print(f"Total listings checked: {stats['total']}")
        print(f"  High confidence:   {stats['high']}")
        print(f"  Medium confidence: {stats['medium']}")
        print(f"  Low confidence:    {stats['low']}")
        print(f"Sources searched: {', '.join(stats['sources'])}")

        if stats["high"] > 0:
            print("\n⚠️  HIGH CONFIDENCE MATCHES FOUND! Check output/potential_matches/high_confidence/")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logging.exception("Error during search")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def check_urls(args: argparse.Namespace) -> int:
    """Check specific URLs command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        # Read URLs from file
        urls_path = Path(args.urls_file)
        if not urls_path.exists():
            print(f"Error: File not found: {urls_path}", file=sys.stderr)
            return 1

        urls = [
            line.strip() for line in urls_path.read_text().splitlines() if line.strip() and not line.startswith("#")
        ]

        if not urls:
            print("No URLs found in file", file=sys.stderr)
            return 1

        # Validate URL format
        invalid_urls = [url for url in urls if not url.startswith(("http://", "https://"))]
        if invalid_urls:
            print(f"Warning: {len(invalid_urls)} URLs don't start with http(s)://", file=sys.stderr)
            for url in invalid_urls[:3]:
                print(f"  - {url}", file=sys.stderr)
            if len(invalid_urls) > 3:
                print(f"  ... and {len(invalid_urls) - 3} more", file=sys.stderr)

        print(f"Checking {len(urls)} URLs...")

        orchestrator = SearchOrchestrator(config_path)
        stats = asyncio.run(orchestrator.check_specific_urls(urls, headless=not args.headed))

        print("\n" + "=" * 50)
        print("URL Check Complete!")
        print("=" * 50)
        print(f"URLs checked: {stats['total']}")
        print(f"  High confidence:   {stats['high']}")
        print(f"  Medium confidence: {stats['medium']}")
        print(f"  Low confidence:    {stats['low']}")

        return 0

    except Exception as e:
        logging.exception("Error checking URLs")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def show_report(args: argparse.Namespace) -> int:
    """Show report command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        orchestrator = SearchOrchestrator(config_path)

        # Find summary file
        output_dir = Path(orchestrator.config.get("output", {}).get("base_dir", "output"))
        logs_dir = output_dir / orchestrator.config.get("output", {}).get("logs_dir", "logs")

        if args.date:
            summary_path = logs_dir / f"daily_summary_{args.date}.md"
        else:
            # Find most recent summary
            summaries = sorted(logs_dir.glob("daily_summary_*.md"), reverse=True)
            if not summaries:
                print("No summary files found", file=sys.stderr)
                return 1
            summary_path = summaries[0]

        if not summary_path.exists():
            print(f"Summary not found: {summary_path}", file=sys.stderr)
            return 1

        print(summary_path.read_text())
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for CLI.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Ring Search Automation - Find lost antique ring across marketplaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ring-search run --config config.yaml
  ring-search check-urls urls.txt --config config.yaml
  ring-search report --date 2024-11-30
        """,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run daily search across all marketplaces",
    )
    run_parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible)",
    )
    run_parser.set_defaults(func=run_search)

    # Check URLs command
    urls_parser = subparsers.add_parser(
        "check-urls",
        help="Check specific URLs from a file",
    )
    urls_parser.add_argument(
        "urls_file",
        help="Path to file containing URLs (one per line)",
    )
    urls_parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible)",
    )
    urls_parser.set_defaults(func=check_urls)

    # Report command
    report_parser = subparsers.add_parser(
        "report",
        help="Show daily summary report",
    )
    report_parser.add_argument(
        "--date",
        help="Date to show report for (YYYY-MM-DD format)",
    )
    report_parser.set_defaults(func=show_report)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
