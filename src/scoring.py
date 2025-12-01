"""Relevance scoring engine for ring matching criteria."""

from typing import Literal

from src.models import Listing, ScoredListing, ScoringWeights


class RelevanceScorer:
    """Scores listings based on match criteria for the target ring."""

    THRESHOLDS = {"high": 70, "medium": 40}

    def __init__(self, weights: ScoringWeights | None = None):
        """Initialize scorer with optional custom weights.

        Args:
            weights: Custom scoring weights. Uses defaults if None.
        """
        self.weights = weights or ScoringWeights()

    def score(self, listing: Listing) -> ScoredListing:
        """Score a listing based on match criteria.

        Args:
            listing: The listing to score.

        Returns:
            ScoredListing with score, confidence level, and matched factors.
        """
        score = 0
        factors: list[str] = []

        # Combine title and description for analysis
        text = f"{listing.title} {listing.description or ''}".lower()

        # Metal analysis
        score, factors = self._score_metal(text, score, factors)

        # Stone analysis
        score, factors = self._score_stones(text, score, factors)

        # Pearl analysis
        score, factors = self._score_pearls(text, score, factors)

        # Design analysis
        score, factors = self._score_design(text, score, factors)

        # Era/style analysis
        score, factors = self._score_era(text, score, factors)

        # Size analysis
        score, factors = self._score_size(text, score, factors)

        # Cap score at 100
        score = min(score, 100)

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

    def _score_metal(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on metal type."""
        if "yellow gold" in text or ("gold" in text and "white" not in text and "rose" not in text):
            score += self.weights.metal_yellow_gold
            factors.append("gold")

        if "10k" in text or "10 karat" in text or "10kt" in text:
            score += self.weights.metal_10k
            factors.append("10k")
        elif "14k" in text or "9k" in text:
            # Acceptable alternatives get partial credit
            score += self.weights.metal_10k // 2
            factors.append("gold karat")

        return score, factors

    def _score_stones(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on stone type."""
        if "amethyst" in text:
            score += self.weights.stone_amethyst
            factors.append("amethyst")
        elif "purple" in text or "magenta" in text or "raspberry" in text:
            score += self.weights.stone_purple
            factors.append("purple stone")

        return score, factors

    def _score_pearls(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on pearl presence."""
        if "seed pearl" in text:
            score += self.weights.pearl_seed
            factors.append("seed pearl")
        elif "pearl" in text:
            score += self.weights.pearl_any
            factors.append("pearl")

        return score, factors

    def _score_design(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on design elements."""
        swirl_keywords = ["swirl", "infinity", "figure-8", "figure 8", "flowing", "cluster"]
        if any(kw in text for kw in swirl_keywords):
            score += self.weights.design_swirl
            factors.append("swirl design")
        elif "floral" in text or "flower" in text:
            score += self.weights.design_floral
            factors.append("floral design")

        return score, factors

    def _score_era(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on era/style."""
        era_keywords = [
            "victorian",
            "edwardian",
            "antique",
            "vintage",
            "art nouveau",
            "estate",
        ]
        if any(kw in text for kw in era_keywords):
            score += self.weights.era_victorian
            factors.append("vintage era")

        return score, factors

    def _score_size(self, text: str, score: int, factors: list[str]) -> tuple[int, list[str]]:
        """Score based on ring size."""
        # Look for size 7 exactly
        if "size 7" in text or "size: 7" in text or "sz 7" in text:
            score += self.weights.size_exact
            factors.append("size 7")
        # Look for sizes 6-8 (close matches)
        elif any(f"size {s}" in text or f"sz {s}" in text for s in ["6", "6.5", "7.5", "8"]):
            score += self.weights.size_close
            factors.append("size close")

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
