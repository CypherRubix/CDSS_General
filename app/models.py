from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[str | None] = mapped_column(String(500))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(255))
    doi: Mapped[str | None] = mapped_column(String(255), unique=True)
    url: Mapped[str | None] = mapped_column(String(1000))
    evidence_level: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)


class Condition(Base):
    __tablename__ = "conditions"

    condition_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    urgency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prior_probability: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True, default=None)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)

    symptoms: Mapped[list["ConditionSymptom"]] = relationship(back_populates="condition", cascade="all, delete-orphan")
    risk_factors: Mapped[list["ConditionRiskFactor"]] = relationship(back_populates="condition", cascade="all, delete-orphan")
    tests: Mapped[list["ConditionTest"]] = relationship(back_populates="condition", cascade="all, delete-orphan")
    treatments: Mapped[list["ConditionTreatment"]] = relationship(back_populates="condition", cascade="all, delete-orphan")


class Symptom(Base):
    __tablename__ = "symptoms"

    symptom_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    conditions: Mapped[list["ConditionSymptom"]] = relationship(back_populates="symptom", cascade="all, delete-orphan")


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    risk_factor_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column("factor_type", String(100), nullable=False, index=True)

    conditions: Mapped[list["ConditionRiskFactor"]] = relationship(back_populates="risk_factor", cascade="all, delete-orphan")

    @property
    def factor_type(self) -> str:
        return self.type

    @factor_type.setter
    def factor_type(self, value: str) -> None:
        self.type = value


class Test(Base):
    __test__ = False
    __tablename__ = "tests"

    test_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(100), nullable=False, default="general")

    conditions: Mapped[list["ConditionTest"]] = relationship(back_populates="test", cascade="all, delete-orphan")


class Treatment(Base):
    __tablename__ = "treatments"

    treatment_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    treatment_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    conditions: Mapped[list["ConditionTreatment"]] = relationship(back_populates="treatment", cascade="all, delete-orphan")


class ConditionSymptom(Base):
    __tablename__ = "condition_symptoms"
    __table_args__ = (UniqueConstraint("condition_id", "symptom_id", name="uq_condition_symptom"),)

    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.condition_id", ondelete="CASCADE"), primary_key=True)
    symptom_id: Mapped[int] = mapped_column(ForeignKey("symptoms.symptom_id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)
    frequency: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True, default=None)
    sensitivity: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True, default=None)
    specificity: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True, default=None)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.evidence_id", ondelete="SET NULL"), index=True, nullable=True)

    condition: Mapped[Condition] = relationship(back_populates="symptoms")
    symptom: Mapped[Symptom] = relationship(back_populates="conditions")
    evidence: Mapped[Evidence | None] = relationship()


class ConditionRiskFactor(Base):
    __tablename__ = "condition_risk_factors"
    __table_args__ = (UniqueConstraint("condition_id", "risk_factor_id", name="uq_condition_risk_factor"),)

    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.condition_id", ondelete="CASCADE"), primary_key=True)
    risk_factor_id: Mapped[int] = mapped_column(ForeignKey("risk_factors.risk_factor_id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)
    relationship_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.evidence_id", ondelete="SET NULL"), index=True, nullable=True)

    condition: Mapped[Condition] = relationship(back_populates="risk_factors")
    risk_factor: Mapped[RiskFactor] = relationship(back_populates="conditions")
    evidence: Mapped[Evidence | None] = relationship()


class ConditionTest(Base):
    __tablename__ = "condition_tests"
    __table_args__ = (UniqueConstraint("condition_id", "test_id", name="uq_condition_test"),)

    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.condition_id", ondelete="CASCADE"), primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.test_id", ondelete="CASCADE"), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    purpose: Mapped[str | None] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.evidence_id", ondelete="SET NULL"), index=True, nullable=True)

    condition: Mapped[Condition] = relationship(back_populates="tests")
    test: Mapped[Test] = relationship(back_populates="conditions")
    evidence: Mapped[Evidence | None] = relationship()


class ConditionTreatment(Base):
    __tablename__ = "condition_treatments"
    __table_args__ = (UniqueConstraint("condition_id", "treatment_id", name="uq_condition_treatment"),)

    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.condition_id", ondelete="CASCADE"), primary_key=True)
    treatment_id: Mapped[int] = mapped_column(ForeignKey("treatments.treatment_id", ondelete="CASCADE"), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text)

    condition: Mapped[Condition] = relationship(back_populates="treatments")
    treatment: Mapped[Treatment] = relationship(back_populates="conditions")


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(50), nullable=True)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    risk_factors: Mapped[str] = mapped_column(Text, nullable=False)
    top_condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    likelihood_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)
