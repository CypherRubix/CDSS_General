import json
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from .condition_management import (
    add_complete_condition,
    add_condition_risk_factor,
    add_condition_symptom,
    add_condition_test,
    add_condition_treatment,
    create_condition,
    create_risk_factor,
    create_symptom,
    create_test,
    create_treatment,
)
from .database import get_db, init_db
from .database import SessionLocal, get_db, init_db
from .diagnosis_engine import evaluate_patient
from .models import Condition, ConditionRiskFactor, ConditionSymptom, ConditionTest, ConditionTreatment, RiskFactor, Symptom, Test, Treatment
from .schemas import (
    CompleteConditionRequest,
    ConditionCreate,
    ConditionDetailResponse,
    ConditionDetailRiskFactor,
    ConditionDetailSymptom,
    ConditionDetailTest,
    ConditionDetailTreatment,
    ConditionRiskFactorCreate,
    ConditionSymptomCreate,
    ConditionTestCreate,
    ConditionTreatmentCreate,
    EvaluationRecordCreate,
    EvaluationRecordResponse,
    EvaluationResponse,
    KnowledgeStatsResponse,
    PatientInput,
    ResourceResponse,
    RiskFactorCreate,
    SymptomCreate,
    TestCreate,
    TreatmentCreate,
)
from .services import DuplicateResourceError, InvalidInputError, KnowledgeRepository, ResourceNotFoundError
from .services import (
    DuplicateResourceError,
    InvalidInputError,
    KnowledgeRepository,
    ResourceNotFoundError,
    seed_initial_clinical_data,
)

app = FastAPI(
    title="Clinical Decision Support API",
    description="Physician-support system for normalized condition, symptom, and treatment knowledge.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:8001", "http://localhost:8001"],
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    with SessionLocal() as session:
        seed_initial_clinical_data(session)



