from decimal import Decimal

from app.models import Condition, ConditionRiskFactor, ConditionSymptom, ConditionTest, Evidence, RiskFactor, Symptom, Test
from app.services import rank_conditions


def make_condition() -> Condition:
    evidence = Evidence(evidence_id=1, title="Demo reference", is_demo=True)
    condition = Condition(name="Demo condition", severity=Decimal("80"), urgency=Decimal("60"), prior_probability=Decimal("0.1"), is_demo=True)
    condition.symptoms = [ConditionSymptom(symptom=Symptom(name="fever"), weight=Decimal("2"), evidence=evidence)]
    condition.risk_factors = [ConditionRiskFactor(risk_factor=RiskFactor(name="smoking", type="lifestyle"), weight=Decimal("1"), evidence=evidence)]
    condition.tests = [ConditionTest(test=Test(name="demo test", type="laboratory"), priority=1, evidence=evidence)]
    return condition


def test_ranking_is_explainable_and_recommends_tests() -> None:
    result = rank_conditions([make_condition()], ["fever"], ["smoking"])
    assert result[0].condition == "Demo condition"
    assert result[0].likelihood_score == 3.1
    assert result[0].clinical_priority_score > result[0].likelihood_score
    assert result[0].matched_symptoms == ["fever"]
    assert result[0].relevant_risk_factors == ["smoking"]
    assert result[0].recommended_tests[0].name == "demo test"
    assert "configurable" in result[0].explanation
