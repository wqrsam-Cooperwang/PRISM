"""Read-only projection from governed runtime results to prediction reports."""

from __future__ import annotations

from src.report.models import (
    AdjustmentReport,
    ConfidenceReport,
    ConsensusReport,
    DecisionReport,
    EngineTraceReport,
    EvidenceReport,
    MatchReport,
    PredictionReport,
    ProvenanceReport,
    ScorelineCandidateReport,
    ScorelineReport,
)
from src.runtime.orchestrator import RuntimeResult


def build_prediction_report(result: RuntimeResult) -> PredictionReport:
    """Project a completed runtime result without recalculating analytical values."""

    context = result.context
    consensus = context.consensus
    confidence = context.confidence
    evidence = context.evidence
    decision = context.decision
    adjustment = context.adjustment
    scoreline = result.scoreline

    return PredictionReport(
        match=MatchReport(
            match_id=context.match.match_id,
            competition=context.match.competition,
            kickoff=context.match.kickoff,
            home_team=context.home_team.name,
            away_team=context.away_team.name,
        ),
        consensus=(
            None
            if consensus is None
            else ConsensusReport(
                home_probability=consensus.home_probability,
                draw_probability=consensus.draw_probability,
                away_probability=consensus.away_probability,
                leading_outcome=consensus.leading_outcome,
                agreement=consensus.agreement,
                model_count=consensus.model_count,
            )
        ),
        confidence=(
            None
            if confidence is None
            else ConfidenceReport(
                overall=confidence.overall,
                band=confidence.band.value,
                penalties=confidence.penalties,
            )
        ),
        evidence=(
            None
            if evidence is None
            else EvidenceReport(
                score=evidence.score,
                gate=evidence.gate.value,
                warnings=evidence.warnings,
                missing_categories=evidence.missing_categories,
                critical_caps_applied=evidence.critical_caps_applied,
            )
        ),
        decision=(
            None
            if decision is None
            else DecisionReport(
                action=decision.action.value,
                selected_market=decision.selected_market,
                expected_value=decision.expected_value,
                risk_level=decision.risk_level,
                rationale=decision.rationale,
            )
        ),
        adjustment=(
            None
            if adjustment is None
            else AdjustmentReport(
                base_confidence=adjustment.base_confidence,
                adjusted_confidence=adjustment.adjusted_confidence,
                confidence_cap=adjustment.confidence_cap,
                decision_blocked=adjustment.decision_blocked,
                applied_effects=adjustment.applied_effects,
                observed_effects=adjustment.observed_effects,
                rule_outputs=context.rule_outputs,
            )
        ),
        scoreline=(
            None
            if scoreline is None
            else ScorelineReport(
                available=scoreline.available,
                method=scoreline.method,
                expected_home_goals=scoreline.expected_home_goals,
                expected_away_goals=scoreline.expected_away_goals,
                top_scorelines=tuple(
                    ScorelineCandidateReport(
                        home_goals=item.home_goals,
                        away_goals=item.away_goals,
                        probability=item.probability,
                    )
                    for item in scoreline.top_scorelines
                ),
                source_model_ids=scoreline.source_model_ids,
                grid_probability_mass=scoreline.grid_probability_mass,
                tail_mass=scoreline.tail_mass,
            )
        ),
        provenance=ProvenanceReport(
            prism_version=context.session.prism_version,
            schema_version=context.schema_version,
            runtime_version=result.runtime_version,
            session_id=context.session.session_id,
            git_commit=context.session.git_commit,
            data_version=context.session.data_version,
            rule_version=context.session.rule_version,
            model_version=context.session.model_version,
            prompt_version=context.session.prompt_version,
            ai_models=context.session.ai_models,
            engine_trace=tuple(
                EngineTraceReport(item.name, item.version, item.status)
                for item in result.engine_trace
            ),
        ),
    )


def build_prediction_report_dict(result: RuntimeResult) -> dict[str, object]:
    """Return the governed prediction report as JSON-compatible data."""

    return build_prediction_report(result).to_dict()
