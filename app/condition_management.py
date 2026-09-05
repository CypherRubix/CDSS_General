from __future__ import annotations

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import Condition, ConditionRiskFactor, ConditionSymptom, ConditionTest, ConditionTreatment, RiskFactor, Symptom, Test, Treatment
from .services import KnowledgeRepository, DuplicateResourceError, InvalidInputError, ResourceNotFoundError


def create_condition(db, payload) -> Condition:
    name = (payload.name or "").strip()
    if not name:
        raise InvalidInputError("name is required")
    if not 1 <= int(payload.severity) <= 10:
        raise InvalidInputError("severity must be between 1 and 10")
    if not 1 <= int(payload.urgency) <= 10:
        raise InvalidInputError("urgency must be between 1 and 10")

    repository = KnowledgeRepository(db)
    if repository.get_condition_by_name(name):
        raise DuplicateResourceError(f"condition '{name}' already exists")

    condition = Condition(name=name, description=payload.description, severity=int(payload.severity), urgency=int(payload.urgency))
    db.add(condition)
    db.flush()
    return condition


def create_symptom(db, payload) -> Symptom:
    name = (payload.name or "").strip()
    if not name:
        raise InvalidInputError("name is required")
    repository = KnowledgeRepository(db)
    if repository.get_symptom_by_name(name):
        raise DuplicateResourceError(f"symptom '{name}' already exists")
    symptom = Symptom(name=name, description=payload.description)
    db.add(symptom)
    db.flush()
    return symptom


def create_risk_factor(db, payload) -> RiskFactor:
    name = (payload.name or "").strip()
    if not name:
        raise InvalidInputError("name is required")
    if not payload.factor_type or not str(payload.factor_type).strip():
        raise InvalidInputError("factor_type is required")
    repository = KnowledgeRepository(db)
    if repository.get_risk_factor_by_name(name):
        raise DuplicateResourceError(f"risk factor '{name}' already exists")
    risk_factor = RiskFactor(name=name, description=payload.description, factor_type=str(payload.factor_type).strip())
    db.add(risk_factor)
    db.flush()
    return risk_factor


def create_test(db, payload) -> Test:
    name = (payload.name or "").strip()
    if not name:
        raise InvalidInputError("name is required")
    repository = KnowledgeRepository(db)
    if repository.get_test_by_name(name):
        raise DuplicateResourceError(f"test '{name}' already exists")
    test = Test(name=name, description=payload.description, purpose=payload.purpose)
    db.add(test)
    db.flush()
    return test


def create_treatment(db, payload) -> Treatment:
    name = (payload.name or "").strip()
    if not name:
        raise InvalidInputError("name is required")
    repository = KnowledgeRepository(db)
    if repository.get_treatment_by_name(name):
        raise DuplicateResourceError(f"treatment '{name}' already exists")
    treatment = Treatment(name=name, description=payload.description, treatment_type=str(payload.treatment_type).strip())
    db.add(treatment)
    db.flush()
    return treatment


def add_condition_symptom(db, condition_id: int, payload) -> ConditionSymptom:
    if payload.weight < 0:
        raise InvalidInputError("weight must be greater than or equal to 0")
    condition = KnowledgeRepository(db).get_condition(condition_id)
    if condition is None:
        raise ResourceNotFoundError("condition not found")
    symptom = KnowledgeRepository(db).get_symptom(payload.symptom_id)
    if symptom is None:
        raise ResourceNotFoundError("symptom not found")
    existing = db.query(ConditionSymptom).filter_by(condition_id=condition_id, symptom_id=payload.symptom_id).first()
    if existing:
        raise DuplicateResourceError("condition-symptom relationship already exists")
    relationship = ConditionSymptom(condition_id=condition_id, symptom_id=payload.symptom_id, weight=float(payload.weight))
    db.add(relationship)
    db.flush()
    return relationship


def add_condition_risk_factor(db, condition_id: int, payload) -> ConditionRiskFactor:
    if payload.weight < 0:
        raise InvalidInputError("weight must be greater than or equal to 0")
    repository = KnowledgeRepository(db)
    if repository.get_condition(condition_id) is None:
        raise ResourceNotFoundError("condition not found")
    if repository.get_risk_factor(payload.risk_factor_id) is None:
        raise ResourceNotFoundError("risk factor not found")
    existing = db.query(ConditionRiskFactor).filter_by(condition_id=condition_id, risk_factor_id=payload.risk_factor_id).first()
    if existing:
        raise DuplicateResourceError("condition-risk-factor relationship already exists")
    relationship = ConditionRiskFactor(condition_id=condition_id, risk_factor_id=payload.risk_factor_id, weight=float(payload.weight))
    db.add(relationship)
    db.flush()
    return relationship