def _raise_http_for_service_error(exc: Exception) -> None:
    if isinstance(exc, ResourceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, DuplicateResourceError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, InvalidInputError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected server error") from exc


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


@app.get("/conditions", response_model=list[ResourceResponse])
def list_conditions(db: Session = Depends(get_db)):
    return [
        ResourceResponse(id=item.condition_id, name=item.name, description=item.description)
        ResourceResponse(
            id=item.condition_id,
            name=item.name,
            description=item.description,
            severity=item.severity,
            urgency=item.urgency,
        )
        for item in KnowledgeRepository(db).conditions()
    ]


@app.get("/conditions/{condition_id}")
def get_condition(condition_id: int, db: Session = Depends(get_db)):
    item = KnowledgeRepository(db).get_condition(condition_id)
    if item is None:
        raise HTTPException(status_code=404, detail="condition not found")
    return {
        "id": item.condition_id,
        "name": item.name,
        "description": item.description,
        "severity": item.severity,
        "urgency": item.urgency,
    }


@app.get("/conditions/{condition_id}/details", response_model=ConditionDetailResponse)
def get_condition_details(condition_id: int, db: Session = Depends(get_db)):
    cond = KnowledgeRepository(db).get_condition_detail(condition_id)
    if cond is None:
        raise HTTPException(status_code=404, detail="condition not found")
    return ConditionDetailResponse(
        id=cond.condition_id,
        name=cond.name,
        description=cond.description,
        severity=cond.severity,
        urgency=cond.urgency,
        symptoms=[
            ConditionDetailSymptom(symptom_id=rel.symptom_id, name=rel.symptom.name, weight=float(rel.weight))
            for rel in sorted(cond.symptoms, key=lambda s: s.symptom.name.casefold())
        ],
        risk_factors=[
            ConditionDetailRiskFactor(risk_factor_id=rel.risk_factor_id, name=rel.risk_factor.name, weight=float(rel.weight))
            for rel in sorted(cond.risk_factors, key=lambda r: r.risk_factor.name.casefold())
        ],
        tests=[
            ConditionDetailTest(test_id=rel.test_id, name=rel.test.name, priority=rel.priority, purpose=rel.purpose or rel.test.purpose)
            for rel in sorted(cond.tests, key=lambda t: (t.priority, t.test.name.casefold()))
        ],
        treatments=[
            ConditionDetailTreatment(treatment_id=rel.treatment_id, name=rel.treatment.name, priority=rel.priority, notes=rel.notes)
            for rel in sorted(cond.treatments, key=lambda tx: (tx.priority, tx.treatment.name.casefold()))
        ],
    )


@app.get("/symptoms", response_model=list[ResourceResponse])
def list_symptoms(db: Session = Depends(get_db)):
    return [
        ResourceResponse(id=item.symptom_id, name=item.name, description=item.description)
        for item in KnowledgeRepository(db).symptoms()
    ]


@app.get("/symptoms/{symptom_id}")
def get_symptom(symptom_id: int, db: Session = Depends(get_db)):
    item = KnowledgeRepository(db).get_symptom(symptom_id)
    if item is None:
        raise HTTPException(status_code=404, detail="symptom not found")
    return {"id": item.symptom_id, "name": item.name, "description": item.description}


@app.get("/risk-factors", response_model=list[ResourceResponse])
def list_risk_factors(db: Session = Depends(get_db)):
    return [
        ResourceResponse(id=item.risk_factor_id, name=item.name, description=item.description, type=item.factor_type)
        for item in KnowledgeRepository(db).risk_factors()
    ]


@app.get("/risk-factors/{risk_factor_id}")
def get_risk_factor(risk_factor_id: int, db: Session = Depends(get_db)):
    item = KnowledgeRepository(db).get_risk_factor(risk_factor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="risk factor not found")
    return {"id": item.risk_factor_id, "name": item.name, "description": item.description, "type": item.factor_type}


@app.get("/tests", response_model=list[ResourceResponse])
def list_tests(db: Session = Depends(get_db)):
    return [
        ResourceResponse(id=item.test_id, name=item.name, description=item.description)
        ResourceResponse(
            id=item.test_id,
            name=item.name,
            description=item.description,
            purpose=item.purpose,
            type=item.type,
        )
        for item in KnowledgeRepository(db).tests()
    ]


@app.get("/tests/{test_id}")
def get_test(test_id: int, db: Session = Depends(get_db)):
    item = KnowledgeRepository(db).get_test(test_id)
    if item is None:
        raise HTTPException(status_code=404, detail="test not found")
    return {"id": item.test_id, "name": item.name, "description": item.description, "purpose": item.purpose}


@app.get("/treatments", response_model=list[ResourceResponse])
def list_treatments(db: Session = Depends(get_db)):
    return [
        ResourceResponse(id=item.treatment_id, name=item.name, description=item.description, type=item.treatment_type)
        for item in KnowledgeRepository(db).treatments()
    ]


@app.get("/treatments/{treatment_id}")
def get_treatment(treatment_id: int, db: Session = Depends(get_db)):
    item = KnowledgeRepository(db).get_treatment(treatment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="treatment not found")
    return {"id": item.treatment_id, "name": item.name, "description": item.description, "type": item.treatment_type}


@app.get("/conditions/{condition_id}/symptoms")
def list_condition_symptoms(condition_id: int, db: Session = Depends(get_db)):
    condition = KnowledgeRepository(db).get_condition(condition_id)
    if condition is None:
        raise HTTPException(status_code=404, detail="condition not found")
    return [
        {"condition_id": rel.condition_id, "symptom_id": rel.symptom_id, "name": rel.symptom.name, "weight": float(rel.weight)}
        for rel in sorted(condition.symptoms, key=lambda item: item.symptom.name.casefold())
    ]


@app.get("/conditions/{condition_id}/risk-factors")
def list_condition_risk_factors(condition_id: int, db: Session = Depends(get_db)):
    condition = KnowledgeRepository(db).get_condition(condition_id)
    if condition is None:
        raise HTTPException(status_code=404, detail="condition not found")
    return [
        {"condition_id": rel.condition_id, "risk_factor_id": rel.risk_factor_id, "name": rel.risk_factor.name, "weight": float(rel.weight)}
        for rel in sorted(condition.risk_factors, key=lambda item: item.risk_factor.name.casefold())
    ]


@app.get("/conditions/{condition_id}/tests")
def list_condition_tests(condition_id: int, db: Session = Depends(get_db)):
    condition = KnowledgeRepository(db).get_condition(condition_id)
    if condition is None:
        raise HTTPException(status_code=404, detail="condition not found")
    return [
        {"condition_id": rel.condition_id, "test_id": rel.test_id, "name": rel.test.name, "priority": rel.priority, "purpose": rel.purpose}
        for rel in sorted(condition.tests, key=lambda item: (item.priority, item.test.name.casefold()))
    ]


@app.get("/conditions/{condition_id}/treatments")
def list_condition_treatments(condition_id: int, db: Session = Depends(get_db)):
    condition = KnowledgeRepository(db).get_condition(condition_id)
    if condition is None:
        raise HTTPException(status_code=404, detail="condition not found")
    return [
        {"condition_id": rel.condition_id, "treatment_id": rel.treatment_id, "name": rel.treatment.name, "priority": rel.priority, "notes": rel.notes}
        for rel in sorted(condition.treatments, key=lambda item: (item.priority, item.treatment.name.casefold()))
    ]


@app.post("/conditions", response_model=ResourceResponse)
def create_condition_endpoint(payload: ConditionCreate, db: Session = Depends(get_db)):
    try:
        item = create_condition(db, payload)
        db.commit()
        return ResourceResponse(id=item.condition_id, name=item.name, description=item.description)
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/symptoms", response_model=ResourceResponse)
def create_symptom_endpoint(payload: SymptomCreate, db: Session = Depends(get_db)):
    try:
        item = create_symptom(db, payload)
        db.commit()
        return ResourceResponse(id=item.symptom_id, name=item.name, description=item.description)
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/risk-factors", response_model=ResourceResponse)
def create_risk_factor_endpoint(payload: RiskFactorCreate, db: Session = Depends(get_db)):
    try:
        item = create_risk_factor(db, payload)
        db.commit()
        return ResourceResponse(id=item.risk_factor_id, name=item.name, description=item.description, type=item.factor_type)
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/tests", response_model=ResourceResponse)
def create_test_endpoint(payload: TestCreate, db: Session = Depends(get_db)):
    try:
        item = create_test(db, payload)
        db.commit()
        return ResourceResponse(id=item.test_id, name=item.name, description=item.description)
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/treatments", response_model=ResourceResponse)
def create_treatment_endpoint(payload: TreatmentCreate, db: Session = Depends(get_db)):
    try:
        item = create_treatment(db, payload)
        db.commit()
        return ResourceResponse(id=item.treatment_id, name=item.name, description=item.description, type=item.treatment_type)
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/conditions/{condition_id}/symptoms")
def add_condition_symptom_endpoint(condition_id: int, payload: ConditionSymptomCreate, db: Session = Depends(get_db)):
    try:
        item = add_condition_symptom(db, condition_id, payload)
        db.commit()
        return {"condition_id": item.condition_id, "symptom_id": item.symptom_id, "weight": float(item.weight)}
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/conditions/{condition_id}/risk-factors")
def add_condition_risk_factor_endpoint(condition_id: int, payload: ConditionRiskFactorCreate, db: Session = Depends(get_db)):
    try:
        item = add_condition_risk_factor(db, condition_id, payload)
        db.commit()
        return {"condition_id": item.condition_id, "risk_factor_id": item.risk_factor_id, "weight": float(item.weight)}
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/conditions/{condition_id}/tests")
def add_condition_test_endpoint(condition_id: int, payload: ConditionTestCreate, db: Session = Depends(get_db)):
    try:
        item = add_condition_test(db, condition_id, payload)
        db.commit()
        return {"condition_id": item.condition_id, "test_id": item.test_id, "priority": item.priority, "purpose": item.purpose}
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/conditions/{condition_id}/treatments")
def add_condition_treatment_endpoint(condition_id: int, payload: ConditionTreatmentCreate, db: Session = Depends(get_db)):
    try:
        item = add_condition_treatment(db, condition_id, payload)
        db.commit()
        return {"condition_id": item.condition_id, "treatment_id": item.treatment_id, "priority": item.priority, "notes": item.notes}
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/conditions/complete")
def add_complete_condition_endpoint(payload: CompleteConditionRequest, db: Session = Depends(get_db)):
    try:
        with db.begin():
            item = add_complete_condition(db, payload)
        return {
            "id": item.condition_id,
            "name": item.name,
            "description": item.description,
            "severity": item.severity,
            "urgency": item.urgency,
        }
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(patient: PatientInput, db: Session = Depends(get_db)) -> EvaluationResponse:
    return evaluate_patient(db, patient)


@app.get("/stats", response_model=KnowledgeStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    return KnowledgeRepository(db).stats()


@app.post("/seed-demo")
def seed_demo_endpoint(db: Session = Depends(get_db)):
    count = seed_initial_clinical_data(db, force=True)
    return {"message": f"Successfully seeded {count} conditions and clinical knowledge records."}


@app.post("/evaluations", response_model=EvaluationRecordResponse)
def save_evaluation_endpoint(payload: EvaluationRecordCreate, db: Session = Depends(get_db)):
    try:
        record = KnowledgeRepository(db).save_evaluation(
            symptoms=payload.symptoms,
            risk_factors=payload.risk_factors,
            age=payload.age,
            sex=payload.sex,
            top_condition=payload.top_condition,
            likelihood_score=payload.likelihood_score,
            priority_score=payload.priority_score,
            results_json=payload.results_json,
        )
        db.commit()
        return EvaluationRecordResponse(
            id=record.id,
            created_at=record.created_at.strftime("%Y-%m-%d %H:%M"),
            age=record.age,
            sex=record.sex,
            symptoms=json.loads(record.symptoms),
            risk_factors=json.loads(record.risk_factors),
            top_condition=record.top_condition,
            likelihood_score=float(record.likelihood_score) if record.likelihood_score is not None else None,
            priority_score=float(record.priority_score) if record.priority_score is not None else None,
            results_json=record.results_json,
        )
    except Exception as exc:
        db.rollback()
        _raise_http_for_service_error(exc)


@app.get("/evaluations", response_model=list[EvaluationRecordResponse])
def list_evaluations_endpoint(db: Session = Depends(get_db)):
    records = KnowledgeRepository(db).list_evaluations()
    return [
        EvaluationRecordResponse(
            id=rec.id,
            created_at=rec.created_at.strftime("%Y-%m-%d %H:%M"),
            age=rec.age,
            sex=rec.sex,
            symptoms=json.loads(rec.symptoms) if rec.symptoms else [],
            risk_factors=json.loads(rec.risk_factors) if rec.risk_factors else [],
            top_condition=rec.top_condition,
            likelihood_score=float(rec.likelihood_score) if rec.likelihood_score is not None else None,
            priority_score=float(rec.priority_score) if rec.priority_score is not None else None,
            results_json=rec.results_json,
        )
        for rec in records
    ]


# Mount frontend static files so visiting http://127.0.0.1:8000 loads the web application
_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
