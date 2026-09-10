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


def test_stats_and_details_endpoints() -> None:
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)
    app.dependency_overrides[get_db] = override_db_factory(session_factory)
    try:
        with TestClient(app) as client:
            stats_initial = client.get("/stats").json()
            assert stats_initial["conditions"] == 0

            s_res = client.post("/symptoms", json={"name": "Cough", "description": "Productive"})
            r_res = client.post("/risk-factors", json={"name": "Smoker", "description": "Heavy", "factor_type": "lifestyle"})
            t_res = client.post("/tests", json={"name": "X-Ray", "description": "Chest imaging", "purpose": "Check lungs"})
            tx_res = client.post("/treatments", json={"name": "Inhaler", "description": "Bronchodilator", "treatment_type": "medication"})
            c_res = client.post("/conditions", json={"name": "Bronchitis", "description": "Airway inflammation", "severity": 6, "urgency": 5})

            assert s_res.status_code == 200
            assert r_res.status_code == 200
            assert t_res.status_code == 200
            assert tx_res.status_code == 200
            assert c_res.status_code == 200

            # Verify enriched fields
            conds = client.get("/conditions").json()
            assert conds[0]["severity"] == 6
            assert conds[0]["urgency"] == 5

            tests_resp = client.get("/tests").json()
            assert tests_resp[0]["purpose"] == "Check lungs"

            # Link relationships
            cid = c_res.json()["id"]
            client.post(f"/conditions/{cid}/symptoms", json={"symptom_id": s_res.json()["id"], "weight": 0.85})
            client.post(f"/conditions/{cid}/risk-factors", json={"risk_factor_id": r_res.json()["id"], "weight": 0.65})
            client.post(f"/conditions/{cid}/tests", json={"test_id": t_res.json()["id"], "priority": 1, "purpose": "Inspect airway"})
            client.post(f"/conditions/{cid}/treatments", json={"treatment_id": tx_res.json()["id"], "priority": 1, "notes": "Use PRN"})

            # Verify details endpoint
            details = client.get(f"/conditions/{cid}/details").json()
            assert details["name"] == "Bronchitis"
            assert details["symptoms"][0]["name"] == "Cough"
            assert details["symptoms"][0]["weight"] == 0.85
            assert details["risk_factors"][0]["name"] == "Smoker"
            assert details["tests"][0]["name"] == "X-Ray"
            assert details["treatments"][0]["name"] == "Inhaler"

            # Verify stats incremented
            stats_after = client.get("/stats").json()
            assert stats_after["conditions"] == 1
            assert stats_after["symptoms"] == 1
            assert stats_after["risk_factors"] == 1
            assert stats_after["tests"] == 1
            assert stats_after["treatments"] == 1
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_evaluation_records_lifecycle() -> None:
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)
    app.dependency_overrides[get_db] = override_db_factory(session_factory)
    try:
        with TestClient(app) as client:
            records_before = client.get("/evaluations").json()
            assert len(records_before) == 0

            save_res = client.post(
                "/evaluations",
                json={
                    "age": 62,
                    "sex": "Female",
                    "symptoms": ["Fever", "Cough"],
                    "risk_factors": ["Smoking"],
                    "top_condition": "Pneumonia",
                    "likelihood_score": 0.85,
                    "priority_score": 0.76,
                    "results_json": '{"ranked_conditions": [{"condition": "Pneumonia"}]}',
                },
            )
            assert save_res.status_code == 200
            saved = save_res.json()
            assert saved["id"] is not None
            assert saved["top_condition"] == "Pneumonia"
            assert saved["age"] == 62
            assert saved["symptoms"] == ["Fever", "Cough"]

            records_after = client.get("/evaluations").json()
            assert len(records_after) == 1
            assert records_after[0]["id"] == saved["id"]
            assert records_after[0]["top_condition"] == "Pneumonia"

            stats = client.get("/stats").json()
            assert stats["evaluations"] == 1
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_seed_demo_and_frontend_serving() -> None:
    engine = build_test_db()
    session_factory = sessionmaker(bind=engine)
    app.dependency_overrides[get_db] = override_db_factory(session_factory)
    try:
        with TestClient(app) as client:
            seed_res = client.post("/seed-demo")
            assert seed_res.status_code == 200
            stats = client.get("/stats").json()
            assert stats["conditions"] == 5
            assert stats["symptoms"] >= 10
            assert stats["risk_factors"] >= 5

            # Test static frontend serving
            frontend_res = client.get("/")
            assert frontend_res.status_code == 200
            assert "Clarity CDSS" in frontend_res.text or "<div id=\"app\">" in frontend_res.text

            app_js_res = client.get("/app.js")
            assert app_js_res.status_code == 200
            assert "API_BASE" in app_js_res.text
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
