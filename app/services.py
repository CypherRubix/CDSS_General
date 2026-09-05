from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Condition,
    ConditionRiskFactor,
    ConditionSymptom,
    ConditionTest,
    ConditionTreatment,
    RiskFactor,
    Symptom,
    Test,
    Treatment,
)


class ResourceNotFoundError(Exception):
    pass


class DuplicateResourceError(Exception):
    pass


class InvalidInputError(Exception):
    pass


class KnowledgeRepository:
    """Data access layer for the CDSS knowledge tables."""

    def __init__(self, db: Session):
        self.db = db

    def conditions(self) -> list[Condition]:
        statement = select(Condition).order_by(Condition.name)
        return list(self.db.scalars(statement).all())

    def conditions_with_relations(self) -> list[Condition]:
        statement = select(Condition).options(
            selectinload(Condition.symptoms).selectinload(ConditionSymptom.symptom),
            selectinload(Condition.risk_factors).selectinload(ConditionRiskFactor.risk_factor),
            selectinload(Condition.tests).selectinload(ConditionTest.test),
            selectinload(Condition.treatments).selectinload(ConditionTreatment.treatment),
        )
        return list(self.db.scalars(statement).unique().all())

    def symptoms(self) -> list[Symptom]:
        return list(self.db.scalars(select(Symptom).order_by(Symptom.name)).all())

    def risk_factors(self) -> list[RiskFactor]:
        return list(self.db.scalars(select(RiskFactor).order_by(RiskFactor.name)).all())

    def tests(self) -> list[Test]:
        return list(self.db.scalars(select(Test).order_by(Test.name)).all())

    def treatments(self) -> list[Treatment]:
        return list(self.db.scalars(select(Treatment).order_by(Treatment.name)).all())

    def get_condition(self, condition_id: int) -> Condition | None:
        return self.db.get(Condition, condition_id)

    def get_condition_by_name(self, name: str) -> Condition | None:
        return self.db.scalar(select(Condition).where(Condition.name == name))

    def get_symptom(self, symptom_id: int) -> Symptom | None:
        return self.db.get(Symptom, symptom_id)

    def get_symptom_by_name(self, name: str) -> Symptom | None:
        return self.db.scalar(select(Symptom).where(Symptom.name == name))

    def get_risk_factor(self, risk_factor_id: int) -> RiskFactor | None:
        return self.db.get(RiskFactor, risk_factor_id)

    def get_risk_factor_by_name(self, name: str) -> RiskFactor | None:
        return self.db.scalar(select(RiskFactor).where(RiskFactor.name == name))

    def get_test(self, test_id: int) -> Test | None:
        return self.db.get(Test, test_id)

    def get_test_by_name(self, name: str) -> Test | None:
        return self.db.scalar(select(Test).where(Test.name == name))

    def get_treatment(self, treatment_id: int) -> Treatment | None:
        return self.db.get(Treatment, treatment_id)

    def get_treatment_by_name(self, name: str) -> Treatment | None:
        return self.db.scalar(select(Treatment).where(Treatment.name == name))


def _lower(value: str | None) -> str:
    return (value or "").strip().casefold()


def _matching_name(values: Iterable[str], target: str) -> bool:
    return any(_lower(item) == _lower(target) for item in values)


from dataclasses import dataclass, field

from .ranking import rank_conditions as _rank_conditions


@dataclass
class LegacyTestRecommendation:
    name: str
    purpose: str | None = None
    type: str | None = None
    priority: int = 1
    evidence: list = field(default_factory=list)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


@dataclass
class LegacyRankedCondition:
    condition: str
    likelihood_score: float
    severity: float
    urgency: float
    clinical_priority_score: float
    matched_symptoms: list[str] = field(default_factory=list)
    relevant_risk_factors: list[str] = field(default_factory=list)
    recommended_tests: list[LegacyTestRecommendation] = field(default_factory=list)
    evidence: list = field(default_factory=list)
    explanation: str = ""

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


def rank_conditions_legacy(
    conditions: Iterable[Condition],
    symptoms: Iterable[str],
    risk_factors: Iterable[str],
) -> list[LegacyRankedCondition]:
    supplied_symptoms = {value.casefold().strip() for value in symptoms}
    supplied_risks = {value.casefold().strip() for value in risk_factors}
    ranked: list[LegacyRankedCondition] = []

    for condition in conditions:
        matched_symptom_relations = [
            relation for relation in condition.symptoms if relation.symptom.name.casefold() in supplied_symptoms
        ]
        matched_risk_relations = [
            relation for relation in condition.risk_factors if relation.risk_factor.name.casefold() in supplied_risks
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
        matched_names = [item.symptom.name for item in matched_symptom_relations]
        risk_names = [item.risk_factor.name for item in matched_risk_relations]

        ranked.append(
            LegacyRankedCondition(
                condition=condition.name,
                likelihood_score=likelihood,
                severity=severity,
                urgency=urgency,
                clinical_priority_score=priority,
                matched_symptoms=matched_names,
                relevant_risk_factors=risk_names,
                recommended_tests=[
                    LegacyTestRecommendation(
                        name=relation.test.name,
                        purpose=relation.purpose or relation.test.purpose,
                        type=relation.test.type,
                        priority=relation.priority,
                        evidence=[],
                    )
                    for relation in sorted(condition.tests, key=lambda item: item.priority)
                ],
                evidence=[],
                explanation=(
                    f"Matched {len(matched_names)} supplied symptom(s) with configurable contribution {symptom_score:.2f}; "
                    f"matched {len(risk_names)} risk factor(s) with contribution {risk_score:.2f}. "
                    f"The stored prior contribution is {prior_score:.4f}. Severity and urgency are applied separately to "
                    "clinical priority. These are ranking signals, not validated clinical probabilities."
                ),
            )
        )

    return sorted(ranked, key=lambda item: (-item.clinical_priority_score, -item.likelihood_score, item.condition))


# Backwards-compatible export expected by older code.
rank_conditions = rank_conditions_legacy

