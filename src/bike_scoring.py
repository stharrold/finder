"""Relevance scoring engine for Trek Allant+ 7S bike matching criteria."""

import re
from typing import Literal

from src.models import BikeScoringWeights, Listing, ScoredListing


class BikeRelevanceScorer:
    """Scores listings based on match criteria for Trek Allant+ 7S."""

    THRESHOLDS = {"high": 70, "medium": 40}

    def __init__(self, weights: BikeScoringWeights | None = None):
        """Initialize scorer with optional custom weights.

        Args:
            weights: Custom scoring weights. Uses defaults if None.
        """
        self.weights = weights or BikeScoringWeights()

    def score(self, listing: Listing) -> ScoredListing:
        """Score a listing based on Trek Allant+ 7S match criteria.

        Args:
            listing: The listing to score.

        Returns:
            ScoredListing with score, confidence level, and matched factors.
        """
        score = 0
        factors: list[str] = []

        # Combine title and description for analysis
        text = f"{listing.title} {listing.description or ''}".lower()

        # Model analysis (most important)
        score, factors = self._score_model(text, score, factors)

        # Class analysis (Class 3 vs Class 1)
        score, factors = self._score_class(text, score, factors)

        # Battery analysis
        score, factors = self._score_battery(text, score, factors)

        # Range extender analysis
        score, factors = self._score_range_extender(text, score, factors)

        # Frame size analysis
        score, factors = self._score_frame(text, score, factors)

        # Cap score at 100, floor at 0
        score = max(0, min(score, 100))

        # Classify confidence
        confidence = self._classify_confidence(score)

        return ScoredListing(
            url=listing.url,
            source=listing.source,
            title=listing.title,
            price=listing.price,
            score=score,
            confidence=confidence,
            matched_factors=factors,
            description=listing.description,
            image_url=listing.image_url,
        )

    def _score_model(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on model identification.

        Priority:
        1. Allant+ 7S (exact match) - full points
        2. Allant+ 7 (wrong model) - penalty
        3. Generic Allant+ - partial points
        """
        # Check for exact Allant+ 7S match (various formats)
        allant_7s_patterns = [
            r"allant\+?\s*7s",
            r"allant\s+plus\s+7s",
            r"allant\+\s*7\s*s",
        ]
        if any(re.search(pattern, text) for pattern in allant_7s_patterns):
            score += self.weights.model_allant_7s
            factors.append("model: Allant+ 7S")
            return score, factors

        # Check for Allant+ 7 (wrong model - Class 1)
        # Note: text is already lowercased (line 35), so (?!\s*s) correctly excludes "7s"
        allant_7_patterns = [
            r"allant\+?\s*7(?!\s*s)",  # Allant+ 7 but not 7S
            r"allant\s+plus\s+7(?!\s*s)",
        ]
        if any(re.search(pattern, text) for pattern in allant_7_patterns):
            # This is likely the Class 1 model - apply penalty
            score += self.weights.model_allant_7_penalty
            factors.append("model: Allant+ 7 (WRONG - Class 1)")
            return score, factors

        # Check for generic Allant+ mention
        if "allant+" in text or "allant plus" in text or "allant +" in text:
            score += self.weights.model_allant_plus
            factors.append("model: Allant+ (generic)")

        return score, factors

    def _score_class(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on e-bike class (Class 3 = 28mph, Class 1 = 20mph)."""
        # Check for Class 3 indicators
        class_3_patterns = [
            r"class\s*3",
            r"28\s*mph",
            r"28mph",
            r"speed\s+pedelec",
        ]
        if any(re.search(pattern, text) for pattern in class_3_patterns):
            score += self.weights.class_3
            factors.append("class: 3 (28 mph)")
            return score, factors

        # Check for Class 1 indicators (penalty)
        class_1_patterns = [
            r"class\s*1",
            r"20\s*mph",
            r"20mph",
        ]
        if any(re.search(pattern, text) for pattern in class_1_patterns):
            score += self.weights.class_1_penalty
            factors.append("class: 1 (20 mph) - REJECT")

        return score, factors

    def _score_battery(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on battery capacity (625Wh required, 500Wh insufficient)."""
        # Check for 625Wh battery
        if "625wh" in text or "625 wh" in text:
            score += self.weights.battery_625wh
            factors.append("battery: 625Wh")
            return score, factors

        # Check for 500Wh battery (penalty - insufficient)
        if "500wh" in text or "500 wh" in text:
            score += self.weights.battery_500wh_penalty
            factors.append("battery: 500Wh (insufficient)")

        return score, factors

    def _score_range_extender(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on range extender presence."""
        range_extender_patterns = [
            r"range\s*extender",
            r"second\s*battery",
            r"dual\s*battery",
            r"2\s*batteries",
            r"two\s*batteries",
            r"extra\s*battery",
            r"additional\s*battery",
        ]
        if any(re.search(pattern, text) for pattern in range_extender_patterns):
            score += self.weights.range_extender
            factors.append("range extender")

        return score, factors

    def _score_frame(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on frame size (Large/L preferred)."""
        # Check for Large frame
        # Note: Patterns require explicit size/frame context to avoid false positives
        # Text is already lowercased, so patterns only need lowercase
        large_patterns = [
            r"\blarge\b",  # Word "large" with word boundaries
            r"size[:\s]+l(?:\b|\s|$|,)",  # "size: L" or "size L" with proper termination
            r"frame[:\s]+l(?:\b|\s|$|,)",  # "frame: L" or "frame L" with proper termination
            r"size[:\s]+large",  # "size: large" or "size large"
            r"\(l\)",  # "(L)" common in listings
            r"5[5-8]\s*cm",  # 55-58cm = Large frame sizes
        ]
        if any(re.search(pattern, text) for pattern in large_patterns):
            score += self.weights.frame_large
            factors.append("frame: Large")

        return score, factors

    def _classify_confidence(self, score: int) -> Literal["high", "medium", "low"]:
        """Classify confidence level based on score.

        Args:
            score: The numeric score (0-100).

        Returns:
            Confidence level: 'high', 'medium', or 'low'.
        """
        if score >= self.THRESHOLDS["high"]:
            return "high"
        elif score >= self.THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"
