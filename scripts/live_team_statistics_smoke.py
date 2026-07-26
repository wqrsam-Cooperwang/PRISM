"""Manual CLI for one secret-safe API-Football team-statistics smoke test."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from src.acquisition import ApiFootballIdentityResolver
from src.acquisition.api_football_runtime import (
    ApiFootballRuntimeConfig,
    build_api_football_team_statistics_client,
)
from src.acquisition.api_football_smoke import run_live_team_statistics_smoke
from src.acquisition.models import ProviderFetchRequest
from src.connectors import StdlibHttpTransport
from src.intelligence import MatchTarget


def _parse_kickoff(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("kickoff must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("kickoff must include a timezone")
    return parsed


def _positive_year(value: str) -> int:
    try:
        year = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("season must be an integer year") from exc
    if year <= 0:
        raise argparse.ArgumentTypeError("season must be positive")
    return year


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one live PRISM API-Football team-statistics smoke test"
    )
    parser.add_argument("--home", required=True, help="Home team name")
    parser.add_argument("--away", required=True, help="Away team name")
    parser.add_argument("--competition", required=True, help="Competition label")
    parser.add_argument("--season", required=True, type=_positive_year, help="Season year")
    parser.add_argument("--kickoff", required=True, type=_parse_kickoff, help="ISO-8601 kickoff")
    return parser


def _required_api_key() -> str:
    value = os.environ.get("API_FOOTBALL_KEY")
    if value is None or not value.strip():
        raise RuntimeError("Required provider secret is missing: API_FOOTBALL_KEY")
    return value.strip()


def main() -> int:
    args = _parser().parse_args()
    api_key = _required_api_key()
    transport = StdlibHttpTransport()
    resolver = ApiFootballIdentityResolver(api_key=api_key, transport=transport)
    identity = resolver.resolve(
        competition=args.competition,
        season=args.season,
        home_team=args.home,
        away_team=args.away,
    )

    run_id = uuid4().hex
    target = MatchTarget(
        match_id=f"live-team-statistics-{run_id}",
        competition=identity.league_name,
        kickoff=args.kickoff,
        home_team_id=str(identity.home_team_id),
        home_team_name=identity.home_team_name,
        away_team_id=str(identity.away_team_id),
        away_team_name=identity.away_team_name,
        season=str(identity.season),
    )
    request = ProviderFetchRequest(
        request_id=f"live-team-statistics-{run_id}",
        target=target,
        requested_at=datetime.now(timezone.utc),
    )
    config = ApiFootballRuntimeConfig(
        api_key=api_key,
        league_id=identity.league_id,
        season=identity.season,
        home_team_id=identity.home_team_id,
        away_team_id=identity.away_team_id,
    )
    client = build_api_football_team_statistics_client(config, transport=transport)
    summary = run_live_team_statistics_smoke(request, client)
    payload = asdict(summary)
    payload["home_retrieved_at"] = summary.home_retrieved_at.isoformat()
    payload["away_retrieved_at"] = summary.away_retrieved_at.isoformat()
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
