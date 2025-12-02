"""Marketplace adapters for ring search automation."""

from src.adapters.base import MarketplaceAdapter
from src.adapters.craigslist import CraigslistAdapter
from src.adapters.ebay import EbayAdapter
from src.adapters.etsy import EtsyAdapter
from src.adapters.mercari import MercariAdapter
from src.adapters.poshmark import PoshmarkAdapter
from src.adapters.rubylane import RubyLaneAdapter
from src.adapters.shopgoodwill import ShopGoodwillAdapter

__all__ = [
    "MarketplaceAdapter",
    "ShopGoodwillAdapter",
    "EbayAdapter",
    "EtsyAdapter",
    "CraigslistAdapter",
    "RubyLaneAdapter",
    "MercariAdapter",
    "PoshmarkAdapter",
]
