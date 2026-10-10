from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .models import Condition, ConditionRiskFactor, ConditionSymptom, ConditionTest

# Small floor to guarantee numerical stability and prevent log(0)
EPSILON = 1e-4
# Baseline probability for a finding given a condition when no specific link is established
BASELINE_FINDING_RATE = 0.05
# Default threshold for normalized entropy triggering "high uncertainty" recommendation
DEFAULT_UNCERTAINTY_THRESHOLD = 0.50
# Severity threshold defining "high-severity / high-harm" conditions
HIGH_SEVERITY_THRESHOLD = 7


@dataclass
class EvidenceItem:
    name: str
    weight: float
    probability: float
    is_positive: bool
    is_proxy: bool


@dataclass
class DiagnosticUncertaintyResult:
    shannon_entropy_bits: float
    normalized_entropy: float
    margin_of_separation: float
    is_uncertain: bool
    uncertainty_threshold: float
    leading_competing_diagnoses: list[str]
    missingness_ratio: float
    interpretation: str


@dataclass
class SafetyAssessmentResult:
    high_severity_conditions_at_risk: list[str]
    critical_escalation_flag: bool
    urgent_findings: list[str]
    safety_rationale: str


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
    is_high_severity_risk: bool = False
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


def _extract_test_performance(relation: ConditionTest) -> tuple[float, float, bool]:
    """
    Extracts test sensitivity and specificity for a condition relation.
    Returns (sensitivity, specificity, is_proxy).
    """
    sens = 0.85
    spec = 0.90
    is_proxy = True

    if relation.sensitivity is not None and float(relation.sensitivity) > 0:
        s = float(relation.sensitivity)
        sens = s / 100.0 if s > 1.0 else s
        is_proxy = False

    if relation.specificity is not None and float(relation.specificity) > 0:
        sp = float(relation.specificity)
        spec = sp / 100.0 if sp > 1.0 else sp
        is_proxy = False

    return min(max(sens, 0.01), 0.99), min(max(spec, 0.01), 0.99), is_proxy


def log_sum_exp(log_values: list[float]) -> float:
    """Numerically stable calculation of ln(sum(exp(x_i)))."""
    if not log_values:
        return float("-inf")
    max_val = max(log_values)
    if math.isinf(max_val) and max_val < 0:
        return float("-inf")
    sum_exp = sum(math.exp(val - max_val) for val in log_values)
    return max_val + math.log(sum_exp)


