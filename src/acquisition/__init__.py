"""Public provider acquisition API for PRISM."""

from src.acquisition.api_football import ApiFootballTeamStatisticsClient
from src.acquisition.api_football_runtime import (
    ApiFootballRuntimeConfig,
    build_api_football_team_statistics_client,
)
from src.acquisition.api_football_smoke import (
    LiveTeamStatisticsSmokeSummary,
    run_live_team_statistics_smoke,
)
from src.acquisition.fixture import FixtureProviderClient
from src.acquisition.interface import ProviderClient
from src.acquisition.live_production import run_live_market_prediction_path
from src.acquisition.live_smoke import LiveOddsSmokeSummary, run_live_odds_smoke
from src.acquisition.models import ProviderFetchRequest
from src.acquisition.production_path import run_acquired_prediction_path
from src.acquisition.runner import ProviderAcquisitionError, acquire_source_envelopes
from src.acquisition.runtime_config import (
    OddsProviderRuntimeConfig,
    build_the_odds_api_market_client,
)
from src.acquisition.the_odds_api import TheOddsApiV4MarketClient

__all__ = [
    "ApiFootballRuntimeConfig",
    "ApiFootballTeamStatisticsClient",
    "FixtureProviderClient",
    "LiveOddsSmokeSummary",
    "LiveTeamStatisticsSmokeSummary",
    "OddsProviderRuntimeConfig",
    "ProviderAcquisitionError",
    "ProviderClient",
    "ProviderFetchRequest",
    "TheOddsApiV4MarketClient",
    "acquire_source_envelopes",
    "build_api_football_team_statistics_client",
    "build_the_odds_api_market_client",
    "run_acquired_prediction_path",
    "run_live_market_prediction_path",
    "run_live_odds_smoke",
    "run_live_team_statistics_smoke",
]
