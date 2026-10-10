from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .models import Condition, ConditionTest, Test

EPSILON = 1e-9


@dataclass
class DiagnosticTestEvaluation:
    test_id: int
    name: str
    description: str | None
    purpose: str | None
    priority: int
    associated_conditions: list[str]
    discriminates_between: list[str]
    sensitivity: float | None
    specificity: float | None
    cost: float | None
    information_gain: float | None  # in bits
    expected_entropy_reduction: float | None
    safety_priority_boost: float | None
    composite_utility_score: float | None
    is_information_gain_calculated: bool
    missing_parameters: bool
    rationale: str
    limitations: list[str] = field(default_factory=list)


def calculate_entropy(probabilities: list[float]) -> float:
    """Calculates Shannon entropy H(C) = -sum(P(c) * log2(P(c))) in bits."""
    entropy = 0.0
    for p in probabilities:
        if p > EPSILON:
            entropy -= p * math.log2(p)
    return entropy


def select_and_rank_tests(
    conditions_with_probabilities: list[tuple[Condition, float]],
    all_tests: list[Test],
    completed_test_names: list[str] | None = None,
    severity_weight: float = 0.40,
    cost_weight: float = 0.0,
) -> list[DiagnosticTestEvaluation]:
    """
    Evaluates and ranks candidate diagnostic tests using Expected Information Gain (IG)
    combined with severity safety constraints.

    IG(T) = H(C) - E[H(C | T)]
    where H(C) is current Shannon diagnostic entropy across candidate conditions,
    and E[H(C | T)] is expected posterior entropy after observing the test result.

    Safety-Aware Adjustment:
    Composite Utility = IG(T) + severity_weight * Safety_Boost - cost_weight * Cost
    where Safety_Boost = max_{c in Target(T)} [ (Severity(c) / 10) * P(c) ]
    ensures high-severity conditions (e.g. Pneumonia, Hypertensive crisis) receive safety-priority
    diagnostic testing even if entropy alone favors another test.
    """
    if not conditions_with_probabilities:
        return []

    completed_set = {
        name.strip().casefold()
        for name in (completed_test_names or [])
        if name and str(name).strip()
    }

    # Normalize candidate condition probabilities
    total_prob = sum(prob for _, prob in conditions_with_probabilities)
    if total_prob <= 0:
        return []

    norm_candidates = [
        (cond, prob / total_prob) for cond, prob in conditions_with_probabilities
    ]
    cand_probs = [p for _, p in norm_candidates]
    prior_entropy = calculate_entropy(cand_probs)

    # Build index of condition-test relations
    test_relations_map: dict[int, list[tuple[Condition, ConditionTest]]] = {}
    for cond, _ in norm_candidates:
        for rel in cond.tests:
            if rel.test:
                test_relations_map.setdefault(rel.test.test_id, []).append((cond, rel))

    evaluations: list[DiagnosticTestEvaluation] = []

    # Evaluate each available test
    for test in all_tests:
        # Exclude completed tests
        if test.name.strip().casefold() in completed_set:
            continue

        relations = test_relations_map.get(test.test_id, [])
        if not relations:
            # Test not indicated for any active candidate conditions
            continue

        associated_condition_names = sorted({cond.name for cond, _ in relations})
        best_priority = min(rel.priority for _, rel in relations)
        purpose = relations[0][1].purpose or test.purpose

        # Compute safety priority boost for severe conditions targeted by test
        # Safety_Boost = max_{target c} [ (Severity(c) / 10) * P(c) ]
        safety_boost = 0.0
        for cond, _ in relations:
            cond_prob = next((p for c, p in norm_candidates if c.condition_id == cond.condition_id), 0.0)
            sev = int(cond.severity or 1)
            boost = (sev / 10.0) * cond_prob
            if boost > safety_boost:
                safety_boost = boost

        cost_val = next((float(rel.cost) for _, rel in relations if rel.cost is not None), None)

        # Check sensitivity/specificity availability across candidate conditions
        has_performance_data = any(
            rel.sensitivity is not None or rel.specificity is not None
            for _, rel in relations
        )

        if has_performance_data and len(norm_candidates) > 1:
            p_pos_given_cond: list[float] = []
            discriminates: list[str] = []

            for cond, _ in norm_candidates:
                rel_match = next((rel for c, rel in relations if c.condition_id == cond.condition_id), None)
                if rel_match and rel_match.sensitivity is not None:
                    sens = float(rel_match.sensitivity)
                    sens = sens / 100.0 if sens > 1.0 else sens
                    p_pos_given_cond.append(min(max(sens, 0.01), 0.99))
                    discriminates.append(f"{cond.name} (Sens: {sens:.0%})")
                elif rel_match:
                    p_pos_given_cond.append(0.80)
                    discriminates.append(f"{cond.name} (Indicated)")
                else:
                    spec = 0.90
                    fpr = 1.0 - spec
                    p_pos_given_cond.append(fpr)

            # Total probability of positive test: P(T=+) = sum_k P(T=+ | C_k) * P(C_k)
            p_pos = sum(p_pos_given_cond[k] * cand_probs[k] for k in range(len(norm_candidates)))
            p_pos = min(max(p_pos, EPSILON), 1.0 - EPSILON)
            p_neg = 1.0 - p_pos

            # Posterior given T=+: P(C_k | T=+) = P(T=+ | C_k) * P(C_k) / P(T=+)
            post_pos = [(p_pos_given_cond[k] * cand_probs[k]) / p_pos for k in range(len(norm_candidates))]
            entropy_pos = calculate_entropy(post_pos)

            # Posterior given T=-: P(C_k | T=-) = (1 - P(T=+ | C_k)) * P(C_k) / P(T=-)
            post_neg = [((1.0 - p_pos_given_cond[k]) * cand_probs[k]) / p_neg for k in range(len(norm_candidates))]
            entropy_neg = calculate_entropy(post_neg)

            # Expected posterior entropy E[H(C | T)]
            expected_post_entropy = (p_pos * entropy_pos) + (p_neg * entropy_neg)
            info_gain = max(0.0, prior_entropy - expected_post_entropy)
            info_gain_bits = round(info_gain, 4)

            # Composite utility combines pure information gain with safety constraint
            composite_utility = round(info_gain_bits + (severity_weight * safety_boost), 4)

            rep_rel = relations[0][1]
            sens_val = float(rep_rel.sensitivity) if rep_rel.sensitivity is not None else None
            spec_val = float(rep_rel.specificity) if rep_rel.specificity is not None else None

            safety_note = f" (Safety boost: +{safety_boost:.2f})" if safety_boost > 0.05 else ""
            rationale = (
                f"Expected information gain of {info_gain_bits:.3f} bits{safety_note}. "
                f"Helps differentiate {', '.join(discriminates[:3])}."
            )

            evaluations.append(
                DiagnosticTestEvaluation(
                    test_id=test.test_id,
                    name=test.name,
                    description=test.description,
                    purpose=purpose,
                    priority=best_priority,
                    associated_conditions=associated_condition_names,
                    discriminates_between=associated_condition_names,
                    sensitivity=sens_val,
                    specificity=spec_val,
                    cost=cost_val,
                    information_gain=info_gain_bits,
                    expected_entropy_reduction=info_gain_bits,
                    safety_priority_boost=round(safety_boost, 4),
                    composite_utility_score=composite_utility,
                    is_information_gain_calculated=True,
                    missing_parameters=False,
                    rationale=rationale,
                    limitations=[],
                )
            )
        else:
            # Missing sensitivity/specificity parameters: flag transparently
            evaluations.append(
                DiagnosticTestEvaluation(
                    test_id=test.test_id,
                    name=test.name,
                    description=test.description,
                    purpose=purpose,
                    priority=best_priority,
                    associated_conditions=associated_condition_names,
                    discriminates_between=associated_condition_names,
                    sensitivity=None,
                    specificity=None,
                    cost=cost_val,
                    information_gain=None,
                    expected_entropy_reduction=None,
                    safety_priority_boost=round(safety_boost, 4),
                    composite_utility_score=round(safety_boost, 4),
                    is_information_gain_calculated=False,
                    missing_parameters=True,
                    rationale=(
                        f"Associated with {', '.join(associated_condition_names)}. "
                        "Sensitivity/specificity parameters are unrecorded; ranked by relational priority."
                    ),
                    limitations=["Clinical sensitivity and specificity not calibrated in database."],
                )
            )

    # Sort tests:
    # 1. Tests with calculated composite utility first (highest composite utility first)
    # 2. Then by relation priority (lowest priority number = higher priority)
    # 3. Then by name
    evaluations.sort(
        key=lambda t: (
            0 if t.is_information_gain_calculated else 1,
            -(t.composite_utility_score or t.information_gain or 0.0),
            t.priority,
            t.name.casefold(),
        )
    )

    return evaluations