def calculate_diagnostic_uncertainty(
    probabilities: list[float],
    condition_names: list[str],
    total_model_features_count: int = 12,
    recorded_features_count: int = 1,
    uncertainty_threshold: float = DEFAULT_UNCERTAINTY_THRESHOLD,
) -> DiagnosticUncertaintyResult:
    """
    Calculates Shannon entropy, normalized entropy, and separation margin over posterior distribution.

    Entropy H(C | E) = -sum_c P(c | E) * log2(P(c | E)) [bits]
    Normalized Entropy H_norm = H(C | E) / log2(K) (0 = complete certainty, 1 = maximum ambiguity)
    Margin of Separation Delta P = P(top1) - P(top2)
    """
    k = len(probabilities)
    if k <= 1:
        return DiagnosticUncertaintyResult(
            shannon_entropy_bits=0.0,
            normalized_entropy=0.0,
            margin_of_separation=1.0,
            is_uncertain=False,
            uncertainty_threshold=uncertainty_threshold,
            leading_competing_diagnoses=condition_names[:1],
            missingness_ratio=max(0.0, 1.0 - (recorded_features_count / max(total_model_features_count, 1))),
            interpretation="Single candidate condition; zero entropy.",
        )

    # Shannon Entropy in bits (log2)
    entropy_bits = 0.0
    for p in probabilities:
        if p > 1e-9:
            entropy_bits -= p * math.log2(p)

    max_entropy_bits = math.log2(k)
    norm_entropy = min(1.0, max(0.0, entropy_bits / max_entropy_bits)) if max_entropy_bits > 0 else 0.0

    # Margin of separation between top 1 and top 2
    sorted_pairs = sorted(zip(probabilities, condition_names), key=lambda x: x[0], reverse=True)
    p_top1 = sorted_pairs[0][0] if len(sorted_pairs) > 0 else 0.0
    p_top2 = sorted_pairs[1][0] if len(sorted_pairs) > 1 else 0.0
    margin = round(p_top1 - p_top2, 4)

    is_uncertain = (norm_entropy >= uncertainty_threshold) or (margin < 0.20)

    # Leading competing diagnoses covering the uncertainty
    leading = [name for p, name in sorted_pairs[:3] if p > 0.08]

    # Input data missingness ratio (explicitly distinguished from posterior entropy)
    missingness = round(max(0.0, 1.0 - (recorded_features_count / max(total_model_features_count, 1))), 2)

    if norm_entropy > 0.70:
        interpretation = (
            f"High diagnostic uncertainty (entropy: {entropy_bits:.2f} bits, {norm_entropy:.0%} of max). "
            f"Probability is distributed across competing diagnoses ({', '.join(leading[:2])}). "
            "Differential diagnostic testing is strongly recommended to resolve ambiguity."
        )
    elif norm_entropy > uncertainty_threshold:
        interpretation = (
            f"Moderate diagnostic uncertainty (entropy: {entropy_bits:.2f} bits, separation margin: {margin:.1%}). "
            "Targeted diagnostic testing could help distinguish the leading candidate."
        )
    else:
        interpretation = (
            f"Low diagnostic uncertainty (entropy: {entropy_bits:.2f} bits). "
            f"Dominant candidate {sorted_pairs[0][1]} has {sorted_pairs[0][0]:.1%} posterior probability."
        )

    return DiagnosticUncertaintyResult(
        shannon_entropy_bits=round(entropy_bits, 4),
        normalized_entropy=round(norm_entropy, 4),
        margin_of_separation=margin,
        is_uncertain=is_uncertain,
        uncertainty_threshold=uncertainty_threshold,
        leading_competing_diagnoses=leading,
        missingness_ratio=missingness,
        interpretation=interpretation,
    )


def evaluate_severity_and_safety(
    results: list[BayesianConditionResult],
    positive_symptoms: list[str],
) -> SafetyAssessmentResult:
    """
    Evaluates condition severity and clinical urgency independently of likelihood.
    Flags high-severity conditions requiring clinical watch even if posterior probability is lower,
    preventing cognitive under-triage of serious conditions.
    """
    high_sev_conditions: list[str] = []
    urgent_findings: list[str] = []
    critical_flag = False

    # Check for urgent clinical symptoms
    red_flag_symptoms = {"chest pain", "shortness of breath", "dizziness"}
    pos_norm = {_normalize_name(s) for s in positive_symptoms}
    for sym in red_flag_symptoms:
        if sym in pos_norm:
            urgent_findings.append(sym.title())

    for res in results:
        cond = res.condition
        sev = int(cond.severity or 1)
        urg = int(cond.urgency or 1)

        # High-severity harm risk: severe conditions with non-negligible probability (> 4%)
        if sev >= HIGH_SEVERITY_THRESHOLD and res.posterior_probability > 0.04:
            res.is_high_severity_risk = True
            high_sev_conditions.append(f"{cond.name} (Sev {sev}/10, P={res.posterior_probability:.1%})")

        # Critical escalation: very high severity (>=8) or high urgency with moderate probability (>15%)
        if (sev >= 8 or urg >= 8) and res.posterior_probability > 0.15:
            critical_flag = True

    if urgent_findings:
        critical_flag = True

    if critical_flag:
        rationale = (
            "Safety escalation active: Red-flag symptoms or high-harm potential diagnoses identified. "
            "Diagnostic investigations should prioritize ruling out serious conditions regardless of prior probability."
        )
    else:
        rationale = "Standard clinical safety parameters apply; no emergent red-flag escalation triggered."

    return SafetyAssessmentResult(
        high_severity_conditions_at_risk=high_sev_conditions,
        critical_escalation_flag=critical_flag,
        urgent_findings=urgent_findings,
        safety_rationale=rationale,
    )


