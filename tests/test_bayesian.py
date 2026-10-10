import pytest
from decimal import Decimal

from app.bayesian import run_bayesian_inference
from app.models import Condition, ConditionRiskFactor, ConditionSymptom, Symptom, RiskFactor


def test_hand_calculated_bayesian_example():
    """
    Mathematically verifiable two-condition Bayesian test case:
    Condition A: Prior = 0.60, P(Symptom | A) = 0.80
    Condition B: Prior = 0.40, P(Symptom | B) = 0.20
    Observed: Symptom present.

    Unnormalized posterior:
    A: 0.60 * 0.80 = 0.48
    B: 0.40 * 0.20 = 0.08
    Total = 0.56

    Normalized posterior:
    P(A | Symptom) = 0.48 / 0.56 = 0.8571 (85.71%)
    P(B | Symptom) = 0.08 / 0.56 = 0.1429 (14.29%)
    """
    sym = Symptom(symptom_id=1, name="Fever")

    cond_a = Condition(
        condition_id=1,
        name="Condition A",
        prior_probability=Decimal("0.60"),
        severity=5,
        urgency=5,
    )
    cond_a.symptoms = [
        ConditionSymptom(condition_id=1, symptom_id=1, symptom=sym, weight=1.0, sensitivity=Decimal("0.80"))
    ]
    cond_a.risk_factors = []

    cond_b = Condition(
        condition_id=2,
        name="Condition B",
        prior_probability=Decimal("0.40"),
        severity=5,
        urgency=5,
    )
    cond_b.symptoms = [
        ConditionSymptom(condition_id=2, symptom_id=1, symptom=sym, weight=1.0, sensitivity=Decimal("0.20"))
    ]
    cond_b.risk_factors = []

    results = run_bayesian_inference(
        conditions=[cond_a, cond_b],
        positive_symptoms=["Fever"],
        positive_risk_factors=[],
    )

    assert len(results) == 2
    res_a = next(r for r in results if r.condition.name == "Condition A")
    res_b = next(r for r in results if r.condition.name == "Condition B")

    assert pytest.approx(res_a.posterior_probability, abs=0.01) == 0.8571
    assert pytest.approx(res_b.posterior_probability, abs=0.01) == 0.1429
    assert pytest.approx(res_a.posterior_probability + res_b.posterior_probability, abs=0.001) == 1.0


def test_posterior_probabilities_normalize_to_one():
    """Verify that posterior probabilities across candidate conditions sum to 1.0."""
    sym1 = Symptom(symptom_id=1, name="Cough")
    sym2 = Symptom(symptom_id=2, name="Fever")

    cond1 = Condition(condition_id=1, name="C1", prior_probability=Decimal("0.1"), severity=5, urgency=5)
    cond1.symptoms = [ConditionSymptom(condition_id=1, symptom_id=1, symptom=sym1, weight=1.0, sensitivity=Decimal("0.85"))]
    cond1.risk_factors = []

    cond2 = Condition(condition_id=2, name="C2", prior_probability=Decimal("0.2"), severity=6, urgency=4)
    cond2.symptoms = [ConditionSymptom(condition_id=2, symptom_id=2, symptom=sym2, weight=1.0, sensitivity=Decimal("0.70"))]
    cond2.risk_factors = []

    cond3 = Condition(condition_id=3, name="C3", prior_probability=Decimal("0.3"), severity=3, urgency=2)
    cond3.symptoms = [
        ConditionSymptom(condition_id=3, symptom_id=1, symptom=sym1, weight=1.0, sensitivity=Decimal("0.40")),
        ConditionSymptom(condition_id=3, symptom_id=2, symptom=sym2, weight=1.0, sensitivity=Decimal("0.50")),
    ]
    cond3.risk_factors = []

    results = run_bayesian_inference([cond1, cond2, cond3], ["Cough"], [])
    total_post = sum(r.posterior_probability for r in results)
    assert pytest.approx(total_post, abs=0.01) == 1.0


