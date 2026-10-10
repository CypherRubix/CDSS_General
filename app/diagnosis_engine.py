from __future__ import annotations

from .bayesian import calculate_diagnostic_uncertainty, evaluate_severity_and_safety, run_bayesian_inference
from .ranking import rank_conditions
from .schemas import (
    EvaluationResponse,
    MatchedFactor,
    PatientInput,
    RankedCondition,
    SeverityUrgencySafety,
    TestRecommendationResult,
    TreatmentRecommendationResult,
    UncertaintyMetrics,
)
from .services import KnowledgeRepository
from .test_selection import calculate_entropy, select_and_rank_tests


def _normalize_risk_factors(data):
    if isinstance(data, dict):
        return list(data.keys())
    return list(data or [])


def evaluate_patient(db, patient: PatientInput) -> EvaluationResponse:
    repository = KnowledgeRepository(db)
    patient_symptoms = list(patient.symptoms)
    patient_risk_factors = _normalize_risk_factors(patient.risk_factors)
    negative_symptoms = list(patient.negative_symptoms or [])
    negative_risk_factors = _normalize_risk_factors(patient.negative_risk_factors or [])
    completed_tests = list(patient.completed_tests or [])
    test_results = list(patient.test_results or [])

    # Collect completed test names from both completed_tests and test_results
    for t_res in test_results:
        t_name = getattr(t_res, "test_name", None) or (t_res.get("test_name") if isinstance(t_res, dict) else None)
        if t_name and t_name not in completed_tests:
            completed_tests.append(t_name)

    conditions = repository.conditions_with_relations()
    all_tests = repository.tests()
    all_symptoms = repository.symptoms()

    # 1. Run Bayesian diagnostic inference with sequential test results
    ranked_matches = rank_conditions(
        conditions=conditions,
        supplied_symptoms=patient_symptoms,
        supplied_risk_factors=patient_risk_factors,
        negative_symptoms=negative_symptoms,
        negative_risk_factors=negative_risk_factors,
        test_results=test_results,
    )

    candidates_with_probs = [
        (match.condition, match.posterior_probability)
        for match in ranked_matches
    ]

    # 2. Estimate diagnostic uncertainty
    cand_probs = [p for _, p in candidates_with_probs]
    cand_names = [c.name for c, _ in candidates_with_probs]
    uncertainty_res = calculate_diagnostic_uncertainty(
        probabilities=cand_probs,
        condition_names=cand_names,
        total_model_features_count=len(all_symptoms),
        recorded_features_count=len(patient_symptoms) + len(negative_symptoms),
    )

    # 3. Evaluate condition severity and clinical urgency safety
    raw_bayesian_results = run_bayesian_inference(
        conditions=conditions,
        positive_symptoms=patient_symptoms,
        positive_risk_factors=patient_risk_factors,
        negative_symptoms=negative_symptoms,
        negative_risk_factors=negative_risk_factors,
        test_results=test_results,
    )
    safety_res = evaluate_severity_and_safety(
        results=raw_bayesian_results,
        positive_symptoms=patient_symptoms,
    )

    # 4. Run Uncertainty-guided, severity-aware diagnostic test selection
    diag_tests_eval = select_and_rank_tests(
        conditions_with_probabilities=candidates_with_probs,
        all_tests=all_tests,
        completed_test_names=completed_tests,
        severity_weight=0.50,
    )

    test_eval_by_id = {t.test_id: t for t in diag_tests_eval}

    ranked_conditions: list[RankedCondition] = []
    for match in ranked_matches:
        condition = match.condition

        recommended_tests: list[TestRecommendationResult] = []
        for rel in sorted(condition.tests, key=lambda item: (item.priority, item.test.name.casefold())):
            test_obj = rel.test
            # Skip if test has already been completed or evaluated
            if any(test_obj.name.strip().casefold() == c.strip().casefold() for c in completed_tests):
                continue

            eval_info = test_eval_by_id.get(test_obj.test_id)
            info_gain = eval_info.information_gain if eval_info else None
            entropy_reduc = eval_info.expected_entropy_reduction if eval_info else None
            safety_boost = eval_info.safety_priority_boost if eval_info else None
            composite_utility = eval_info.composite_utility_score if eval_info else None
            is_ig_calc = eval_info.is_information_gain_calculated if eval_info else False
            missing_params = eval_info.missing_parameters if eval_info else True
            rationale_text = eval_info.rationale if eval_info else None
            discrim = eval_info.discriminates_between if eval_info else [condition.name]

            sens_val = float(rel.sensitivity) if rel.sensitivity is not None else (eval_info.sensitivity if eval_info else None)
            spec_val = float(rel.specificity) if rel.specificity is not None else (eval_info.specificity if eval_info else None)
            cost_val = float(rel.cost) if rel.cost is not None else (eval_info.cost if eval_info else None)

            recommended_tests.append(
                TestRecommendationResult(
                    test_id=test_obj.test_id,
                    name=test_obj.name,
                    description=test_obj.description,
                    purpose=rel.purpose or test_obj.purpose,
                    priority=rel.priority,
                    associated_conditions=[condition.name],
                    discriminates_between=discrim,
                    information_gain=info_gain,
                    expected_entropy_reduction=entropy_reduc,
                    safety_priority_boost=safety_boost,
                    composite_utility_score=composite_utility,
                    is_information_gain_calculated=is_ig_calc,
                    missing_parameters=missing_params,
                    sensitivity=sens_val,
                    specificity=spec_val,
                    cost=cost_val,
                    rationale=rationale_text,
                    limitations=eval_info.limitations if eval_info else [],
                )
            )

        treatments = [
            TreatmentRecommendationResult(
                treatment_id=rel.treatment.treatment_id,
                name=rel.treatment.name,
                description=rel.treatment.description,
                treatment_type=rel.treatment.treatment_type,
                priority=rel.priority,
                notes=rel.notes,
                associated_condition=condition.name,
            )
            for rel in sorted(condition.treatments, key=lambda item: (item.priority, item.treatment.name.casefold()))
        ]

        matched_symptoms_list = [
            MatchedFactor(name=rel.symptom.name, weight=float(rel.weight or 1.0), is_positive=True)
            for rel in match.matched_symptoms
        ]
        matched_risks_list = [
            MatchedFactor(name=rel.risk_factor.name, weight=float(rel.weight or 1.0), is_positive=True)
            for rel in match.matched_risk_factors
        ]
        absent_symptoms_list = [
            MatchedFactor(name=item.name, weight=item.weight, probability=item.probability, is_positive=False)
            for item in match.absent_symptoms
        ]
        absent_risks_list = [
            MatchedFactor(name=item.name, weight=item.weight, probability=item.probability, is_positive=False)
            for item in match.absent_risk_factors
        ]

        ranked_conditions.append(
            RankedCondition(
                condition=condition.name,
                likelihood_score=match.likelihood_score,
                posterior_probability=match.posterior_probability,
                prior_probability=match.prior_probability,
                is_probability=match.is_probability,
                severity=match.severity,
                urgency=match.urgency,
                priority_score=match.priority_score,
                is_high_severity_risk=match.is_high_severity_risk,
                matched_symptoms=matched_symptoms_list,
                matched_risk_factors=matched_risks_list,
                absent_symptoms=absent_symptoms_list,
                absent_risk_factors=absent_risks_list,
                unrecorded_findings=match.unrecorded_findings,
                supporting_evidence=match.supporting_evidence,
                conflicting_evidence=match.conflicting_evidence,
                recommended_tests=recommended_tests,
                treatments=treatments,
                explanation=match.explanation,
                limitations=match.limitations,
            )
        )

    # Build top global differential tests
    differential_tests = [
        TestRecommendationResult(
            test_id=t.test_id,
            name=t.name,
            description=t.description,
            purpose=t.purpose,
            priority=t.priority,
            associated_conditions=t.associated_conditions,
            discriminates_between=t.discriminates_between,
            information_gain=t.information_gain,
            expected_entropy_reduction=t.expected_entropy_reduction,
            safety_priority_boost=t.safety_priority_boost,
            composite_utility_score=t.composite_utility_score,
            is_information_gain_calculated=t.is_information_gain_calculated,
            missing_parameters=t.missing_parameters,
            sensitivity=t.sensitivity,
            specificity=t.specificity,
            cost=t.cost,
            rationale=t.rationale,
            limitations=t.limitations,
        )
        for t in diag_tests_eval[:6]
    ]

    uncertainty_dto = UncertaintyMetrics(
        shannon_entropy_bits=uncertainty_res.shannon_entropy_bits,
        normalized_entropy=uncertainty_res.normalized_entropy,
        margin_of_separation=uncertainty_res.margin_of_separation,
        is_uncertain=uncertainty_res.is_uncertain,
        uncertainty_threshold=uncertainty_res.uncertainty_threshold,
        leading_competing_diagnoses=uncertainty_res.leading_competing_diagnoses,
        missingness_ratio=uncertainty_res.missingness_ratio,
        interpretation=uncertainty_res.interpretation,
    )

    safety_dto = SeverityUrgencySafety(
        high_severity_conditions_at_risk=safety_res.high_severity_conditions_at_risk,
        critical_escalation_flag=safety_res.critical_escalation_flag,
        urgent_findings=safety_res.urgent_findings,
        safety_rationale=safety_res.safety_rationale,
    )

    return EvaluationResponse(
        disclaimer=(
            "Research Prototype: Combines Bayesian inference, explicit uncertainty estimation (entropy), "
            "independent severity/urgency assessment, and Information Gain test selection. "
            "Model parameters reflect database configuration and are not clinically validated."
        ),
        ranked_conditions=ranked_conditions,
        differential_tests=differential_tests,
        diagnostic_entropy=uncertainty_res.shannon_entropy_bits,
        uncertainty_metrics=uncertainty_dto,
        safety_assessment=safety_dto,
        algorithm_used="Bayesian Inference + Information Gain + Severity Constraints",
    )
