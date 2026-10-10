from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .models import Condition, ConditionRiskFactor, ConditionSymptom

# Small floor to guarantee numerical stability and prevent log(0)
EPSILON = 1e-4
# Baseline probability for a finding given a condition when no specific link is established
BASELINE_FINDING_RATE = 0.05


@dataclass
class EvidenceItem:
    name: str
    weight: float
    probability: float
    is_positive: bool
    is_proxy: bool


@dataclass
class BayesianConditionResult:
    condition: Condition
    prior_probability: float
    is_prior_configured: bool
    log_prior: float
    log_likelihood: float
    log_posterior: float
    posterior_probability: float
    is_calibrated_probability: bool
    matched_symptoms: list[EvidenceItem] = field(default_factory=list)
    matched_risk_factors: list[EvidenceItem] = field(default_factory=list)
    absent_symptoms: list[EvidenceItem] = field(default_factory=list)
    absent_risk_factors: list[EvidenceItem] = field(default_factory=list)
    unrecorded_findings: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    conflicting_evidence: list[str] = field(default_factory=list)
    severity: int = 1
    urgency: int = 1
    priority_score: float = 0.0
    explanation: str = ""
    limitations: list[str] = field(default_factory=list)


def _normalize_name(name: str) -> str:
    return name.strip().casefold() if name else ""


def _extract_symptom_probability(relation: ConditionSymptom) -> tuple[float, bool]:
    """
    Extracts conditional probability P(symptom=1 | condition).
    Uses sensitivity or frequency if recorded; otherwise falls back to a bounded proxy based on weight.
    Returns (probability, is_proxy).
    """
    if relation.sensitivity is not None and float(relation.sensitivity) > 0:
        val = float(relation.sensitivity)
        if val > 1.0:
            val = val / 100.0 if val <= 100.0 else val / 10.0
        return min(max(val, EPSILON), 1.0 - EPSILON), False

    if relation.frequency is not None and float(relation.frequency) > 0:
        val = float(relation.frequency)
        if val > 1.0:
            val = val / 100.0 if val <= 100.0 else val / 10.0
        return min(max(val, EPSILON), 1.0 - EPSILON), False

    # Weight fallback: treat normalized weight as an uncalibrated proxy
    weight = float(relation.weight) if relation.weight is not None else 1.0
    val = min(max(weight if weight <= 1.0 else weight / 10.0, 0.1), 0.95)
    return val, True


def _extract_risk_probability(relation: ConditionRiskFactor) -> tuple[float, bool]:
    """
    Extracts conditional probability P(risk_factor=1 | condition).
    Uses relational weight as an uncalibrated proxy.
    Returns (probability, is_proxy).
    """
    weight = float(relation.weight) if relation.weight is not None else 1.0
    val = min(max(weight if weight <= 1.0 else weight / 10.0, 0.05), 0.90)
    return val, True


def log_sum_exp(log_values: list[float]) -> float:
    """Numerically stable calculation of ln(sum(exp(x_i)))."""
    if not log_values:
        return float("-inf")
    max_val = max(log_values)
    if math.isinf(max_val) and max_val < 0:
        return float("-inf")
    sum_exp = sum(math.exp(val - max_val) for val in log_values)
    return max_val + math.log(sum_exp)


