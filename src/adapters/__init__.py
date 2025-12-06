"""Marketplace adapters for ring search automation."""

from src.adapters.base import MarketplaceAdapter
from src.adapters.bicyclebluebook import BicycleBlueBookAdapter
from src.adapters.craigslist import CraigslistAdapter
from src.adapters.ebay import EbayAdapter
from src.adapters.etsy import EtsyAdapter
from src.adapters.mercari import MercariAdapter
from src.adapters.pinkbike import PinkbikeAdapter
from src.adapters.poshmark import PoshmarkAdapter
from src.adapters.rubylane import RubyLaneAdapter
from src.adapters.shopgoodwill import ShopGoodwillAdapter
from src.adapters.trek_redbarn import TrekRedBarnAdapter

# Map adapter names to classes (used by LegacyAdapterBridge)
ADAPTER_MAP: dict[str, type[MarketplaceAdapter]] = {
    "shopgoodwill": ShopGoodwillAdapter,
    "ebay": EbayAdapter,
    "etsy": EtsyAdapter,
    "craigslist": CraigslistAdapter,
    "rubylane": RubyLaneAdapter,
    "mercari": MercariAdapter,
    "poshmark": PoshmarkAdapter,
    "pinkbike": PinkbikeAdapter,
    "trek_redbarn": TrekRedBarnAdapter,
    "bicyclebluebook": BicycleBlueBookAdapter,
}

__all__ = [
    "MarketplaceAdapter",
    "ShopGoodwillAdapter",
    "EbayAdapter",
    "EtsyAdapter",
    "CraigslistAdapter",
    "RubyLaneAdapter",
    "MercariAdapter",
    "PoshmarkAdapter",
    "PinkbikeAdapter",
    "TrekRedBarnAdapter",
    "BicycleBlueBookAdapter",
    "ADAPTER_MAP",
]