def run_bayesian_inference(
    conditions: list[Condition],
    positive_symptoms: list[str],
    positive_risk_factors: list[str],
    negative_symptoms: list[str] | None = None,
    negative_risk_factors: list[str] | None = None,
    test_results: list[Any] | None = None,
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
    5. Test results update likelihood sequentially via sensitivity / specificity.
    6. Log-space arithmetic with Laplace smoothing prevents numerical underflow.
    7. Posteriors are normalized across candidate conditions such that sum(P(C_k)) = 1.0.
    8. Likelihood/probability is kept strictly separate from severity and urgency.
    """
    if not conditions:
        return []

    pos_sym_set = {_normalize_name(s) for s in positive_symptoms if s and str(s).strip()}
    pos_risk_set = {_normalize_name(r) for r in positive_risk_factors if r and str(r).strip()}
    neg_sym_set = {_normalize_name(s) for s in (negative_symptoms or []) if s and str(s).strip()}
    neg_risk_set = {_normalize_name(r) for r in (negative_risk_factors or []) if r and str(r).strip()}

    # Parse completed test results
    normalized_test_results: list[tuple[str, str]] = []
    if test_results:
        for t_item in test_results:
            if isinstance(t_item, dict):
                t_name = _normalize_name(t_item.get("test_name", ""))
                t_res = _normalize_name(t_item.get("result", ""))
            else:
                t_name = _normalize_name(getattr(t_item, "test_name", ""))
                t_res = _normalize_name(getattr(t_item, "result", ""))
            if t_name and t_res:
                normalized_test_results.append((t_name, t_res))

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

        # Map condition's symptoms, risk factors, and tests
        sym_rel_map = {_normalize_name(rel.symptom.name): rel for rel in condition.symptoms if rel.symptom and rel.symptom.name}
        risk_rel_map = {_normalize_name(rel.risk_factor.name): rel for rel in condition.risk_factors if rel.risk_factor and rel.risk_factor.name}
        test_rel_map = {_normalize_name(rel.test.name): rel for rel in condition.tests if rel.test and rel.test.name}

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

        # E. Process SEQUENTIAL TEST RESULTS
        for t_name, t_res in normalized_test_results:
            is_pos_result = t_res in {"positive", "abnormal", "elevated", "pos"}
            is_neg_result = t_res in {"negative", "normal", "neg"}

            if t_name in test_rel_map:
                rel = test_rel_map[t_name]
                sens, spec, is_proxy = _extract_test_performance(rel)
                if is_proxy:
                    has_any_proxy = True

                if is_pos_result:
                    # P(T=+ | Condition) = sensitivity
                    log_likelihood += math.log(max(sens, EPSILON))
                    supporting.append(f"Positive test: {rel.test.name} (Sens: {sens:.0%})")
                elif is_neg_result:
                    # P(T=- | Condition) = 1 - sensitivity
                    prob_fn = max(1.0 - sens, EPSILON)
                    log_likelihood += math.log(prob_fn)
                    conflicting.append(f"Negative test: {rel.test.name} (False neg rate: {prob_fn:.0%})")
            else:
                # Test not linked to this condition
                spec_generic = 0.90
                if is_pos_result:
                    # False positive rate: 1 - specificity
                    fpr = max(1.0 - spec_generic, EPSILON)
                    log_likelihood += math.log(fpr)
                    conflicting.append(f"Positive test for other pathology: {t_name}")
                elif is_neg_result:
                    # True negative rate: specificity
                    log_likelihood += math.log(max(spec_generic, EPSILON))

        # Unrecorded findings
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
                is_high_severity_risk=(severity >= HIGH_SEVERITY_THRESHOLD and posterior_prob > 0.04),
                explanation=explanation,
                limitations=item["limitations"],
            )
        )

    # Sort results by posterior probability descending, then priority score, then name
    results.sort(key=lambda r: (-r.posterior_probability, -r.priority_score, r.condition.name.casefold()))
    return results