def add_condition_test(db, condition_id: int, payload) -> ConditionTest:
    repository = KnowledgeRepository(db)
    if repository.get_condition(condition_id) is None:
        raise ResourceNotFoundError("condition not found")
    if repository.get_test(payload.test_id) is None:
        raise ResourceNotFoundError("test not found")
    if payload.priority < 1:
        raise InvalidInputError("priority must be at least 1")
    existing = db.query(ConditionTest).filter_by(condition_id=condition_id, test_id=payload.test_id).first()
    if existing:
        raise DuplicateResourceError("condition-test relationship already exists")
    relationship = ConditionTest(condition_id=condition_id, test_id=payload.test_id, priority=int(payload.priority), purpose=payload.purpose)
    db.add(relationship)
    db.flush()
    return relationship


def add_condition_treatment(db, condition_id: int, payload) -> ConditionTreatment:
    repository = KnowledgeRepository(db)
    if repository.get_condition(condition_id) is None:
        raise ResourceNotFoundError("condition not found")
    if repository.get_treatment(payload.treatment_id) is None:
        raise ResourceNotFoundError("treatment not found")
    if payload.priority < 1:
        raise InvalidInputError("priority must be at least 1")
    existing = db.query(ConditionTreatment).filter_by(condition_id=condition_id, treatment_id=payload.treatment_id).first()
    if existing:
        raise DuplicateResourceError("condition-treatment relationship already exists")
    relationship = ConditionTreatment(condition_id=condition_id, treatment_id=payload.treatment_id, priority=int(payload.priority), notes=payload.notes)
    db.add(relationship)
    db.flush()
    return relationship


def add_complete_condition(db, payload) -> Condition:
    condition_payload = payload.condition
    condition = Condition(
        name=(condition_payload.name or "").strip(),
        description=condition_payload.description,
        severity=int(condition_payload.severity),
        urgency=int(condition_payload.urgency),
    )
    if not condition.name:
        raise InvalidInputError("name is required")
    if not 1 <= condition.severity <= 10:
        raise InvalidInputError("severity must be between 1 and 10")
    if not 1 <= condition.urgency <= 10:
        raise InvalidInputError("urgency must be between 1 and 10")

    repository = KnowledgeRepository(db)
    if repository.get_condition_by_name(condition.name):
        raise DuplicateResourceError(f"condition '{condition.name}' already exists")

    db.add(condition)
    db.flush()

    for item in payload.symptoms:
        if not repository.get_symptom(item.symptom_id):
            raise ResourceNotFoundError("symptom not found")
        if item.weight < 0:
            raise InvalidInputError("weight must be greater than or equal to 0")
        existing = db.query(ConditionSymptom).filter_by(condition_id=condition.condition_id, symptom_id=item.symptom_id).first()
        if existing:
            raise DuplicateResourceError("condition-symptom relationship already exists")
        db.add(ConditionSymptom(condition_id=condition.condition_id, symptom_id=item.symptom_id, weight=float(item.weight)))

    for item in payload.risk_factors:
        if not repository.get_risk_factor(item.risk_factor_id):
            raise ResourceNotFoundError("risk factor not found")
        if item.weight < 0:
            raise InvalidInputError("weight must be greater than or equal to 0")
        existing = db.query(ConditionRiskFactor).filter_by(condition_id=condition.condition_id, risk_factor_id=item.risk_factor_id).first()
        if existing:
            raise DuplicateResourceError("condition-risk-factor relationship already exists")
        db.add(ConditionRiskFactor(condition_id=condition.condition_id, risk_factor_id=item.risk_factor_id, weight=float(item.weight)))

    for item in payload.tests:
        if not repository.get_test(item.test_id):
            raise ResourceNotFoundError("test not found")
        if item.priority < 1:
            raise InvalidInputError("priority must be at least 1")
        existing = db.query(ConditionTest).filter_by(condition_id=condition.condition_id, test_id=item.test_id).first()
        if existing:
            raise DuplicateResourceError("condition-test relationship already exists")
        db.add(ConditionTest(condition_id=condition.condition_id, test_id=item.test_id, priority=int(item.priority), purpose=item.purpose))

    for item in payload.treatments:
        if not repository.get_treatment(item.treatment_id):
            raise ResourceNotFoundError("treatment not found")
        if item.priority < 1:
            raise InvalidInputError("priority must be at least 1")
        existing = db.query(ConditionTreatment).filter_by(condition_id=condition.condition_id, treatment_id=item.treatment_id).first()
        if existing:
            raise DuplicateResourceError("condition-treatment relationship already exists")
        db.add(ConditionTreatment(condition_id=condition.condition_id, treatment_id=item.treatment_id, priority=int(item.priority), notes=item.notes))

    db.flush()
    return condition
