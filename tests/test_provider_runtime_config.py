import pytest

from src.acquisition import (
    OddsProviderRuntimeConfig,
    build_the_odds_api_market_client,
)
from src.connectors import FixtureHttpTransport, RetryPolicy


def test_runtime_config_reads_required_secret_and_defaults() -> None:
    config = OddsProviderRuntimeConfig.from_environment(
        {"THE_ODDS_API_KEY": " secret-key "}
    )

    assert config.api_key == "secret-key"
    assert config.sport_key == "soccer_korea_kleague1"
    assert config.bookmaker_key == "pinnacle"
    assert "secret-key" not in repr(config)


def test_runtime_config_allows_non_secret_overrides() -> None:
    config = OddsProviderRuntimeConfig.from_environment(
        {
            "THE_ODDS_API_KEY": "secret-key",
            "PRISM_ODDS_SPORT_KEY": " soccer_epl ",
            "PRISM_ODDS_BOOKMAKER_KEY": " betfair_ex_eu ",
        }
    )

    assert config.sport_key == "soccer_epl"
    assert config.bookmaker_key == "betfair_ex_eu"


def test_runtime_config_fails_closed_for_missing_or_blank_values() -> None:
    with pytest.raises(RuntimeError, match="THE_ODDS_API_KEY"):
        OddsProviderRuntimeConfig.from_environment({})
    with pytest.raises(RuntimeError, match="THE_ODDS_API_KEY"):
        OddsProviderRuntimeConfig.from_environment({"THE_ODDS_API_KEY": "   "})
    with pytest.raises(RuntimeError, match="PRISM_ODDS_SPORT_KEY"):
        OddsProviderRuntimeConfig.from_environment(
            {
                "THE_ODDS_API_KEY": "secret-key",
                "PRISM_ODDS_SPORT_KEY": "   ",
            }
        )


def test_provider_factory_keeps_secret_out_of_repr_and_uses_config() -> None:
    config = OddsProviderRuntimeConfig.from_environment(
        {"THE_ODDS_API_KEY": "secret-key"}
    )
    transport = FixtureHttpTransport([])
    policy = RetryPolicy(max_attempts=1)

    client = build_the_odds_api_market_client(
        config,
        transport=transport,
        retry_policy=policy,
    )

    assert client.sport_key == "soccer_korea_kleague1"
    assert client.bookmaker_key == "pinnacle"
    assert client.transport is transport
    assert client.retry_policy is policy
    assert "secret-key" not in repr(client)
