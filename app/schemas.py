from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ResourceResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    type: str | None = None
    severity: int | None = None
    urgency: int | None = None
    purpose: str | None = None


class ConditionCreate(BaseModel):
    name: str
    description: str | None = None
    severity: int = Field(..., ge=1, le=10)
    urgency: int = Field(..., ge=1, le=10)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned


class SymptomCreate(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned


class RiskFactorCreate(BaseModel):
    name: str
    description: str | None = None
    factor_type: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned

    @field_validator("factor_type")
    @classmethod
    def validate_factor_type(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("factor_type is required")
        return cleaned


class TestCreate(BaseModel):
    name: str
    description: str | None = None
    purpose: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned


class TreatmentCreate(BaseModel):
    name: str
    description: str | None = None
    treatment_type: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned

    @field_validator("treatment_type")
    @classmethod
    def validate_treatment_type(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("treatment_type is required")
        return cleaned


class ConditionSymptomCreate(BaseModel):
    symptom_id: int
    weight: float = Field(..., ge=0)


class ConditionRiskFactorCreate(BaseModel):
    risk_factor_id: int
    weight: float = Field(..., ge=0)


class ConditionTestCreate(BaseModel):
    test_id: int
    priority: int = Field(..., ge=1)
    purpose: str | None = None


class ConditionTreatmentCreate(BaseModel):
    treatment_id: int
    priority: int = Field(..., ge=1)
    notes: str | None = None


class CompleteConditionRelational(BaseModel):
    symptom_id: int
    weight: float = Field(..., ge=0)


class CompleteRiskFactorRelational(BaseModel):
    risk_factor_id: int
    weight: float = Field(..., ge=0)


class CompleteTestRelational(BaseModel):
    test_id: int
    priority: int = Field(..., ge=1)
    purpose: str | None = None


class CompleteTreatmentRelational(BaseModel):
    treatment_id: int
    priority: int = Field(..., ge=1)
    notes: str | None = None


class CompleteConditionRequest(BaseModel):
    condition: ConditionCreate
    symptoms: list[CompleteConditionRelational] = Field(default_factory=list)
    risk_factors: list[CompleteRiskFactorRelational] = Field(default_factory=list)
    tests: list[CompleteTestRelational] = Field(default_factory=list)
    treatments: list[CompleteTreatmentRelational] = Field(default_factory=list)


class TestResultInput(BaseModel):
    test_name: str
    result: str  # 'positive', 'negative', 'normal', 'abnormal', 'inconclusive'
    numerical_value: float | None = None
    notes: str | None = None


class PatientInput(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    risk_factors: list[str] | dict[str, Any] = Field(default_factory=list)
    negative_symptoms: list[str] = Field(default_factory=list)
    negative_risk_factors: list[str] = Field(default_factory=list)
    completed_tests: list[str] = Field(default_factory=list)
    test_results: list[TestResultInput] = Field(default_factory=list)
    demographics: dict[str, Any] = Field(default_factory=dict)
    measurements: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symptoms")
    @classmethod
    def validate_symptoms(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if isinstance(value, str) and value.strip()]
        if not cleaned:
            raise ValueError("at least one symptom is required")
        return cleaned


class UncertaintyMetrics(BaseModel):
    shannon_entropy_bits: float
    normalized_entropy: float
    margin_of_separation: float
    is_uncertain: bool
    uncertainty_threshold: float
    leading_competing_diagnoses: list[str] = Field(default_factory=list)
    missingness_ratio: float
    interpretation: str


class SeverityUrgencySafety(BaseModel):
    high_severity_conditions_at_risk: list[str] = Field(default_factory=list)
    critical_escalation_flag: bool = False
    urgent_findings: list[str] = Field(default_factory=list)
    safety_rationale: str = ""


class MatchedFactor(BaseModel):
    name: str
    weight: float
    probability: float | None = None
    is_positive: bool = True
    is_proxy: bool = False


class TestRecommendationResult(BaseModel):
    test_id: int
    name: str
    description: str | None = None
    purpose: str | None = None
    priority: int = 1
    associated_conditions: list[str] = Field(default_factory=list)
    discriminates_between: list[str] = Field(default_factory=list)
    information_gain: float | None = None
    expected_entropy_reduction: float | None = None
    safety_priority_boost: float | None = None
    composite_utility_score: float | None = None
    is_information_gain_calculated: bool = False
    missing_parameters: bool = False
    sensitivity: float | None = None
    specificity: float | None = None
    cost: float | None = None
    rationale: str | None = None
    limitations: list[str] = Field(default_factory=list)


class TreatmentRecommendationResult(BaseModel):
    treatment_id: int
    name: str
    description: str | None = None
    treatment_type: str | None = None
    priority: int
    notes: str | None = None
    associated_condition: str


class RankedCondition(BaseModel):
    condition: str
    likelihood_score: float
    posterior_probability: float | None = None
    prior_probability: float | None = None
    is_probability: bool = True
    severity: int
    urgency: int
    priority_score: float
    is_high_severity_risk: bool = False
    matched_symptoms: list[MatchedFactor]
    matched_risk_factors: list[MatchedFactor]
    absent_symptoms: list[MatchedFactor] = Field(default_factory=list)
    absent_risk_factors: list[MatchedFactor] = Field(default_factory=list)
    unrecorded_findings: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    recommended_tests: list[TestRecommendationResult]
    treatments: list[TreatmentRecommendationResult]
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    disclaimer: str
    ranked_conditions: list[RankedCondition]
    differential_tests: list[TestRecommendationResult] = Field(default_factory=list)
    diagnostic_entropy: float | None = None
    uncertainty_metrics: UncertaintyMetrics | None = None
    safety_assessment: SeverityUrgencySafety | None = None
    algorithm_used: str = "Bayesian Inference with Information Gain"


class SequentialEvaluationRequest(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    negative_symptoms: list[str] = Field(default_factory=list)
    test_results: list[TestResultInput] = Field(default_factory=list)
    demographics: dict[str, Any] = Field(default_factory=dict)


class SequentialStepResponse(BaseModel):
    step_number: int
    evaluation: EvaluationResponse
    next_recommended_test: TestRecommendationResult | None = None
    stopping_criterion_met: bool = False
    stopping_rationale: str = ""


class ModelBenchmarkMetrics(BaseModel):
    model_name: str
    top1_accuracy: float
    top3_accuracy: float
    mean_reciprocal_rank: float
    brier_score: float
    average_tests_recommended: float
    average_residual_entropy: float
    high_severity_recall: float
    missing_data_resilience_score: float


class ResearchBenchmarkResponse(BaseModel):
    benchmark_cases_count: int
    models_evaluated: list[ModelBenchmarkMetrics]
    comparative_summary: str
    evaluation_disclaimer: str


class KnowledgeStatsResponse(BaseModel):
    conditions: int
    symptoms: int
    risk_factors: int
    tests: int
    treatments: int
    evaluations: int


class ConditionDetailSymptom(BaseModel):
    symptom_id: int
    name: str
    weight: float


class ConditionDetailRiskFactor(BaseModel):
    risk_factor_id: int
    name: str
    weight: float


class ConditionDetailTest(BaseModel):
    test_id: int
    name: str
    priority: int
    purpose: str | None = None


class ConditionDetailTreatment(BaseModel):
    treatment_id: int
    name: str
    priority: int
    notes: str | None = None


class ConditionDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    severity: int
    urgency: int
    symptoms: list[ConditionDetailSymptom] = Field(default_factory=list)
    risk_factors: list[ConditionDetailRiskFactor] = Field(default_factory=list)
    tests: list[ConditionDetailTest] = Field(default_factory=list)
    treatments: list[ConditionDetailTreatment] = Field(default_factory=list)


class EvaluationRecordCreate(BaseModel):
    age: int | None = None
    sex: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    top_condition: str | None = None
    likelihood_score: float | None = None
    priority_score: float | None = None
    results_json: str | None = None


class EvaluationRecordResponse(BaseModel):
    id: int
    created_at: str
    age: int | None = None
    sex: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    top_condition: str | None = None
    likelihood_score: float | None = None
    priority_score: float | None = None
    results_json: str | None = None
