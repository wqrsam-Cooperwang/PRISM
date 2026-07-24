"""Post-match scoring harness for governed PRISM predictions."""

from __future__ import annotations

from collections.abc import Iterable
from math import log

from src.evaluation.models import EvaluationCase, EvaluationResult, EvaluationSummary
from src.report.application import analyze_match_report

_LOG_EPSILON = 1e-15


def _actual_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def _leading_probability(
    leading_outcome: str,
    home_probability: float,
    draw_probability: float,
    away_probability: float,
) -> float:
    if leading_outcome == "home":
        return home_probability
    if leading_outcome == "draw":
        return draw_probability
    if leading_outcome == "away":
        return away_probability
    return max(home_probability, draw_probability, away_probability)


class RealMatchEvaluationHarness:
    """Execute production PRISM predictions and score them against final results."""

    version = "1.0.0"

    def evaluate(self, case: EvaluationCase) -> EvaluationResult:
        """Evaluate one historical match without exposing the result to prediction."""

        report = analyze_match_report(
            case.request,
            case.completeness,
            prism_version=case.prism_version,
            session_id=case.session_id,
            created_at=case.created_at,
            git_commit=case.git_commit,
            data_version=case.data_version,
            rule_version=case.rule_version,
            model_version=case.model_version,
            prompt_version=case.prompt_version,
            operator=case.operator,
            ai_models=case.ai_models,
        )

        consensus = report.consensus
        confidence = report.confidence
        evidence = report.evidence
        decision = report.decision
        if consensus is None or confidence is None or evidence is None or decision is None:
            raise ValueError("Evaluation requires a completed governed prediction report")

        actual = _actual_outcome(case.actual_home_goals, case.actual_away_goals)
        probabilities = {
            "home": consensus.home_probability,
            "draw": consensus.draw_probability,
            "away": consensus.away_probability,
        }
        brier_score = sum(
            (probability - (1.0 if outcome == actual else 0.0)) ** 2
            for outcome, probability in probabilities.items()
        )
        actual_probability = max(_LOG_EPSILON, probabilities[actual])
        log_loss = -log(actual_probability)
        top1_correct = consensus.leading_outcome == actual
        leading_probability = _leading_probability(
            consensus.leading_outcome,
            consensus.home_probability,
            consensus.draw_probability,
            consensus.away_probability,
        )

        scoreline_hit: bool | None = None
        if report.scoreline is not None and report.scoreline.available:
            scoreline_hit = any(
                candidate.home_goals == case.actual_home_goals
                and candidate.away_goals == case.actual_away_goals
                for candidate in report.scoreline.top_scorelines
            )

        candidate_correct: bool | None = None
        if decision.action == "candidate" and decision.selected_market in probabilities:
            candidate_correct = decision.selected_market == actual

        return EvaluationResult(
            case_id=case.case_id,
            match_id=case.request.match_id,
            actual_home_goals=case.actual_home_goals,
            actual_away_goals=case.actual_away_goals,
            actual_outcome=actual,
            home_probability=consensus.home_probability,
            draw_probability=consensus.draw_probability,
            away_probability=consensus.away_probability,
            leading_outcome=consensus.leading_outcome,
            leading_probability=leading_probability,
            brier_score=brier_score,
            log_loss=log_loss,
            top1_correct=top1_correct,
            scoreline_top3_hit=scoreline_hit,
            decision_action=decision.action,
            selected_market=decision.selected_market,
            candidate_correct=candidate_correct,
            overall_confidence=confidence.overall,
            evidence_gate=evidence.gate,
            report=report,
        )

    def evaluate_many(self, cases: Iterable[EvaluationCase]) -> EvaluationSummary:
        """Evaluate a non-empty batch while preserving input case order."""

        results = tuple(self.evaluate(case) for case in cases)
        if not results:
            raise ValueError("Evaluation batch must contain at least one case")

        count = len(results)
        scoreline_results = tuple(
            result.scoreline_top3_hit
            for result in results
            if result.scoreline_top3_hit is not None
        )
        candidate_results = tuple(
            result.candidate_correct for result in results if result.candidate_correct is not None
        )

        return EvaluationSummary(
            case_count=count,
            mean_brier_score=sum(result.brier_score for result in results) / count,
            mean_log_loss=sum(result.log_loss for result in results) / count,
            top1_accuracy=sum(result.top1_correct for result in results) / count,
            scoreline_available_count=len(scoreline_results),
            scoreline_top3_hit_rate=(
                None
                if not scoreline_results
                else sum(scoreline_results) / len(scoreline_results)
            ),
            candidate_count=len(candidate_results),
            candidate_accuracy=(
                None
                if not candidate_results
                else sum(candidate_results) / len(candidate_results)
            ),
            mean_overall_confidence=(
                sum(result.overall_confidence for result in results) / count
            ),
            results=results,
        )
