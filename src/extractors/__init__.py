"""Adaptive extractors for marketplace listings."""

from src.extractors.base import AdaptiveExtractor, ExtractedListing
from src.extractors.bridge import LegacyAdapterBridge
from src.extractors.generic import GenericListingExtractor
from src.extractors.structured import StructuredDataExtractor

__all__ = [
    "AdaptiveExtractor",
    "ExtractedListing",
    "StructuredDataExtractor",
    "GenericListingExtractor",
    "LegacyAdapterBridge",
]