def run_bayesian_inference(
    conditions: list[Condition],
    positive_symptoms: list[str],
    positive_risk_factors: list[str],
    negative_symptoms: list[str] | None = None,
    negative_risk_factors: list[str] | None = None,
    all_known_symptoms: list[str] | None = None,
) -> list[BayesianConditionResult]:
    """
    Performs Naive Bayes diagnostic inference across candidate conditions.

    Assumptions & Guarantees:
    1. Prior P(C_k) is derived from condition.prior_probability if configured; otherwise
       a uniform uninformative prior (1/N) is used, explicitly labeled as uncalibrated.
    2. Positive findings update likelihood via ln P(finding | C_k).
    3. Explicit negative findings update likelihood via ln(1 - P(finding | C_k)).
    4. Unrecorded findings are NEITHER positive nor negative; they do not alter the likelihood.
    5. Log-space arithmetic with Laplace smoothing prevents numerical underflow.
    6. Posteriors are normalized across candidate conditions such that sum(P(C_k)) = 1.0.
    7. Likelihood/probability is kept strictly separate from severity and urgency.
    """
    if not conditions:
        return []

    pos_sym_set = {_normalize_name(s) for s in positive_symptoms if s and str(s).strip()}
    pos_risk_set = {_normalize_name(r) for r in positive_risk_factors if r and str(r).strip()}
    neg_sym_set = {_normalize_name(s) for s in (negative_symptoms or []) if s and str(s).strip()}
    neg_risk_set = {_normalize_name(r) for r in (negative_risk_factors or []) if r and str(r).strip()}

    num_conditions = len(conditions)

    # 1. Determine prior probabilities
    priors: list[float] = []
    priors_configured: list[bool] = []
    for cond in conditions:
        if cond.prior_probability is not None and float(cond.prior_probability) > 0:
            priors.append(float(cond.prior_probability))
            priors_configured.append(True)
        else:
            priors.append(1.0 / num_conditions)
            priors_configured.append(False)

    total_prior = sum(priors)
    if total_prior > 0:
        normalized_priors = [p / total_prior for p in priors]
    else:
        normalized_priors = [1.0 / num_conditions] * num_conditions

    # 2. Compute log-likelihood for each condition
    intermediate_results = []
    log_unnormalized_posteriors = []

    for idx, condition in enumerate(conditions):
        prior = normalized_priors[idx]
        is_prior_conf = priors_configured[idx]
        log_prior = math.log(max(prior, EPSILON))

        log_likelihood = 0.0
        has_any_proxy = not is_prior_conf

        matched_syms: list[EvidenceItem] = []
        matched_risks: list[EvidenceItem] = []
        absent_syms: list[EvidenceItem] = []
        absent_risks: list[EvidenceItem] = []
        supporting: list[str] = []
        conflicting: list[str] = []
        limitations: list[str] = []

        if not is_prior_conf:
            limitations.append("Condition prevalence / prior probability is not clinically calibrated (uniform prior used).")

        # Map condition's symptoms and risk factors
        sym_rel_map = {_normalize_name(rel.symptom.name): rel for rel in condition.symptoms if rel.symptom and rel.symptom.name}
        risk_rel_map = {_normalize_name(rel.risk_factor.name): rel for rel in condition.risk_factors if rel.risk_factor and rel.risk_factor.name}

        # A. Process POSITIVE symptoms
        for sym_name in pos_sym_set:
            if sym_name in sym_rel_map:
                rel = sym_rel_map[sym_name]
                prob, is_proxy = _extract_symptom_probability(rel)
                if is_proxy:
                    has_any_proxy = True
                log_prob = math.log(max(prob, EPSILON))
                log_likelihood += log_prob
                disp_name = rel.symptom.name
                item = EvidenceItem(name=disp_name, weight=float(rel.weight or 1.0), probability=prob, is_positive=True, is_proxy=is_proxy)
                matched_syms.append(item)
                if prob > BASELINE_FINDING_RATE:
                    supporting.append(f"{disp_name} (P={prob:.2f})")
            else:
                # Symptom present in patient but unlinked to this condition
                log_prob = math.log(BASELINE_FINDING_RATE)
                log_likelihood += log_prob
                conflicting.append(f"Uncharacteristic finding: {sym_name}")

        # B. Process POSITIVE risk factors
        for risk_name in pos_risk_set:
            if risk_name in risk_rel_map:
                rel = risk_rel_map[risk_name]
                prob, is_proxy = _extract_risk_probability(rel)
                if is_proxy:
                    has_any_proxy = True
                log_prob = math.log(max(prob, EPSILON))
                log_likelihood += log_prob
                disp_name = rel.risk_factor.name
                item = EvidenceItem(name=disp_name, weight=float(rel.weight or 1.0), probability=prob, is_positive=True, is_proxy=is_proxy)
                matched_risks.append(item)
                if prob > BASELINE_FINDING_RATE:
                    supporting.append(f"Risk factor: {disp_name} (P={prob:.2f})")
            else:
                log_prob = math.log(BASELINE_FINDING_RATE)
                log_likelihood += log_prob

        # C. Process EXPLICIT NEGATIVE symptoms (patient confirmed absent)
        for sym_name in neg_sym_set:
            if sym_name in sym_rel_map:
                rel = sym_rel_map[sym_name]
                prob, is_proxy = _extract_symptom_probability(rel)
                prob_absent = max(1.0 - prob, EPSILON)
                log_prob = math.log(prob_absent)
                log_likelihood += log_prob
                disp_name = rel.symptom.name
                item = EvidenceItem(name=disp_name, weight=float(rel.weight or 1.0), probability=prob_absent, is_positive=False, is_proxy=is_proxy)
                absent_syms.append(item)
                if prob > 0.5:
                    conflicting.append(f"Expected symptom absent: {disp_name}")
            else:
                # Absent symptom not linked to condition; expected negative
                prob_absent = 1.0 - BASELINE_FINDING_RATE
                log_likelihood += math.log(prob_absent)

        # D. Process EXPLICIT NEGATIVE risk factors
        for risk_name in neg_risk_set:
            if risk_name in risk_rel_map:
                rel = risk_rel_map[risk_name]
                prob, is_proxy = _extract_risk_probability(rel)
                prob_absent = max(1.0 - prob, EPSILON)
                log_prob = math.log(prob_absent)
                log_likelihood += log_prob
                disp_name = rel.risk_factor.name
                item = EvidenceItem(name=disp_name, weight=float(rel.weight or 1.0), probability=prob_absent, is_positive=False, is_proxy=is_proxy)
                absent_risks.append(item)

        # Unrecorded findings: note them for clinical completeness without altering log_likelihood
        unrecorded = []
        if all_known_symptoms:
            for s in all_known_symptoms:
                norm_s = _normalize_name(s)
                if norm_s not in pos_sym_set and norm_s not in neg_sym_set and norm_s in sym_rel_map:
                    unrecorded.append(sym_rel_map[norm_s].symptom.name)

        log_unnorm_posterior = log_prior + log_likelihood
        log_unnormalized_posteriors.append(log_unnorm_posterior)

        intermediate_results.append({
            "condition": condition,
            "prior": prior,
            "is_prior_configured": is_prior_conf,
            "log_prior": log_prior,
            "log_likelihood": log_likelihood,
            "log_unnorm": log_unnorm_posterior,
            "is_calibrated": not has_any_proxy,
            "matched_syms": matched_syms,
            "matched_risks": matched_risks,
            "absent_syms": absent_syms,
            "absent_risks": absent_risks,
            "unrecorded": unrecorded,
            "supporting": supporting,
            "conflicting": conflicting,
            "limitations": limitations,
        })

    # 3. Normalize posteriors using log_sum_exp
    log_partition = log_sum_exp(log_unnormalized_posteriors)

    results: list[BayesianConditionResult] = []
    for item in intermediate_results:
        log_posterior = item["log_unnorm"] - log_partition
        posterior_prob = round(math.exp(log_posterior), 4)

        condition = item["condition"]
        severity = int(condition.severity or 1)
        urgency = int(condition.urgency or 1)

        # Operational clinical priority: combines likelihood with severity and urgency
        # for triage ordering while keeping posterior probability clean.
        priority_score = round(
            posterior_prob * (1.0 + (severity / 10.0) * 0.5 + (urgency / 10.0) * 0.5),
            4,
        )

        calibrated_str = "evidence-based clinical parameters" if item["is_calibrated"] else "uncalibrated association weights as conditional likelihood proxies"
        explanation = (
            f"Posterior probability estimated at {posterior_prob:.1%} via Bayesian inference using {calibrated_str}. "
            f"Prior probability contributed {item['prior']:.1%}. "
            f"{len(item['matched_syms'])} matched symptoms and {len(item['matched_risks'])} risk factors supported this candidate. "
            f"Severity ({severity}/10) and urgency ({urgency}/10) are maintained as separate triage indicators."
        )

        results.append(
            BayesianConditionResult(
                condition=condition,
                prior_probability=item["prior"],
                is_prior_configured=item["is_prior_configured"],
                log_prior=item["log_prior"],
                log_likelihood=item["log_likelihood"],
                log_posterior=log_posterior,
                posterior_probability=posterior_prob,
                is_calibrated_probability=item["is_calibrated"],
                matched_symptoms=item["matched_syms"],
                matched_risk_factors=item["matched_risks"],
                absent_symptoms=item["absent_syms"],
                absent_risk_factors=item["absent_risks"],
                unrecorded_findings=item["unrecorded"],
                supporting_evidence=item["supporting"],
                conflicting_evidence=item["conflicting"],
                severity=severity,
                urgency=urgency,
                priority_score=priority_score,
                explanation=explanation,
                limitations=item["limitations"],
            )
        )

    # Sort results by posterior probability descending, then priority score, then name
    results.sort(key=lambda r: (-r.posterior_probability, -r.priority_score, r.condition.name.casefold()))
    return results

