from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bayesian import run_bayesian_inference
from .models import Condition, ConditionRiskFactor, ConditionSymptom


@dataclass
class ConditionMatch:
    condition: Condition
    matched_symptoms: list[ConditionSymptom]
    matched_risk_factors: list[ConditionRiskFactor]
    symptom_score: float
    risk_factor_score: float
    likelihood_score: float  # Posterior probability P(Condition | Evidence)
    severity: int
    urgency: int
    priority_score: float
    explanation: str
    posterior_probability: float = 0.0
    prior_probability: float = 0.0
    is_probability: bool = True
    absent_symptoms: list[Any] = field(default_factory=list)
    absent_risk_factors: list[Any] = field(default_factory=list)
    unrecorded_findings: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    conflicting_evidence: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _normalize_name(value: str) -> str:
    return value.strip().casefold() if value else ""


def _safe_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def rank_conditions(
    conditions: list[Condition],
    supplied_symptoms: list[str],
    supplied_risk_factors: list[str],
    negative_symptoms: list[str] | None = None,
    negative_risk_factors: list[str] | None = None,
    use_bayesian: bool = True,
) -> list[ConditionMatch]:
    """
    Ranks candidate conditions using Bayesian diagnostic inference while
    preserving the ConditionMatch interface for existing components.
    """
    normalized_symptoms = {_normalize_name(item) for item in supplied_symptoms if item and str(item).strip()}
    normalized_risk_factors = {_normalize_name(item) for item in supplied_risk_factors if item and str(item).strip()}

    if not use_bayesian:
        # Fallback heuristic path if explicitly requested
        ranked_heuristic: list[ConditionMatch] = []
        for condition in conditions:
            matched_syms = [
                rel for rel in condition.symptoms if rel.symptom and _normalize_name(rel.symptom.name) in normalized_symptoms
            ]
            matched_risks = [
                rel for rel in condition.risk_factors if rel.risk_factor and _normalize_name(rel.risk_factor.name) in normalized_risk_factors
            ]
            if not matched_syms:
                continue

            total_sym_w = sum(_safe_float(item.weight) for item in condition.symptoms)
            total_risk_w = sum(_safe_float(item.weight) for item in condition.risk_factors)
            matched_sym_w = sum(_safe_float(item.weight) for item in matched_syms)
            matched_risk_w = sum(_safe_float(item.weight) for item in matched_risks)

            sym_score = (matched_sym_w / total_sym_w) if total_sym_w else 0.0
            risk_score = (matched_risk_w / total_risk_w) if total_risk_w else 0.0
            likelihood = round((sym_score * 0.70) + (risk_score * 0.30), 4)

            sev = int(condition.severity or 1)
            urg = int(condition.urgency or 1)
            prio = round(
                (likelihood * 0.60) + ((sev / 10.0) * 1.0) + ((urg / 10.0) * 1.0) + (risk_score * 0.20),
                4,
            )

            ranked_heuristic.append(
                ConditionMatch(
                    condition=condition,
                    matched_symptoms=matched_syms,
                    matched_risk_factors=matched_risks,
                    symptom_score=sym_score,
                    risk_factor_score=risk_score,
                    likelihood_score=likelihood,
                    severity=sev,
                    urgency=urg,
                    priority_score=prio,
                    explanation=(
                        f"Heuristic score based on relational weights. Matched symptom score: {sym_score:.2f}, "
                        f"risk score: {risk_score:.2f}."
                    ),
                    posterior_probability=likelihood,
                    prior_probability=0.0,
                    is_probability=False,
                )
            )
        ranked_heuristic.sort(key=lambda item: (-item.priority_score, -item.likelihood_score, item.condition.name.casefold()))
        return ranked_heuristic

    # Execute Bayesian inference
    bayesian_results = run_bayesian_inference(
        conditions=conditions,
        positive_symptoms=supplied_symptoms,
        positive_risk_factors=supplied_risk_factors,
        negative_symptoms=negative_symptoms,
        negative_risk_factors=negative_risk_factors,
    )

    ranked: list[ConditionMatch] = []
    for b_res in bayesian_results:
        cond = b_res.condition

        # Identify condition relation objects corresponding to matched findings
        matched_symptoms_rels = [
            rel for rel in cond.symptoms if rel.symptom and _normalize_name(rel.symptom.name) in normalized_symptoms
        ]
        matched_risk_rels = [
            rel for rel in cond.risk_factors if rel.risk_factor and _normalize_name(rel.risk_factor.name) in normalized_risk_factors
        ]

        # Only retain candidates that have positive evidence or substantial posterior probability (> 1%)
        if not matched_symptoms_rels and b_res.posterior_probability < 0.01:
            continue

        sym_score = len(matched_symptoms_rels) / max(len(cond.symptoms), 1)
        risk_score = len(matched_risk_rels) / max(len(cond.risk_factors), 1)

        ranked.append(
            ConditionMatch(
                condition=cond,
                matched_symptoms=matched_symptoms_rels,
                matched_risk_factors=matched_risk_rels,
                symptom_score=sym_score,
                risk_factor_score=risk_score,
                likelihood_score=b_res.posterior_probability,
                severity=b_res.severity,
                urgency=b_res.urgency,
                priority_score=b_res.priority_score,
                explanation=b_res.explanation,
                posterior_probability=b_res.posterior_probability,
                prior_probability=b_res.prior_probability,
                is_probability=b_res.is_calibrated_probability,
                absent_symptoms=b_res.absent_symptoms,
                absent_risk_factors=b_res.absent_risk_factors,
                unrecorded_findings=b_res.unrecorded_findings,
                supporting_evidence=b_res.supporting_evidence,
                conflicting_evidence=b_res.conflicting_evidence,
                limitations=b_res.limitations,
            )
        )

    # Sort candidates by posterior probability descending, then triage priority score
    ranked.sort(key=lambda item: (-item.posterior_probability, -item.priority_score, item.condition.name.casefold()))
    return ranked
