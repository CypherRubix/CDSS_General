from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import RiskFactor, Symptom, Test
from .schemas import EvaluationResponse, PatientInput, ResourceResponse
from .services import KnowledgeRepository, rank_conditions

app = FastAPI(
    title="Standalone Clinical Decision Support API",
    description="Physician-support prototype with traceable, configurable ranking signals.",
    version="0.1.0",
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


@app.get("/symptoms", response_model=list[ResourceResponse])
def list_symptoms(db: Session = Depends(get_db)):
    return [ResourceResponse(id=item.symptom_id, name=item.name, description=item.description) for item in KnowledgeRepository(db).symptoms()]


@app.get("/risk-factors", response_model=list[ResourceResponse])
def list_risk_factors(db: Session = Depends(get_db)):
    return [ResourceResponse(id=item.risk_factor_id, name=item.name, description=item.description, type=item.type) for item in KnowledgeRepository(db).risk_factors()]


@app.get("/tests", response_model=list[ResourceResponse])
def list_tests(db: Session = Depends(get_db)):
    return [ResourceResponse(id=item.test_id, name=item.name, description=item.description, type=item.type) for item in KnowledgeRepository(db).tests()]


@app.get("/conditions", response_model=list[ResourceResponse])
def list_conditions(db: Session = Depends(get_db)):
    return [ResourceResponse(id=item.condition_id, name=item.name, description=item.description) for item in KnowledgeRepository(db).conditions()]


@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(patient: PatientInput, db: Session = Depends(get_db)) -> EvaluationResponse:
    repository = KnowledgeRepository(db)
    if isinstance(patient.risk_factors, dict):
        risk_names = list(patient.risk_factors)
    else:
        risk_names = patient.risk_factors
    risk_names.extend(patient.demographics)
    risk_names.extend(patient.measurements)
    return EvaluationResponse(
        disclaimer="This is an academic physician-support prototype, not an autonomous diagnostic system. Results require clinician review and validated medical evidence.",
        ranked_conditions=rank_conditions(repository.conditions(), patient.symptoms, risk_names),
    )
