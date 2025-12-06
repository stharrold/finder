"""Tests for bike relevance scoring engine."""

import pytest

from src.bike_scoring import BikeRelevanceScorer
from src.models import BikeScoringWeights, Listing


@pytest.fixture
def scorer() -> BikeRelevanceScorer:
    """Create a scorer with default weights."""
    return BikeRelevanceScorer()


@pytest.fixture
def custom_scorer() -> BikeRelevanceScorer:
    """Create a scorer with custom weights."""
    weights = BikeScoringWeights(
        model_allant_7s=50,
        class_3=25,
        battery_625wh=25,
    )
    return BikeRelevanceScorer(weights=weights)


class TestModelScoring:
    """Tests for model identification scoring."""

    def test_exact_allant_7s_match(self, scorer: BikeRelevanceScorer):
        """Test scoring for exact Allant+ 7S match."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Electric Bike 2024",
        )
        result = scorer.score(listing)
        assert "model: Allant+ 7S" in result.matched_factors
        assert result.score >= 40  # At least model points

    def test_allant_7s_variations(self, scorer: BikeRelevanceScorer):
        """Test various Allant+ 7S format variations."""
        variations = [
            "Trek Allant+7S",
            "Trek Allant 7S",
            "Trek Allant Plus 7S",
            "ALLANT+ 7S",
        ]
        for title in variations:
            listing = Listing(url="https://example.com/1", source="ebay", title=title)
            result = scorer.score(listing)
            assert "model: Allant+ 7S" in result.matched_factors, f"Failed for: {title}"

    def test_allant_7_wrong_model_penalty(self, scorer: BikeRelevanceScorer):
        """Test that Allant+ 7 (Class 1) receives penalty."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7 Electric Bike",
        )
        result = scorer.score(listing)
        assert "model: Allant+ 7 (WRONG - Class 1)" in result.matched_factors
        # Score should be low due to penalty
        assert result.score < 40

    def test_generic_allant_plus(self, scorer: BikeRelevanceScorer):
        """Test scoring for generic Allant+ mention."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ Electric Bike",
        )
        result = scorer.score(listing)
        assert "model: Allant+ (generic)" in result.matched_factors
        assert result.score >= 20


class TestClassScoring:
    """Tests for e-bike class scoring."""

    def test_class_3_detection(self, scorer: BikeRelevanceScorer):
        """Test Class 3 detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Class 3 E-Bike",
        )
        result = scorer.score(listing)
        assert "class: 3 (28 mph)" in result.matched_factors

    def test_28mph_detection(self, scorer: BikeRelevanceScorer):
        """Test 28 mph speed detection as Class 3 indicator."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S 28mph Electric",
        )
        result = scorer.score(listing)
        assert "class: 3 (28 mph)" in result.matched_factors

    def test_class_1_penalty(self, scorer: BikeRelevanceScorer):
        """Test Class 1 detection and penalty."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Electric Bike Class 1 20mph",
        )
        result = scorer.score(listing)
        assert "class: 1 (20 mph) - REJECT" in result.matched_factors


class TestBatteryScoring:
    """Tests for battery capacity scoring."""

    def test_625wh_battery(self, scorer: BikeRelevanceScorer):
        """Test 625Wh battery detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S 625Wh Battery",
        )
        result = scorer.score(listing)
        assert "battery: 625Wh" in result.matched_factors

    def test_625wh_with_space(self, scorer: BikeRelevanceScorer):
        """Test 625 Wh (with space) detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S 625 Wh",
        )
        result = scorer.score(listing)
        assert "battery: 625Wh" in result.matched_factors

    def test_500wh_penalty(self, scorer: BikeRelevanceScorer):
        """Test 500Wh battery penalty."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Electric Bike 500Wh",
        )
        result = scorer.score(listing)
        assert "battery: 500Wh (insufficient)" in result.matched_factors


class TestRangeExtenderScoring:
    """Tests for range extender detection."""

    def test_range_extender_detection(self, scorer: BikeRelevanceScorer):
        """Test range extender keyword detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S with Range Extender",
        )
        result = scorer.score(listing)
        assert "range extender" in result.matched_factors

    def test_dual_battery_detection(self, scorer: BikeRelevanceScorer):
        """Test dual battery keyword detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Dual Battery Setup",
        )
        result = scorer.score(listing)
        assert "range extender" in result.matched_factors

    def test_second_battery_detection(self, scorer: BikeRelevanceScorer):
        """Test second battery keyword detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S with Second Battery",
        )
        result = scorer.score(listing)
        assert "range extender" in result.matched_factors


