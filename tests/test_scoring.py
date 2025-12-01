"""Tests for relevance scoring engine."""

from src.models import Listing, ScoringWeights
from src.scoring import RelevanceScorer


class TestRelevanceScorer:
    """Tests for RelevanceScorer class."""

    def test_high_confidence_match(self) -> None:
        """Test that a listing with many matching criteria scores high."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/1",
            source="ebay",
            title="10K Yellow Gold Amethyst Seed Pearl Victorian Ring Size 7",
            price="$450",
            description="Beautiful antique swirl design ring",
        )

        result = scorer.score(listing)

        assert result.confidence == "high"
        assert result.score >= 70
        assert "gold" in result.matched_factors
        assert "10k" in result.matched_factors
        assert "amethyst" in result.matched_factors
        assert "seed pearl" in result.matched_factors

    def test_medium_confidence_match(self) -> None:
        """Test that a listing with some matching criteria scores medium."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/2",
            source="etsy",
            title="Vintage Gold Amethyst Ring",
            price="$200",
            description=None,
        )

        result = scorer.score(listing)

        assert result.confidence == "medium"
        assert 40 <= result.score < 70
        assert "gold" in result.matched_factors
        assert "amethyst" in result.matched_factors

    def test_low_confidence_match(self) -> None:
        """Test that a listing with few matching criteria scores low."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/3",
            source="ebay",
            title="Silver Ring with Blue Stone",
            price="$50",
            description="Modern design",
        )

        result = scorer.score(listing)

        assert result.confidence == "low"
        assert result.score < 40

    def test_score_capped_at_100(self) -> None:
        """Test that score is capped at 100."""
        scorer = RelevanceScorer()
        # Listing with maximum possible matches
        listing = Listing(
            url="https://example.com/4",
            source="ebay",
            title="10K Yellow Gold Amethyst Seed Pearl Victorian Swirl Ring Size 7",
            price="$1000",
            description="Antique Art Nouveau design with flowing pattern",
        )

        result = scorer.score(listing)

        assert result.score <= 100

    def test_metal_scoring_yellow_gold(self) -> None:
        """Test yellow gold detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/5",
            source="ebay",
            title="Yellow Gold Ring",
            price="$100",
        )

        result = scorer.score(listing)
        assert "gold" in result.matched_factors

    def test_metal_scoring_excludes_white_gold(self) -> None:
        """Test that white gold is not scored as yellow gold."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/6",
            source="ebay",
            title="White Gold Ring",
            price="$100",
        )

        result = scorer.score(listing)
        assert "gold" not in result.matched_factors

    def test_metal_scoring_14k_partial(self) -> None:
        """Test that 14k gold gets partial credit."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/7",
            source="ebay",
            title="14K Gold Ring",
            price="$200",
        )

        result = scorer.score(listing)
        assert "gold karat" in result.matched_factors

    def test_stone_scoring_amethyst(self) -> None:
        """Test amethyst detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/8",
            source="ebay",
            title="Ring with Amethyst Stone",
            price="$100",
        )

        result = scorer.score(listing)
        assert "amethyst" in result.matched_factors
        assert result.score >= 25  # amethyst weight

    def test_stone_scoring_purple_alternative(self) -> None:
        """Test purple stone as amethyst alternative."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/9",
            source="ebay",
            title="Ring with Purple Stone",
            price="$100",
        )

        result = scorer.score(listing)
        assert "purple stone" in result.matched_factors

    def test_pearl_scoring_seed_pearl(self) -> None:
        """Test seed pearl detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/10",
            source="ebay",
            title="Ring with Seed Pearl",
            price="$100",
        )

        result = scorer.score(listing)
        assert "seed pearl" in result.matched_factors

    def test_pearl_scoring_generic_pearl(self) -> None:
        """Test generic pearl detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/11",
            source="ebay",
            title="Ring with Pearl",
            price="$100",
        )

        result = scorer.score(listing)
        assert "pearl" in result.matched_factors

    def test_design_scoring_swirl(self) -> None:
        """Test swirl design detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/12",
            source="ebay",
            title="Swirl Design Ring",
            price="$100",
        )

        result = scorer.score(listing)
        assert "swirl design" in result.matched_factors

    def test_design_scoring_infinity(self) -> None:
        """Test infinity design detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/13",
            source="ebay",
            title="Infinity Pattern Ring",
            price="$100",
        )

        result = scorer.score(listing)
        assert "swirl design" in result.matched_factors

    def test_era_scoring_victorian(self) -> None:
        """Test Victorian era detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/14",
            source="ebay",
            title="Victorian Era Ring",
            price="$100",
        )

        result = scorer.score(listing)
        assert "vintage era" in result.matched_factors

    def test_era_scoring_antique(self) -> None:
        """Test antique detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/15",
            source="ebay",
            title="Antique Ring",
            price="$100",
        )

        result = scorer.score(listing)
        assert "vintage era" in result.matched_factors

    def test_size_scoring_exact_match(self) -> None:
        """Test exact size 7 detection."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/16",
            source="ebay",
            title="Ring Size 7",
            price="$100",
        )

        result = scorer.score(listing)
        assert "size 7" in result.matched_factors

    def test_size_scoring_close_match(self) -> None:
        """Test close size detection (6, 6.5, 7.5, 8)."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/17",
            source="ebay",
            title="Ring Size 6.5",
            price="$100",
        )

        result = scorer.score(listing)
        assert "size close" in result.matched_factors

    def test_custom_weights(self) -> None:
        """Test that custom weights are applied."""
        custom_weights = ScoringWeights(stone_amethyst=50)  # Double the default
        scorer = RelevanceScorer(weights=custom_weights)
        listing = Listing(
            url="https://example.com/18",
            source="ebay",
            title="Amethyst Ring",
            price="$100",
        )

        result = scorer.score(listing)
        assert result.score >= 50

    def test_description_included_in_scoring(self) -> None:
        """Test that description text is included in scoring."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/19",
            source="ebay",
            title="Ring",
            price="$100",
            description="Beautiful amethyst stone with seed pearls",
        )

        result = scorer.score(listing)
        assert "amethyst" in result.matched_factors
        assert "seed pearl" in result.matched_factors

    def test_result_preserves_listing_data(self) -> None:
        """Test that scored listing preserves original data."""
        scorer = RelevanceScorer()
        listing = Listing(
            url="https://example.com/20",
            source="shopgoodwill",
            title="Test Ring",
            price="$99",
            description="Test description",
            image_url="https://example.com/img.jpg",
        )

        result = scorer.score(listing)

        assert result.url == listing.url
        assert result.source == listing.source
        assert result.title == listing.title
        assert result.price == listing.price
        assert result.description == listing.description
        assert result.image_url == listing.image_url
