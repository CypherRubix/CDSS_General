from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Condition, ConditionRiskFactor, ConditionSymptom, ConditionTest, ConditionTreatment, RiskFactor, Symptom, Test, Treatment


def build_test_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def override_db_factory(session_factory):
    def override_db():
        with session_factory() as session:
            yield session

    return override_db


def test_evaluate_api_uses_test_database() -> None:
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        symptom = Symptom(name="fever", description="demo")
        condition = Condition(name="Demo", description="Demo condition", severity=7, urgency=6)
        condition.symptoms = [ConditionSymptom(symptom=symptom, weight=1.0)]
        session.add(condition)
        session.commit()

    app.dependency_overrides[get_db] = override_db_factory(session_factory)
    try:
        with TestClient(app) as client:
            response = client.post("/evaluate", json={"symptoms": ["fever"]})
        assert response.status_code == 200
        body = response.json()
        assert body["ranked_conditions"][0]["condition"] == "Demo"
        assert "disclaimer" in body
        assert "likelihood_score" in body["ranked_conditions"][0]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_invalid_evaluate_input_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post("/evaluate", json={"symptoms": []})
    assert response.status_code == 422


def test_condition_management_and_ranking_workflow() -> None:
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)
    app.dependency_overrides[get_db] = override_db_factory(session_factory)
    try:
        with TestClient(app) as client:
            symptom_resp = client.post("/symptoms", json={"name": "fever", "description": "Raised temperature"})
            risk_resp = client.post("/risk-factors", json={"name": "smoking", "description": "Current smoker", "factor_type": "lifestyle"})
            test_resp = client.post("/tests", json={"name": "CBC", "description": "Complete blood count", "purpose": "Assess inflammation"})
            treatment_resp = client.post("/treatments", json={"name": "Antibiotics", "description": "Standard antibiotic therapy", "treatment_type": "medication"})
            condition_resp = client.post("/conditions", json={"name": "Pneumonia", "description": "Example respiratory infection", "severity": 8, "urgency": 7})
            assert symptom_resp.status_code == 200
            assert risk_resp.status_code == 200
            assert test_resp.status_code == 200
            assert treatment_resp.status_code == 200
            assert condition_resp.status_code == 200

            condition_id = condition_resp.json()["id"]
            symptom_id = symptom_resp.json()["id"]
            risk_id = risk_resp.json()["id"]
            test_id = test_resp.json()["id"]
            treatment_id = treatment_resp.json()["id"]

            rel_symptom = client.post(f"/conditions/{condition_id}/symptoms", json={"symptom_id": symptom_id, "weight": 0.9})
            rel_risk = client.post(f"/conditions/{condition_id}/risk-factors", json={"risk_factor_id": risk_id, "weight": 0.7})
            rel_test = client.post(f"/conditions/{condition_id}/tests", json={"test_id": test_id, "priority": 1, "purpose": "Check for infection"})
            rel_treatment = client.post(f"/conditions/{condition_id}/treatments", json={"treatment_id": treatment_id, "priority": 1, "notes": "Use as prescribed"})
            assert rel_symptom.status_code == 200
            assert rel_risk.status_code == 200
            assert rel_test.status_code == 200
            assert rel_treatment.status_code == 200

            evaluate = client.post("/evaluate", json={"symptoms": ["fever"], "risk_factors": ["smoking"]})
            assert evaluate.status_code == 200
            body = evaluate.json()
            assert body["ranked_conditions"][0]["condition"] == "Pneumonia"
            assert body["ranked_conditions"][0]["recommended_tests"][0]["name"] == "CBC"
            assert body["ranked_conditions"][0]["treatments"][0]["name"] == "Antibiotics"
            assert body["ranked_conditions"][0]["matched_symptoms"][0]["name"] == "fever"
            assert body["ranked_conditions"][0]["matched_risk_factors"][0]["name"] == "smoking"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_duplicate_and_invalid_data_are_rejected() -> None:
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)
    app.dependency_overrides[get_db] = override_db_factory(session_factory)
    try:
        with TestClient(app) as client:
            assert client.post("/conditions", json={"name": "A", "severity": 5, "urgency": 4}).status_code == 200
            assert client.post("/conditions", json={"name": "A", "severity": 5, "urgency": 4}).status_code == 409
            assert client.post("/conditions", json={"name": "", "severity": 11, "urgency": 4}).status_code == 422
            assert client.post("/symptoms", json={"name": "pain", "description": "x"}).status_code == 200
            assert client.post("/symptoms", json={"name": "pain", "description": "x"}).status_code == 409
            assert client.post("/risk-factors", json={"name": "smoker", "description": "x", "factor_type": "lifestyle"}).status_code == 200
            assert client.post("/risk-factors", json={"name": "smoker", "description": "x", "factor_type": "lifestyle"}).status_code == 409
            assert client.post("/conditions/999/symptoms", json={"symptom_id": 1, "weight": 0.4}).status_code == 404
            assert client.post("/conditions/1/symptoms", json={"symptom_id": 999, "weight": 0.4}).status_code == 404
            assert client.post("/conditions/1/symptoms", json={"symptom_id": 1, "weight": -1}).status_code == 422
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_complete_condition_transaction_rollback() -> None:
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)
    app.dependency_overrides[get_db] = override_db_factory(session_factory)
    try:
        with TestClient(app) as client:
            symptom = client.post("/symptoms", json={"name": "wheeze", "description": "airflow sound"})
            risk = client.post("/risk-factors", json={"name": "asthma", "description": "history", "factor_type": "medical_history"})
            test = client.post("/tests", json={"name": "spirometry", "description": "lung function", "purpose": "assess airflow"})
            treatment = client.post("/treatments", json={"name": "inhaler", "description": "bronchodilator", "treatment_type": "medication"})
            assert symptom.status_code == 200
            assert risk.status_code == 200
            assert test.status_code == 200
            assert treatment.status_code == 200

            response = client.post(
                "/conditions/complete",
                json={
                    "condition": {"name": "Asthma", "severity": 6, "urgency": 5, "description": "Reactive airway disease"},
                    "symptoms": [{"symptom_id": symptom.json()["id"], "weight": 0.8}],
                    "risk_factors": [{"risk_factor_id": risk.json()["id"], "weight": 0.6}],
                    "tests": [{"test_id": test.json()["id"], "priority": 1, "purpose": "Confirm diagnosis"}],
                    "treatments": [{"treatment_id": treatment.json()["id"], "priority": 1, "notes": "Use for exacerbations"}],
                },
            )
            assert response.status_code == 200
            assert client.get("/conditions").json()[0]["name"] == "Asthma"

            bad_response = client.post(
                "/conditions/complete",
                json={
                    "condition": {"name": "Asthma Duplicate", "severity": 7, "urgency": 5},
                    "symptoms": [{"symptom_id": 9999, "weight": 0.8}],
                    "risk_factors": [],
                    "tests": [],
                    "treatments": [],
                },
            )
            assert bad_response.status_code == 404
            assert client.get("/conditions").json()[-1]["name"] == "Asthma"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
