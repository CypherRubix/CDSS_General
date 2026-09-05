from typing import Any

from pydantic import BaseModel, Field, field_validator


class PatientInput(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    risk_factors: list[str] | dict[str, Any] = Field(default_factory=list)
    demographics: dict[str, Any] = Field(default_factory=dict)
    measurements: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symptoms")
    @classmethod
    def validate_symptoms(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if not cleaned:
            raise ValueError("at least one symptom is required")
        return cleaned


class EvidenceResponse(BaseModel):
    evidence_id: int
    title: str
    authors: str | None = None
    publication_year: int | None = None
    source: str | None = None
    doi: str | None = None
    url: str | None = None
    evidence_level: str | None = None
    notes: str | None = None
    is_demo: bool


class TestRecommendation(BaseModel):
    name: str
    purpose: str | None = None
    type: str
    priority: int
    evidence: list[EvidenceResponse] = Field(default_factory=list)


class RankedCondition(BaseModel):
    condition: str
    likelihood_score: float
    severity: float
    urgency: float
    clinical_priority_score: float
    matched_symptoms: list[str]
    relevant_risk_factors: list[str]
    recommended_tests: list[TestRecommendation]
    evidence: list[EvidenceResponse]
    explanation: str


class EvaluationResponse(BaseModel):
    disclaimer: str
    ranked_conditions: list[RankedCondition]


class ResourceResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    type: str | None = None
