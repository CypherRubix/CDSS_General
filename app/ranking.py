from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Condition, ConditionRiskFactor, ConditionSymptom

SYMPTOM_WEIGHT = 0.70
RISK_FACTOR_WEIGHT = 0.30
PRIORITY_SYMPTOM_WEIGHT = 0.60
PRIORITY_RISK_WEIGHT = 0.20
PRIORITY_SEVERITY_WEIGHT = 0.10
PRIORITY_URGENCY_WEIGHT = 0.10


@dataclass
class ConditionMatch:
    condition: Condition
    matched_symptoms: list[ConditionSymptom]
    matched_risk_factors: list[ConditionRiskFactor]
    symptom_score: float
    risk_factor_score: float
    likelihood_score: float
    severity: int
    urgency: int
    priority_score: float
    explanation: str


def _normalize_name(value: str) -> str:
    return value.strip().casefold()


def _safe_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _compute_score_for_relations(relations: list[Any]) -> float:
    return sum(_safe_float(item.weight) for item in relations)


def rank_conditions(
    conditions: list[Condition],
    supplied_symptoms: list[str],
    supplied_risk_factors: list[str],
) -> list[ConditionMatch]:
    normalized_symptoms = {_normalize_name(item) for item in supplied_symptoms if item and str(item).strip()}
    normalized_risk_factors = {_normalize_name(item) for item in supplied_risk_factors if item and str(item).strip()}
    ranked: list[ConditionMatch] = []

    for condition in conditions:
        matched_symptoms = [
            relation for relation in condition.symptoms if _normalize_name(relation.symptom.name) in normalized_symptoms
        ]
        matched_risk_factors = [
            relation for relation in condition.risk_factors if _normalize_name(relation.risk_factor.name) in normalized_risk_factors
        ]
        if not matched_symptoms:
            continue

        total_symptom_weight = _compute_score_for_relations(condition.symptoms)
        total_risk_weight = _compute_score_for_relations(condition.risk_factors)
        matched_symptom_weight = _compute_score_for_relations(matched_symptoms)
        matched_risk_weight = _compute_score_for_relations(matched_risk_factors)

        symptom_score = (matched_symptom_weight / total_symptom_weight) if total_symptom_weight else 0.0
        risk_factor_score = (matched_risk_weight / total_risk_weight) if total_risk_weight else 0.0
        likelihood_score = round((symptom_score * SYMPTOM_WEIGHT) + (risk_factor_score * RISK_FACTOR_WEIGHT), 4)

        severity = int(condition.severity or 1)
        urgency = int(condition.urgency or 1)
        priority_score = round(
            (likelihood_score * PRIORITY_SYMPTOM_WEIGHT)
            + ((severity / 10) * PRIORITY_SEVERITY_WEIGHT * 10)
            + ((urgency / 10) * PRIORITY_URGENCY_WEIGHT * 10)
            + (risk_factor_score * PRIORITY_RISK_WEIGHT),
            4,
        )
        explanation = (
            "This result is based on the weighted relationship values explicitly stored for the condition, "
            "not a medically validated probability model. The symptom match contributes "
            f"{symptom_score:.2f} of the symptom signal and the risk-factor match contributes "
            f"{risk_factor_score:.2f}. Severity ({severity}) and urgency ({urgency}) are treated as separate "
            "priority considerations."
        )

        ranked.append(
            ConditionMatch(
                condition=condition,
                matched_symptoms=matched_symptoms,
                matched_risk_factors=matched_risk_factors,
                symptom_score=symptom_score,
                risk_factor_score=risk_factor_score,
                likelihood_score=likelihood_score,
                severity=severity,
                urgency=urgency,
                priority_score=priority_score,
                explanation=explanation,
            )
        )

    ranked.sort(key=lambda item: (-item.priority_score, -item.likelihood_score, item.condition.name.casefold()))
    return ranked
