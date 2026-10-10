from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Condition, ConditionSymptom, ConditionTest, Symptom, Test
from app.schemas import SequentialEvaluationRequest, TestResultInput
from app.sequential_workflow import run_sequential_step


def build_test_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def test_sequential_workflow_updates_posteriors_and_entropy():
    """
    Verifies that the sequential workflow iteratively updates posterior
    probabilities and reduces diagnostic entropy upon receiving test results.
    """
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        sym_cough = Symptom(symptom_id=1, name="Cough")
        sym_fever = Symptom(symptom_id=2, name="Fever")
        db.add_all([sym_cough, sym_fever])
        db.flush()

        test_xray = Test(test_id=101, name="Chest X-Ray", purpose="Detect consolidation")
        db.add(test_xray)
        db.flush()

        # Condition 1: Pneumonia (Prior 0.5, Cough sens 0.9, Fever sens 0.8, X-Ray sens 0.88, spec 0.85)
        c_pneu = Condition(condition_id=1, name="Pneumonia", prior_probability=Decimal("0.5"), severity=8, urgency=7)
        c_pneu.symptoms = [
            ConditionSymptom(condition_id=1, symptom_id=1, symptom=sym_cough, weight=1.0, sensitivity=Decimal("0.90")),
            ConditionSymptom(condition_id=1, symptom_id=2, symptom=sym_fever, weight=1.0, sensitivity=Decimal("0.80")),
        ]
        c_pneu.tests = [
            ConditionTest(condition_id=1, test_id=101, test=test_xray, priority=1, sensitivity=Decimal("0.88"), specificity=Decimal("0.85"))
        ]

        # Condition 2: Bronchitis (Prior 0.5, Cough sens 0.9, Fever sens 0.2, X-Ray sens 0.10, spec 0.90)
        c_bron = Condition(condition_id=2, name="Bronchitis", prior_probability=Decimal("0.5"), severity=4, urgency=3)
        c_bron.symptoms = [
            ConditionSymptom(condition_id=2, symptom_id=1, symptom=sym_cough, weight=1.0, sensitivity=Decimal("0.90")),
            ConditionSymptom(condition_id=2, symptom_id=2, symptom=sym_fever, weight=1.0, sensitivity=Decimal("0.20")),
        ]
        c_bron.tests = [
            ConditionTest(condition_id=2, test_id=101, test=test_xray, priority=2, sensitivity=Decimal("0.10"), specificity=Decimal("0.90"))
        ]

        db.add_all([c_pneu, c_bron])
        db.commit()

        # Step 1: Patient presents with Cough only. Ambiguity exists.
        req_step1 = SequentialEvaluationRequest(
            symptoms=["Cough"],
            risk_factors=[],
            negative_symptoms=[],
            test_results=[],
        )
        res_step1 = run_sequential_step(db, req_step1)

        assert res_step1.step_number == 1
        assert res_step1.next_recommended_test is not None
        assert res_step1.next_recommended_test.name == "Chest X-Ray"
        assert not res_step1.stopping_criterion_met

        initial_entropy = res_step1.evaluation.diagnostic_entropy
        assert initial_entropy is not None
        assert initial_entropy > 0.5

        # Step 2: Clinician performs Chest X-Ray and records POSITIVE result
        req_step2 = SequentialEvaluationRequest(
            symptoms=["Cough"],
            risk_factors=[],
            negative_symptoms=[],
            test_results=[TestResultInput(test_name="Chest X-Ray", result="positive")],
        )
        res_step2 = run_sequential_step(db, req_step2)

        assert res_step2.step_number == 2
        # After positive X-Ray, Pneumonia must dominate
        top_cand = res_step2.evaluation.ranked_conditions[0]
        assert top_cand.condition == "Pneumonia"
        assert top_cand.posterior_probability > 0.80

        # Residual entropy should have decreased significantly
        post_test_entropy = res_step2.evaluation.diagnostic_entropy
        assert post_test_entropy < initial_entropy
        assert res_step2.stopping_criterion_met


def test_sequential_workflow_negative_test_shifts_diagnosis():
    """
    Verifies that a negative test result shifts probability away from the target condition.
    """
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        sym_cough = Symptom(symptom_id=1, name="Cough")
        test_xray = Test(test_id=101, name="Chest X-Ray")
        db.add_all([sym_cough, test_xray])
        db.flush()

        c_pneu = Condition(condition_id=1, name="Pneumonia", prior_probability=Decimal("0.5"), severity=8, urgency=7)
        c_pneu.symptoms = [ConditionSymptom(condition_id=1, symptom_id=1, symptom=sym_cough, weight=1.0, sensitivity=Decimal("0.90"))]
        c_pneu.tests = [ConditionTest(condition_id=1, test_id=101, test=test_xray, priority=1, sensitivity=Decimal("0.88"), specificity=Decimal("0.85"))]

        c_bron = Condition(condition_id=2, name="Bronchitis", prior_probability=Decimal("0.5"), severity=4, urgency=3)
        c_bron.symptoms = [ConditionSymptom(condition_id=2, symptom_id=1, symptom=sym_cough, weight=1.0, sensitivity=Decimal("0.90"))]
        c_bron.tests = [ConditionTest(condition_id=2, test_id=101, test=test_xray, priority=2, sensitivity=Decimal("0.10"), specificity=Decimal("0.90"))]

        db.add_all([c_pneu, c_bron])
        db.commit()

        # Negative X-Ray outcome entered
        req = SequentialEvaluationRequest(
            symptoms=["Cough"],
            risk_factors=[],
            test_results=[TestResultInput(test_name="Chest X-Ray", result="negative")],
        )
        res = run_sequential_step(db, req)

        # Bronchitis should now have higher probability than Pneumonia
        cands = {c.condition: c.posterior_probability for c in res.evaluation.ranked_conditions}
        assert cands["Bronchitis"] > cands["Pneumonia"]

