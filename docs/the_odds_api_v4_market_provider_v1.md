# The Odds API V4 Market Provider Client V1

## Objective

Implement the first real external football provider client for PRISM by translating
The Odds API V4 football `h2h` responses into the existing
`market_odds_1x2` collection envelope contract.

## Endpoint

The client queries:

`GET https://api.the-odds-api.com/v4/sports/{sport_key}/odds`

with:

- `apiKey` supplied at runtime only;
- `bookmakers` set to one explicit bookmaker key;
- `markets=h2h`;
- `oddsFormat=decimal`;
- `dateFormat=iso`.

The API key must never be stored in `SourceEnvelope`, fixtures, reports, or
request `repr` output.

## Identity

V1 performs fail-closed exact normalized team-name matching against the
`MatchTarget` home and away names. It also validates the provider commence time
against the target kickoff within a configurable tolerance.

No fuzzy team matching is permitted in V1.

## Market extraction

The selected event must contain exactly one requested bookmaker and an `h2h`
market with numeric prices for:

- target home team;
- `Draw`;
- target away team.

The provider market `last_update` is used as `observed_at` when available,
otherwise bookmaker `last_update` is used. The HTTP response receipt time is
used as `retrieved_at`.

## Output

Exactly one `SourceEnvelope` is emitted with:

- `adapter_id = market_odds_1x2`;
- source type `MARKET`;
- source id `the-odds-api:{bookmaker_key}`;
- acquisition request id preserved;
- standard market adapter payload containing team ids and three decimal odds.

No de-vigging, bookmaker averaging, consensus, or prediction logic is performed
inside this client.

## Failure behaviour

The client fails closed when:

- HTTP acquisition ultimately fails;
- response JSON is invalid or is not an array;
- no exact event identity match exists;
- more than one event matches the same target identity;
- kickoff differs beyond tolerance;
- requested bookmaker or `h2h` market is missing;
- one of home/draw/away outcomes is missing or invalid.
