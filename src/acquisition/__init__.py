"""Public provider acquisition API for PRISM."""

from src.acquisition.fixture import FixtureProviderClient
from src.acquisition.interface import ProviderClient
from src.acquisition.models import ProviderFetchRequest
from src.acquisition.production_path import run_acquired_prediction_path
from src.acquisition.runner import ProviderAcquisitionError, acquire_source_envelopes
from src.acquisition.the_odds_api import TheOddsApiV4MarketClient

__all__ = [
    "FixtureProviderClient",
    "ProviderAcquisitionError",
    "ProviderClient",
    "ProviderFetchRequest",
    "TheOddsApiV4MarketClient",
    "acquire_source_envelopes",
    "run_acquired_prediction_path",
]
