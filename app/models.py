from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
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
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Condition(Base):
    __tablename__ = "conditions"

    condition_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    urgency: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    prior_probability: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    symptoms: Mapped[list["ConditionSymptom"]] = relationship(cascade="all, delete-orphan")
    risk_factors: Mapped[list["ConditionRiskFactor"]] = relationship(cascade="all, delete-orphan")
    tests: Mapped[list["ConditionTest"]] = relationship(cascade="all, delete-orphan")


class Symptom(Base):
    __tablename__ = "symptoms"

    symptom_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    risk_factor_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)


class Test(Base):
    __test__ = False
    __tablename__ = "tests"

    test_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(100), nullable=False)


class ConditionSymptom(Base):
    __tablename__ = "condition_symptoms"
    __table_args__ = (UniqueConstraint("condition_id", "symptom_id"),)

    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.condition_id", ondelete="CASCADE"), primary_key=True)
    symptom_id: Mapped[int] = mapped_column(ForeignKey("symptoms.symptom_id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=1, nullable=False)
    frequency: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    sensitivity: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    specificity: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.evidence_id", ondelete="SET NULL"), index=True)
    symptom: Mapped[Symptom] = relationship()
    evidence: Mapped[Evidence | None] = relationship()


class ConditionRiskFactor(Base):
    __tablename__ = "condition_risk_factors"
    __table_args__ = (UniqueConstraint("condition_id", "risk_factor_id"),)

    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.condition_id", ondelete="CASCADE"), primary_key=True)
    risk_factor_id: Mapped[int] = mapped_column(ForeignKey("risk_factors.risk_factor_id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=1, nullable=False)
    relationship_description: Mapped[str | None] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.evidence_id", ondelete="SET NULL"), index=True)
    risk_factor: Mapped[RiskFactor] = relationship()
    evidence: Mapped[Evidence | None] = relationship()


class ConditionTest(Base):
    __tablename__ = "condition_tests"
    __table_args__ = (UniqueConstraint("condition_id", "test_id"),)

    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.condition_id", ondelete="CASCADE"), primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.test_id", ondelete="CASCADE"), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.evidence_id", ondelete="SET NULL"), index=True)
    test: Mapped[Test] = relationship()
    evidence: Mapped[Evidence | None] = relationship()
