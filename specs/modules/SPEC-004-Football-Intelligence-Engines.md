# SPEC-004 — Football Intelligence Engines

Status: Draft  
Target release: PRISM Enterprise V3.1

## 1. League Reliability

Each competition receives a dynamic reliability profile based on:

- source coverage and consistency;
- xG and event-data availability;
- lineup and injury transparency;
- market liquidity and efficiency;
- schedule stability;
- historical model calibration;
- sample size.

Reliability affects confidence and uncertainty width. It must not be treated as a direct team-strength feature.

## 2. League-Specific Models

PRISM may maintain league-specific parameters or models for:

- home advantage;
- goal distribution;
- draw tendency;
- referee effects;
- market efficiency;
- feature weights;
- seasonal transition speed.

Hierarchical shrinkage should be used where a league has insufficient data, allowing information sharing without forcing one global model on all competitions.

## 3. Team DNA

Long-term team profiles may include:

- behaviour when leading or trailing;
- home/away style difference;
- late-goal tendency;
- set-piece dependence;
- pressing intensity;
- transition and counterattack tendency;
- performance against stronger and weaker opponents;
- volatility and upset profile.

Team DNA must be time-decayed and reset or partially reset after major regime breaks.

## 4. Coach DNA

Coach profiles may include:

- preferred tactical styles;
- rotation tendency;
- substitution timing;
- competition-priority behaviour;
- away-match conservatism;
- strong-opponent approach;
- game-state management.

A coaching change triggers a regime-break process. Historical team data must not be transferred unchanged into the new regime.

## 5. Player Impact V2

Player impact is decomposed into:

- attacking impact;
- defensive impact;
- buildup impact;
- pressing impact;
- set-piece impact;
- replacement-level gap;
- minutes and fitness uncertainty.

Availability must be represented probabilistically when status is unconfirmed. Multiple absences require interaction controls rather than naive summation.

## 6. Goalkeeper Engine

The goalkeeper model may use:

- post-shot xG minus goals allowed;
- save performance;
- cross and aerial handling;
- sweeping and positioning;
- distribution under pressure;
- penalty performance;
- replacement goalkeeper gap.

Goalkeeper effects must be regularised heavily because small samples are noisy.

## 7. Set-Piece Engine

Model attacking and defensive threat from:

- corners;
- direct and indirect free kicks;
- long throws;
- penalties;
- aerial mismatches;
- delivery quality and target availability.

The engine should separate repeatable set-piece quality from short-term conversion variance.

## 8. Tactical Matchup

Represent styles rather than formation labels alone:

- high press;
- low block;
- possession control;
- direct play;
- long ball;
- transition attack;
- counterpress;
- width and crossing dependence.

Matchup features must describe interactions between both teams, not only isolated style ratings.

## 9. Aggregate Incentive

For two-legged ties, model:

- current aggregate score;
- away/home second-leg context;
- qualification incentives;
- extra-time and penalty pathways;
- asymmetric risk tolerance;
- time-dependent tactical incentives.

The first-leg result must be sourced and verified before use.

## 10. Competition Priority

Estimate rotation and effort incentives from:

- competition importance;
- league position;
- relegation/title pressure;
- fixture congestion;
- travel;
- upcoming fixtures;
- club statements;
- historical coach and team behaviour.

Projected rotation must enter through probability-weighted scenarios.

## 11. Anomaly Detection

Flag matches affected by:

- mass rotation;
- unexpected lineup change;
- severe weather or pitch deterioration;
- early red card;
- unusual penalty or VAR events;
- goalkeeper injury;
- extreme market movement;
- source disagreement;
- data gaps.

Anomaly flags serve two purposes:

1. adjust live/post-match interpretation;
2. prevent abnormal matches from contaminating learning.

They must not automatically delete samples. Weight reduction and exclusion require documented rules.