def test_unrecorded_finding_is_not_treated_as_confirmed_negative():
    """
    CRITICAL MEDICAL PRINCIPLE:
    An unrecorded finding must NOT be penalized as a negative finding.
    If Fever is unrecorded, Condition with Fever must have significantly HIGHER
    probability than if Fever is explicitly confirmed absent.
    """
    fever = Symptom(symptom_id=1, name="Fever")
    cough = Symptom(symptom_id=2, name="Cough")

    # Pneumonia strongly presents with both Fever (sens: 0.90) and Cough (sens: 0.90)
    pneu = Condition(condition_id=1, name="Pneumonia", prior_probability=Decimal("0.5"), severity=8, urgency=7)
    pneu.symptoms = [
        ConditionSymptom(condition_id=1, symptom_id=1, symptom=fever, weight=1.0, sensitivity=Decimal("0.90")),
        ConditionSymptom(condition_id=1, symptom_id=2, symptom=cough, weight=1.0, sensitivity=Decimal("0.90")),
    ]
    pneu.risk_factors = []

    # Bronchitis presents with Cough (sens: 0.85) but rarely Fever (sens: 0.15)
    bron = Condition(condition_id=2, name="Bronchitis", prior_probability=Decimal("0.5"), severity=4, urgency=3)
    bron.symptoms = [
        ConditionSymptom(condition_id=2, symptom_id=1, symptom=fever, weight=1.0, sensitivity=Decimal("0.15")),
        ConditionSymptom(condition_id=2, symptom_id=2, symptom=cough, weight=1.0, sensitivity=Decimal("0.85")),
    ]
    bron.risk_factors = []

    # Scenario 1: Patient has Cough. Fever is UNRECORDED (unknown).
    results_unrecorded = run_bayesian_inference(
        conditions=[pneu, bron],
        positive_symptoms=["Cough"],
        positive_risk_factors=[],
        negative_symptoms=[],  # Empty negatives: Fever is unknown
    )
    pneu_unrecorded = next(r for r in results_unrecorded if r.condition.name == "Pneumonia")

    # Scenario 2: Patient has Cough. Fever is CONFIRMED ABSENT (explicit negative).
    results_negative = run_bayesian_inference(
        conditions=[pneu, bron],
        positive_symptoms=["Cough"],
        positive_risk_factors=[],
        negative_symptoms=["Fever"],  # Confirmed absent Fever
    )
    pneu_negative = next(r for r in results_negative if r.condition.name == "Pneumonia")

    # When Fever is confirmed absent, Pneumonia's likelihood must drop sharply relative to Bronchitis
    assert pneu_unrecorded.posterior_probability > pneu_negative.posterior_probability
    assert pneu_negative.posterior_probability < 0.30


def test_missing_priors_use_uniform_prior_with_limitations_flagged():
    """When condition prior is unrecorded, a uniform uninformative prior is used and flagged."""
    sym = Symptom(symptom_id=1, name="Headache")
    c1 = Condition(condition_id=1, name="Migraine", prior_probability=None, severity=5, urgency=4)
    c1.symptoms = [ConditionSymptom(condition_id=1, symptom_id=1, symptom=sym, weight=1.0, sensitivity=Decimal("0.80"))]
    c1.risk_factors = []

    c2 = Condition(condition_id=2, name="Tension Headache", prior_probability=None, severity=3, urgency=2)
    c2.symptoms = [ConditionSymptom(condition_id=2, symptom_id=1, symptom=sym, weight=1.0, sensitivity=Decimal("0.80"))]
    c2.risk_factors = []

    results = run_bayesian_inference([c1, c2], ["Headache"], [])
    for r in results:
        assert not r.is_prior_configured
        assert any("prior probability is not clinically calibrated" in lim for lim in r.limitations)
        assert pytest.approx(r.prior_probability, abs=0.01) == 0.5


def test_separation_of_likelihood_and_severity_urgency():
    """Changing severity or urgency must alter triage priority score, but MUST NOT alter posterior probability."""
    sym = Symptom(symptom_id=1, name="Chest pain")

    c_mild = Condition(condition_id=1, name="Costochondritis", prior_probability=Decimal("0.5"), severity=2, urgency=2)
    c_mild.symptoms = [ConditionSymptom(condition_id=1, symptom_id=1, symptom=sym, weight=1.0, sensitivity=Decimal("0.70"))]
    c_mild.risk_factors = []

    c_severe = Condition(condition_id=2, name="Aortic Dissection", prior_probability=Decimal("0.5"), severity=10, urgency=10)
    c_severe.symptoms = [ConditionSymptom(condition_id=2, symptom_id=1, symptom=sym, weight=1.0, sensitivity=Decimal("0.70"))]
    c_severe.risk_factors = []

    results = run_bayesian_inference([c_mild, c_severe], ["Chest pain"], [])
    r_mild = next(r for r in results if r.condition.name == "Costochondritis")
    r_severe = next(r for r in results if r.condition.name == "Aortic Dissection")

    # Identical priors and sensitivities -> identical posterior probabilities!
    assert pytest.approx(r_mild.posterior_probability, abs=0.01) == r_severe.posterior_probability

    # But severity & urgency create distinct triage priority scores!
    assert r_severe.priority_score > r_mild.priority_score

