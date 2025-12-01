"""Data models for ring search automation."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Listing:
    """Raw listing from marketplace."""

    url: str
    source: str  # 'shopgoodwill', 'ebay', 'etsy', 'craigslist', etc.
    title: str
    price: str | None = None
    description: str | None = None
    image_url: str | None = None


@dataclass
class ScoredListing:
    """Listing with relevance score."""

    url: str
    source: str
    title: str
    price: str | None
    score: int  # 0-100
    confidence: Literal["high", "medium", "low"]
    matched_factors: list[str] = field(default_factory=list)
    description: str | None = None
    image_url: str | None = None


@dataclass
class LogEntry:
    """Entry in search_log.json."""

    timestamp: str  # ISO format
    url: str
    source: str
    title: str
    price: str | None
    confidence_score: int
    confidence: Literal["high", "medium", "low"]
    matched_factors: list[str]
    screenshot: str | None = None  # Path to screenshot
    status: str = "new"  # 'new', 'reviewed', 'dismissed'


@dataclass
class ScoringWeights:
    """Configurable scoring weights for ring matching criteria."""

    metal_yellow_gold: int = 20
    metal_10k: int = 10
    stone_amethyst: int = 25
    stone_purple: int = 15
    pearl_seed: int = 20
    pearl_any: int = 10
    design_swirl: int = 15
    design_floral: int = 5
    era_victorian: int = 10
    size_exact: int = 10  # Size 7
    size_close: int = 5  # Size 6-8
