from __future__ import annotations

from .ranking import rank_conditions
from .schemas import EvaluationResponse, MatchedFactor, PatientInput, RankedCondition, TestRecommendationResult, TreatmentRecommendationResult
from .services import KnowledgeRepository
from .test_recommendations import build_aggregate_test_recommendations
from .treatment_recommendations import build_treatment_recommendations


def _normalize_risk_factors(data):
    if isinstance(data, dict):
        return list(data.keys())
    return list(data or [])


def evaluate_patient(db, patient: PatientInput) -> EvaluationResponse:
    repository = KnowledgeRepository(db)
    patient_symptoms = list(patient.symptoms)
    patient_risk_factors = _normalize_risk_factors(patient.risk_factors)
    conditions = repository.conditions_with_relations()
    ranked_matches = rank_conditions(conditions, patient_symptoms, patient_risk_factors)

    ranked_conditions: list[RankedCondition] = []
    for match in ranked_matches:
        condition = match.condition
        recommended_tests = []
        for test in sorted(condition.tests, key=lambda item: (item.priority, item.test.name.casefold())):
            recommended_tests.append(
                {
                    "test_id": test.test.test_id,
                    "name": test.test.name,
                    "description": test.test.description,
                    "purpose": test.purpose or test.test.purpose,
                    "priority": test.priority,
                    "associated_conditions": [condition.name],
                }
            )
        treatments = [
            {
                "treatment_id": rel.treatment.treatment_id,
                "name": rel.treatment.name,
                "description": rel.treatment.description,
                "treatment_type": rel.treatment.treatment_type,
                "priority": rel.priority,
                "notes": rel.notes,
                "associated_condition": condition.name,
            }
            for rel in sorted(condition.treatments, key=lambda item: (item.priority, item.treatment.name.casefold()))
        ]
        ranked_conditions.append(
            RankedCondition(
                condition=condition.name,
                likelihood_score=match.likelihood_score,
                severity=match.severity,
                urgency=match.urgency,
                priority_score=match.priority_score,
                matched_symptoms=[MatchedFactor(name=relation.symptom.name, weight=float(relation.weight)) for relation in match.matched_symptoms],
                matched_risk_factors=[MatchedFactor(name=relation.risk_factor.name, weight=float(relation.weight)) for relation in match.matched_risk_factors],
                recommended_tests=[TestRecommendationResult(**item) for item in recommended_tests],
                treatments=[TreatmentRecommendationResult(**item) for item in treatments],
                explanation=match.explanation,
            )
        )

    return EvaluationResponse(
        disclaimer=(
            "This is an initial software ranking model for physician support only; it is not a medically validated "
            "diagnostic probability model."
        ),
        ranked_conditions=ranked_conditions,
    )
