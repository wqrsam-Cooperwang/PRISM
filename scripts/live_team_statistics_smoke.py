"""Manual CLI for one secret-safe API-Football team-statistics smoke test."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from src.acquisition.api_football_runtime import (
    ApiFootballRuntimeConfig,
    build_api_football_team_statistics_client,
)
from src.acquisition.api_football_smoke import run_live_team_statistics_smoke
from src.acquisition.models import ProviderFetchRequest
from src.intelligence import MatchTarget


def _parse_kickoff(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("kickoff must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("kickoff must include a timezone")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one live PRISM API-Football team-statistics smoke test"
    )
    parser.add_argument("--home", required=True, help="Home team name")
    parser.add_argument("--away", required=True, help="Away team name")
    parser.add_argument("--competition", required=True, help="Competition label")
    parser.add_argument("--kickoff", required=True, type=_parse_kickoff, help="ISO-8601 kickoff")
    return parser


def main() -> int:
    args = _parser().parse_args()
    run_id = uuid4().hex
    target = MatchTarget(
        match_id=f"live-team-statistics-{run_id}",
        competition=args.competition,
        kickoff=args.kickoff,
        home_team_id="home",
        home_team_name=args.home,
        away_team_id="away",
        away_team_name=args.away,
    )
    request = ProviderFetchRequest(
        request_id=f"live-team-statistics-{run_id}",
        target=target,
        requested_at=datetime.now(timezone.utc),
    )
    config = ApiFootballRuntimeConfig.from_environment()
    client = build_api_football_team_statistics_client(config)
    summary = run_live_team_statistics_smoke(request, client)
    payload = asdict(summary)
    payload["home_retrieved_at"] = summary.home_retrieved_at.isoformat()
    payload["away_retrieved_at"] = summary.away_retrieved_at.isoformat()
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
