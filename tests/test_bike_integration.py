"""Integration tests for bike search workflow."""

from pathlib import Path

import pytest

from src.bike_scoring import BikeRelevanceScorer
from src.bike_search import BikeSearchOrchestrator, create_orchestrator
from src.models import Listing


@pytest.fixture
def bike_config_path(tmp_path: Path) -> Path:
    """Create a temporary bike config file."""
    config_content = """
target_bike:
  name: "Trek Allant+ 7S"
  class: 3
  battery: "625Wh"

marketplaces:
  - name: ebay
    enabled: true
    priority: 1
    searches:
      - "Trek Allant+ 7S"

scoring:
  thresholds:
    high: 70
    medium: 40
  weights:
    model_allant_7s: 40
    class_3: 20
    battery_625wh: 20
    range_extender: 15
    frame_large: 5

output:
  base_dir: "{tmp_path}/output"
  logs_dir: "logs"
"""
    config_path = tmp_path / "bike_config.yaml"
    config_path.write_text(config_content.replace("{tmp_path}", str(tmp_path)))

    # Create output directories
    (tmp_path / "output" / "logs").mkdir(parents=True, exist_ok=True)

    return config_path


@pytest.fixture
def ring_config_path(tmp_path: Path) -> Path:
    """Create a temporary ring config file (no target_bike key)."""
    config_content = """
target_ring:
  name: "The Giulia Ring"

marketplaces:
  - name: ebay
    enabled: true
    searches:
      - "amethyst ring"

output:
  base_dir: "{tmp_path}/output"
  logs_dir: "logs"
"""
    config_path = tmp_path / "ring_config.yaml"
    config_path.write_text(config_content.replace("{tmp_path}", str(tmp_path)))

    # Create output directories
    (tmp_path / "output" / "logs").mkdir(parents=True, exist_ok=True)

    return config_path


class TestOrchestratorFactory:
    """Tests for create_orchestrator factory function."""

    def test_creates_bike_orchestrator_for_bike_config(self, bike_config_path: Path):
        """Test that bike config creates BikeSearchOrchestrator."""
        orchestrator = create_orchestrator(bike_config_path)

        assert isinstance(orchestrator, BikeSearchOrchestrator)
        assert isinstance(orchestrator.scorer, BikeRelevanceScorer)

    def test_creates_ring_orchestrator_for_ring_config(self, ring_config_path: Path):
        """Test that ring config creates SearchOrchestrator (not Bike)."""
        from src.ring_search import SearchOrchestrator
        from src.scoring import RelevanceScorer

        orchestrator = create_orchestrator(ring_config_path)

        # Should be base SearchOrchestrator, not BikeSearchOrchestrator
        assert type(orchestrator) is SearchOrchestrator
        assert isinstance(orchestrator.scorer, RelevanceScorer)


class TestBikeSearchOrchestrator:
    """Tests for BikeSearchOrchestrator."""

    def test_initializes_with_bike_scorer(self, bike_config_path: Path):
        """Test that BikeSearchOrchestrator uses BikeRelevanceScorer."""
        orchestrator = BikeSearchOrchestrator(bike_config_path)

        assert isinstance(orchestrator.scorer, BikeRelevanceScorer)

    def test_loads_custom_weights_from_config(self, bike_config_path: Path):
        """Test that scoring weights are loaded from config."""
        orchestrator = BikeSearchOrchestrator(bike_config_path)

        # Check weights match config
        assert orchestrator.scorer.weights.model_allant_7s == 40
        assert orchestrator.scorer.weights.class_3 == 20
        assert orchestrator.scorer.weights.battery_625wh == 20

    def test_adapter_map_includes_bike_adapters(self, bike_config_path: Path):
        """Test that bike-specific adapters are available."""
        orchestrator = BikeSearchOrchestrator(bike_config_path)

        assert "pinkbike" in orchestrator.ADAPTER_MAP
        assert "trek_redbarn" in orchestrator.ADAPTER_MAP

    def test_adapter_map_includes_common_adapters(self, bike_config_path: Path):
        """Test that common adapters are still available."""
        orchestrator = BikeSearchOrchestrator(bike_config_path)

        assert "ebay" in orchestrator.ADAPTER_MAP
        assert "craigslist" in orchestrator.ADAPTER_MAP


