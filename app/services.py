from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Condition,
    ConditionRiskFactor,
    ConditionSymptom,
    ConditionTest,
    RiskFactor,
    Symptom,
    Test,
)
from .schemas import EvidenceResponse, RankedCondition, TestRecommendation


class KnowledgeRepository:
    """Read-only access to the medical knowledge tables."""

    def __init__(self, db: Session):
        self.db = db

    def conditions(self) -> list[Condition]:
        statement = select(Condition).options(
            selectinload(Condition.symptoms).selectinload(ConditionSymptom.symptom),
            selectinload(Condition.symptoms).selectinload(ConditionSymptom.evidence),
            selectinload(Condition.risk_factors).selectinload(ConditionRiskFactor.risk_factor),
            selectinload(Condition.risk_factors).selectinload(ConditionRiskFactor.evidence),
            selectinload(Condition.tests).selectinload(ConditionTest.test),
            selectinload(Condition.tests).selectinload(ConditionTest.evidence),
        )
        return list(self.db.scalars(statement).unique().all())

    def symptoms(self) -> list[Symptom]:
        return list(self.db.scalars(select(Symptom).order_by(Symptom.name)).all())

    def risk_factors(self) -> list[RiskFactor]:
        return list(self.db.scalars(select(RiskFactor).order_by(RiskFactor.name)).all())

    def tests(self) -> list[Test]:
        return list(self.db.scalars(select(Test).order_by(Test.name)).all())


def evidence_response(evidence: Iterable) -> list[EvidenceResponse]:
    seen: set[int] = set()
    result: list[EvidenceResponse] = []
    for item in evidence:
        if item is None or item.evidence_id in seen:
            continue
        seen.add(item.evidence_id)
        result.append(EvidenceResponse.model_validate(item, from_attributes=True))
    return result


def recommendation_response(condition) -> list[TestRecommendation]:
    return [
        TestRecommendation(
            name=relation.test.name,
            purpose=relation.purpose or relation.test.purpose,
            type=relation.test.type,
            priority=relation.priority,
            evidence=evidence_response([relation.evidence]),
        )
        for relation in sorted(condition.tests, key=lambda item: item.priority)
    ]


def rank_conditions(
    conditions: Iterable[Condition],
    symptoms: Iterable[str],
    risk_factors: Iterable[str],
) -> list[RankedCondition]:
    supplied_symptoms = {value.casefold().strip() for value in symptoms}
    supplied_risks = {value.casefold().strip() for value in risk_factors}
    ranked: list[RankedCondition] = []

    for condition in conditions:
        matched_symptom_relations = [
            relation for relation in condition.symptoms
            if relation.symptom.name.casefold() in supplied_symptoms
        ]
        matched_risk_relations = [
            relation for relation in condition.risk_factors
            if relation.risk_factor.name.casefold() in supplied_risks
        ]
        if not matched_symptom_relations:
            continue

        symptom_score = sum(float(item.weight) for item in matched_symptom_relations)
        risk_score = sum(float(item.weight) for item in matched_risk_relations)
        prior_score = float(condition.prior_probability or 0)
        likelihood = round(symptom_score + risk_score + prior_score, 4)
        severity = float(condition.severity)
        urgency = float(condition.urgency)
        priority = round(likelihood * (1 + (severity + urgency) / 200), 4)
        all_evidence = [
            *(item.evidence for item in matched_symptom_relations),
            *(item.evidence for item in matched_risk_relations),
            *(item.evidence for item in condition.tests),
        ]
        matched_names = [item.symptom.name for item in matched_symptom_relations]
        risk_names = [item.risk_factor.name for item in matched_risk_relations]
        explanation = (
            f"Matched {len(matched_names)} supplied symptom(s) with a configurable "
            f"symptom contribution of {symptom_score:.2f}; matched {len(risk_names)} "
            f"risk factor(s) with a configurable contribution of {risk_score:.2f}. "
            f"The stored prior contribution is {prior_score:.4f}. Severity and urgency "
            "are applied separately to clinical priority. These are ranking signals, "
            "not validated clinical probabilities."
        )
        ranked.append(
            RankedCondition(
                condition=condition.name,
                likelihood_score=likelihood,
                severity=severity,
                urgency=urgency,
                clinical_priority_score=priority,
                matched_symptoms=matched_names,
                relevant_risk_factors=risk_names,
                recommended_tests=recommendation_response(condition),
                evidence=evidence_response(all_evidence),
                explanation=explanation,
            )
        )

    return sorted(ranked, key=lambda item: (-item.clinical_priority_score, -item.likelihood_score, item.condition))