class TestFrameScoring:
    """Tests for frame size detection."""

    def test_large_frame_detection(self, scorer: BikeRelevanceScorer):
        """Test Large frame size detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Large Frame",
        )
        result = scorer.score(listing)
        assert "frame: Large" in result.matched_factors

    def test_size_l_detection(self, scorer: BikeRelevanceScorer):
        """Test size L detection."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Size: L",
        )
        result = scorer.score(listing)
        assert "frame: Large" in result.matched_factors


class TestConfidenceClassification:
    """Tests for confidence level classification."""

    def test_high_confidence(self, scorer: BikeRelevanceScorer):
        """Test high confidence classification."""
        # Perfect listing with all criteria
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Class 3 625Wh Range Extender Large",
        )
        result = scorer.score(listing)
        assert result.confidence == "high"
        assert result.score >= 70

    def test_medium_confidence(self, scorer: BikeRelevanceScorer):
        """Test medium confidence classification."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S",
        )
        result = scorer.score(listing)
        assert result.confidence == "medium"
        assert 40 <= result.score < 70

    def test_low_confidence(self, scorer: BikeRelevanceScorer):
        """Test low confidence classification."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Electric Bike",
        )
        result = scorer.score(listing)
        assert result.confidence == "low"
        assert result.score < 40


class TestScoreCapping:
    """Tests for score bounds."""

    def test_score_capped_at_100(self, scorer: BikeRelevanceScorer):
        """Test that score is capped at 100."""
        # Listing with all positive criteria
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Class 3 625Wh Range Extender Large Frame 28mph",
            description="Perfect bike with dual battery setup and second battery",
        )
        result = scorer.score(listing)
        assert result.score <= 100

    def test_score_floored_at_0(self, scorer: BikeRelevanceScorer):
        """Test that score is floored at 0."""
        # Listing with multiple penalties
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7 Class 1 500Wh 20mph",
        )
        result = scorer.score(listing)
        assert result.score >= 0


class TestCustomWeights:
    """Tests for custom scoring weights."""

    def test_custom_weights_applied(self, custom_scorer: BikeRelevanceScorer):
        """Test that custom weights are applied."""
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="Trek Allant+ 7S Class 3 625Wh",
        )
        result = custom_scorer.score(listing)
        # With custom weights: 50 + 25 + 25 = 100
        assert result.score == 100


class TestIntegration:
    """Integration tests with realistic listings."""

    def test_perfect_match(self, scorer: BikeRelevanceScorer):
        """Test a perfect listing match."""
        listing = Listing(
            url="https://example.com/perfect",
            source="ebay",
            title="2024 Trek Allant+ 7S - Class 3 Electric Bike",
            description="625Wh battery with range extender. Large frame. 28 mph pedal assist. Excellent condition.",
        )
        result = scorer.score(listing)
        assert result.confidence == "high"
        assert len(result.matched_factors) >= 4

    def test_wrong_model_rejected(self, scorer: BikeRelevanceScorer):
        """Test that wrong model is properly rejected."""
        listing = Listing(
            url="https://example.com/wrong",
            source="ebay",
            title="Trek Allant+ 7 Electric Bike",
            description="Class 1 e-bike, 20 mph assist, 500Wh battery",
        )
        result = scorer.score(listing)
        assert result.confidence == "low"
        # Should have penalties applied
        assert any("WRONG" in f or "REJECT" in f for f in result.matched_factors)

    def test_partial_match(self, scorer: BikeRelevanceScorer):
        """Test a partial match listing."""
        listing = Listing(
            url="https://example.com/partial",
            source="ebay",
            title="Trek Allant+ Electric Bike",
            description="Great commuter bike, 625Wh battery included.",
        )
        result = scorer.score(listing)
        # Should be medium confidence - has some but not all criteria
        assert result.confidence in ["medium", "low"]
        assert "battery: 625Wh" in result.matched_factors