class TestBikeScoringIntegration:
    """Integration tests for bike scoring with realistic data."""

    @pytest.fixture
    def scorer(self) -> BikeRelevanceScorer:
        """Create scorer with default weights."""
        return BikeRelevanceScorer()

    def test_perfect_allant_7s_listing(self, scorer: BikeRelevanceScorer):
        """Test scoring of a perfect Trek Allant+ 7S listing."""
        listing = Listing(
            url="https://example.com/perfect-bike",
            source="ebay",
            title="2024 Trek Allant+ 7S Class 3 E-Bike Large",
            description="625Wh battery with range extender. 28 mph assist. Excellent condition.",
        )

        result = scorer.score(listing)

        # Should be high confidence with all factors matched
        assert result.confidence == "high"
        assert result.score >= 70
        assert "model: Allant+ 7S" in result.matched_factors
        assert "class: 3 (28 mph)" in result.matched_factors
        assert "battery: 625Wh" in result.matched_factors
        assert "range extender" in result.matched_factors
        assert "frame: Large" in result.matched_factors

    def test_wrong_model_allant_7_listing(self, scorer: BikeRelevanceScorer):
        """Test scoring rejects Allant+ 7 (Class 1)."""
        listing = Listing(
            url="https://example.com/wrong-model",
            source="ebay",
            title="Trek Allant+ 7 Electric Bike",
            description="Class 1 e-bike with 500Wh battery. 20 mph max assist.",
        )

        result = scorer.score(listing)

        # Should be low confidence with penalties
        assert result.confidence == "low"
        assert result.score < 40
        assert any("WRONG" in f for f in result.matched_factors)

    def test_partial_match_listing(self, scorer: BikeRelevanceScorer):
        """Test scoring of a partial match."""
        listing = Listing(
            url="https://example.com/partial",
            source="ebay",
            title="Trek Allant+ 7S Electric Bike",
            description="Great commuter bike in good condition.",
        )

        result = scorer.score(listing)

        # Should have model match but missing other criteria
        assert "model: Allant+ 7S" in result.matched_factors
        assert result.confidence in ["medium", "low"]


class TestAdapterRegistration:
    """Tests for adapter registration."""

    def test_pinkbike_adapter_registered(self):
        """Test that PinkbikeAdapter is in ADAPTER_MAP."""
        from src.adapters import ADAPTER_MAP, PinkbikeAdapter

        assert "pinkbike" in ADAPTER_MAP
        assert ADAPTER_MAP["pinkbike"] is PinkbikeAdapter

    def test_trek_redbarn_adapter_registered(self):
        """Test that TrekRedBarnAdapter is in ADAPTER_MAP."""
        from src.adapters import ADAPTER_MAP, TrekRedBarnAdapter

        assert "trek_redbarn" in ADAPTER_MAP
        assert ADAPTER_MAP["trek_redbarn"] is TrekRedBarnAdapter


class TestConfigDetection:
    """Tests for config-based orchestrator selection."""

    def test_bike_config_detected_by_target_bike_key(self, tmp_path: Path):
        """Test that target_bike key triggers bike orchestrator."""
        config = tmp_path / "config.yaml"
        config.write_text("""
target_bike:
  name: "Test Bike"
marketplaces: []
output:
  base_dir: "output"
  logs_dir: "logs"
""")
        (tmp_path / "output" / "logs").mkdir(parents=True)

        orchestrator = create_orchestrator(config)

        assert isinstance(orchestrator, BikeSearchOrchestrator)

    def test_ring_config_without_target_bike_key(self, tmp_path: Path):
        """Test that missing target_bike key uses ring orchestrator."""
        from src.ring_search import SearchOrchestrator

        config = tmp_path / "config.yaml"
        config.write_text("""
target_ring:
  name: "Test Ring"
marketplaces: []
output:
  base_dir: "output"
  logs_dir: "logs"
""")
        (tmp_path / "output" / "logs").mkdir(parents=True)

        orchestrator = create_orchestrator(config)

        assert type(orchestrator) is SearchOrchestrator
