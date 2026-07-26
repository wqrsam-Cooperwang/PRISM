"""Runtime configuration for real PRISM provider clients."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from src.acquisition.the_odds_api import TheOddsApiV4MarketClient
from src.connectors import HttpTransport, RetryPolicy, StdlibHttpTransport

_DEFAULT_SPORT_KEY = "soccer_korea_kleague1"
_DEFAULT_BOOKMAKER_KEY = "pinnacle"


def _required_secret(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Required provider secret is missing: {name}")
    return value.strip()


def _optional_text(environment: Mapping[str, str], name: str, default: str) -> str:
    value = environment.get(name, default)
    if not value.strip():
        raise RuntimeError(f"Provider configuration must not be blank: {name}")
    return value.strip()


@dataclass(frozen=True)
class OddsProviderRuntimeConfig:
    """Secret-safe runtime configuration for The Odds API V4 market client."""

    api_key: str = field(repr=False)
    sport_key: str = _DEFAULT_SPORT_KEY
    bookmaker_key: str = _DEFAULT_BOOKMAKER_KEY

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "OddsProviderRuntimeConfig":
        source = os.environ if environment is None else environment
        return cls(
            api_key=_required_secret(source, "THE_ODDS_API_KEY"),
            sport_key=_optional_text(source, "PRISM_ODDS_SPORT_KEY", _DEFAULT_SPORT_KEY),
            bookmaker_key=_optional_text(
                source,
                "PRISM_ODDS_BOOKMAKER_KEY",
                _DEFAULT_BOOKMAKER_KEY,
            ),
        )


def build_the_odds_api_market_client(
    config: OddsProviderRuntimeConfig,
    *,
    transport: HttpTransport | None = None,
    retry_policy: RetryPolicy | None = None,
) -> TheOddsApiV4MarketClient:
    """Construct the real market client from validated runtime configuration."""

    return TheOddsApiV4MarketClient(
        api_key=config.api_key,
        sport_key=config.sport_key,
        bookmaker_key=config.bookmaker_key,
        transport=StdlibHttpTransport() if transport is None else transport,
        retry_policy=RetryPolicy() if retry_policy is None else retry_policy,
    )
