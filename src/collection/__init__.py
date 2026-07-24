"""Public automated collection API for PRISM."""

from src.collection.fixture import FixtureObservationAdapter
from src.collection.interface import ObservationAdapter
from src.collection.market import MarketOdds1X2Adapter
from src.collection.models import SourceEnvelope
from src.collection.runner import collect_observations
from src.collection.team_strength_form import TeamStrengthFormAdapter

__all__ = [
    "FixtureObservationAdapter",
    "MarketOdds1X2Adapter",
    "ObservationAdapter",
    "SourceEnvelope",
    "TeamStrengthFormAdapter",
    "collect_observations",
]
