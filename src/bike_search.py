"""Bike search orchestrator - extends ring search for Trek Allant+ 7S."""

import logging
from pathlib import Path
from typing import Any

from src.adapters import MarketplaceAdapter, PinkbikeAdapter, TrekRedBarnAdapter
from src.bike_scoring import BikeRelevanceScorer
from src.models import BikeScoringWeights
from src.ring_search import SearchOrchestrator

logger = logging.getLogger(__name__)


class BikeSearchOrchestrator(SearchOrchestrator):
    """Specialized orchestrator for bike search using BikeRelevanceScorer.

    Extends the base SearchOrchestrator with:
    - Bike-specific marketplace adapters (Pinkbike, Trek Red Barn)
    - BikeRelevanceScorer for Trek Allant+ 7S matching
    """

    # Extend adapter map with bike-specific marketplaces
    ADAPTER_MAP: dict[str, type[MarketplaceAdapter]] = {
        **SearchOrchestrator.ADAPTER_MAP,
        "pinkbike": PinkbikeAdapter,
        "trek_redbarn": TrekRedBarnAdapter,
    }

    def __init__(self, config_path: Path, adaptive: bool = False):
        """Initialize bike search orchestrator.

        Args:
            config_path: Path to bike_config.yaml file.
            adaptive: Enable adaptive search discovery mode.
        """
        # Call parent init (sets up dedup, logger, capture, etc.)
        super().__init__(config_path, adaptive)

        # Override scorer with BikeRelevanceScorer
        self._init_bike_scorer()

        logger.info("BikeSearchOrchestrator initialized with BikeRelevanceScorer")

    def _init_bike_scorer(self) -> None:
        """Initialize bike-specific scorer from config."""
        scoring_config = self.config.get("scoring", {})
        weights_config = scoring_config.get("weights", {})

        # Create weights from config or use defaults
        if weights_config:
            weights = BikeScoringWeights(
                model_allant_7s=weights_config.get("model_allant_7s", 40),
                model_allant_plus=weights_config.get("model_allant_plus", 20),
                class_3=weights_config.get("class_3", 20),
                battery_625wh=weights_config.get("battery_625wh", 20),
                range_extender=weights_config.get("range_extender", 15),
                frame_large=weights_config.get("frame_large", 5),
                class_1_penalty=weights_config.get("class_1_penalty", -50),
                battery_500wh_penalty=weights_config.get("battery_500wh_penalty", -20),
                model_allant_7_penalty=weights_config.get("model_allant_7_penalty", -40),
            )
        else:
            weights = BikeScoringWeights()

        self.scorer = BikeRelevanceScorer(weights=weights)  # type: ignore[assignment]

    def _create_adapter(self, marketplace: dict[str, Any]) -> MarketplaceAdapter | None:
        """Create adapter for a marketplace configuration.

        Extended to handle bike-specific adapters.

        Args:
            marketplace: Marketplace configuration dictionary.

        Returns:
            Configured adapter instance, or None if unknown marketplace.
        """
        name = marketplace.get("name", "").lower()

        # Use parent method for common adapters
        if name in SearchOrchestrator.ADAPTER_MAP:
            return super()._create_adapter(marketplace)

        # Handle bike-specific adapters
        if name not in self.ADAPTER_MAP:
            logger.warning(f"Unknown marketplace: {name}")
            return None

        adapter_class = self.ADAPTER_MAP[name]

        return adapter_class(
            min_delay=self.min_delay,
            max_delay=self.max_delay,
        )


def create_orchestrator(config_path: Path, adaptive: bool = False) -> SearchOrchestrator:
    """Factory function to create appropriate orchestrator based on config.

    Examines the config file to determine whether to use ring or bike search.

    Args:
        config_path: Path to config file.
        adaptive: Enable adaptive search discovery mode.

    Returns:
        Appropriate orchestrator instance.
    """
    import yaml

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Check if this is a bike config (has target_bike key)
    if "target_bike" in config:
        logger.info("Detected bike search configuration")
        return BikeSearchOrchestrator(config_path, adaptive)

    # Default to ring search
    return SearchOrchestrator(config_path, adaptive)
