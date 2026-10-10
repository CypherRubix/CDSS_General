from __future__ import annotations

from sqlalchemy.orm import Session

from .diagnosis_engine import evaluate_patient
from .schemas import (
    PatientInput,
    SequentialEvaluationRequest,
    SequentialStepResponse,
    TestRecommendationResult,
)


def run_sequential_step(db: Session, request: SequentialEvaluationRequest) -> SequentialStepResponse:
    """
    Executes a single step in the sequential diagnostic workflow:
    1. Formulates patient findings and accumulated test results into PatientInput.
    2. Runs Bayesian inference and entropy estimation.
    3. Evaluates stopping criteria (low entropy, dominant probability, or no remaining tests).
    4. Proposes the next highest Information Gain test if uncertainty remains.
    """
    completed_test_names = [t.test_name for t in request.test_results]

    patient = PatientInput(
        symptoms=request.symptoms,
        risk_factors=request.risk_factors,
        negative_symptoms=request.negative_symptoms,
        completed_tests=completed_test_names,
        test_results=request.test_results,
        demographics=request.demographics,
    )

    evaluation = evaluate_patient(db, patient)

    step_number = len(request.test_results) + 1
    ranked = evaluation.ranked_conditions
    diff_tests = evaluation.differential_tests
    uncertainty = evaluation.uncertainty_metrics

    # Check diagnostic stopping criteria
    stopping_met = False
    stopping_rationale = ""
    next_test: TestRecommendationResult | None = None

    if not ranked:
        stopping_met = True
        stopping_rationale = "No candidate conditions matched the provided clinical findings."
    else:
        top_prob = ranked[0].posterior_probability or 0.0
        entropy_val = uncertainty.shannon_entropy_bits if uncertainty else 1.0

        if top_prob >= 0.85:
            stopping_met = True
            stopping_rationale = (
                f"Diagnostic convergence reached: Leading condition '{ranked[0].condition}' "
                f"has reached {top_prob:.1%} posterior probability with low residual uncertainty ({entropy_val:.2f} bits)."
            )
        elif entropy_val < 0.25:
            stopping_met = True
            stopping_rationale = (
                f"Uncertainty minimized: Residual entropy is {entropy_val:.2f} bits. "
                "Differential ambiguity resolved."
            )
        elif not diff_tests:
            stopping_met = True
            stopping_rationale = (
                "No further indicated diagnostic tests with positive information gain remain in the database."
            )
        else:
            # Propose the top ranked differential test
            next_test = diff_tests[0]
            stopping_met = False
            stopping_rationale = (
                f"Significant diagnostic uncertainty persists (entropy: {entropy_val:.2f} bits). "
                f"Recommended test '{next_test.name}' will maximize expected information gain."
            )

    return SequentialStepResponse(
        step_number=step_number,
        evaluation=evaluation,
        next_recommended_test=next_test,
        stopping_criterion_met=stopping_met,
        stopping_rationale=stopping_rationale,
    )

