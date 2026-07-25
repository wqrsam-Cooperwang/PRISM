"""Public automated collection API for PRISM."""

from src.collection.availability_schedule import AvailabilityScheduleAdapter
from src.collection.fixture import FixtureObservationAdapter
from src.collection.interface import ObservationAdapter
from src.collection.market import MarketOdds1X2Adapter
from src.collection.models import SourceEnvelope
from src.collection.readiness import (
    CollectionGateDecision,
    CollectionReadinessGateResult,
    evaluate_collection_readiness,
)
from src.collection.runner import collect_observations
from src.collection.team_strength_form import TeamStrengthFormAdapter
from src.collection.weather_lineup import WeatherLineupAdapter

__all__ = [
    "AvailabilityScheduleAdapter",
    "CollectionGateDecision",
    "CollectionReadinessGateResult",
    "FixtureObservationAdapter",
    "MarketOdds1X2Adapter",
    "ObservationAdapter",
    "SourceEnvelope",
    "TeamStrengthFormAdapter",
    "WeatherLineupAdapter",
    "collect_observations",
    "evaluate_collection_readiness",
]
