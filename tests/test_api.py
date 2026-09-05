from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Condition, ConditionSymptom, Symptom


def test_evaluate_api_uses_test_database() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        symptom = Symptom(name="fever", description="demo")
        condition = Condition(name="Demo", severity=10, urgency=20, prior_probability=0, is_demo=True)
        condition.symptoms = [ConditionSymptom(symptom=symptom, weight=1)]
        session.add(condition)
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post("/evaluate", json={"symptoms": ["fever"]})
        assert response.status_code == 200
        body = response.json()
        assert body["ranked_conditions"][0]["condition"] == "Demo"
        assert "disclaimer" in body
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_invalid_evaluate_input_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post("/evaluate", json={"symptoms": []})
    assert response.status_code == 422
