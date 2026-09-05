# Standalone Clinical Decision Support System

This is a local, independent academic prototype for physician support. It is not an autonomous diagnostic system and must not be used for clinical decisions without clinician review and properly sourced, validated medical evidence.

## What is included

- FastAPI endpoints for knowledge lookup and `/evaluate`.
- SQLAlchemy models for MySQL-compatible relational storage.
- Normalized condition, symptom, risk-factor, test, evidence, and relationship tables.
- Explainable configurable ranking based on symptom matches, risk-factor matches, stored prior contribution, severity, and urgency.
- Test recommendations and traceable evidence references.
- SQLite-compatible automated tests that do not require a production database.
- Clearly labeled synthetic SQL seed data only.

Patient input is request-scoped. It is not stored in the medical knowledge tables and this project does not create a patient-record system.

## Local setup

From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The default configuration uses `sqlite:///./clinical_cdss.db`, which is convenient for local experimentation. The `.env.example` uses a MySQL URL instead:

```text
CDSS_DATABASE_URL=mysql+pymysql://cdss_user:change_me@localhost:3306/clinical_cdss
CDSS_SQL_ECHO=false
CDSS_DEMO_DATA=false
```

Replace `change_me` locally; never commit a real password. Create the MySQL database and user separately, then either let SQLAlchemy create tables on API startup or run `database/schema.sql` with your MySQL client. Run `database/seed.sql` only when you intentionally want the synthetic demo rows.

## Run the API

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation. Health check:

```text
GET /health
```

## Example evaluation request

```json
{
  "symptoms": ["DEMO symptom one"],
  "risk_factors": ["DEMO age factor"],
  "demographics": {"age": 65},
  "measurements": {"DEMO measurement": 1}
}
```

The API returns `ranked_conditions`. Each result includes a configurable `likelihood_score`, separate `severity`, `urgency`, and `clinical_priority_score`, matched inputs, recommended tests, evidence references, and an explanation of the score. These scores are ranking signals, not validated clinical probabilities.

Example response shape:

```json
{
  "disclaimer": "This is an academic physician-support prototype...",
  "ranked_conditions": [
    {
      "condition": "DEMO Condition A",
      "likelihood_score": 3.1,
      "severity": 50.0,
      "urgency": 40.0,
      "clinical_priority_score": 4.495,
      "matched_symptoms": ["DEMO symptom one"],
      "relevant_risk_factors": ["DEMO age factor"],
      "recommended_tests": [],
      "evidence": [],
      "explanation": "..."
    }
  ]
}
```

The example response is illustrative. Real response contents depend on the rows loaded into the configured database.

## Tests

```powershell
python -m pytest -q
```

The tests use an in-memory SQLite database and cover ranking, explanations, relationship traversal, recommendations, API evaluation, and invalid input handling. They do not connect to MySQL.

## Schema design

`conditions`, `symptoms`, `risk_factors`, `tests`, and `evidence` are independent entities. The `condition_symptoms`, `condition_risk_factors`, and `condition_tests` tables implement many-to-many relationships with composite primary keys and foreign keys. Relationship-specific weights and evidence references stay on those association tables instead of being duplicated in the main entities.

Risk factors are named concepts with a `type`; request values remain separate in `risk_factors`, `demographics`, and `measurements`. The initial engine matches known names and does not pretend that age, blood pressure, BMI, or similar values are binary flags. Value-aware rules can be added later without changing the normalized schema.

## Important TODOs before any serious use

- Replace all `DEMO` rows with reviewed, properly sourced evidence.
- Define and validate scoring weights with clinical subject-matter experts.
- Add evidence versioning, provenance review status, and audit logging.
- Add authentication, authorization, rate limiting, and production migrations.
- Add structured value/range matching for measurements and demographic data.
- Add clinician review workflows and stronger integration tests against a controlled MySQL instance.
- Do not claim diagnostic accuracy or use the demonstration ranking as a medical probability.
