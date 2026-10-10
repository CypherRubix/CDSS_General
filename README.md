# Clinical Decision Support System

This project implements a physician-support backend for a normalized CDSS knowledge base. It stores conditions, symptoms, risk factors, tests, and treatments in MySQL-compatible SQLAlchemy models and uses Bayesian inference to rank candidate diagnoses, estimate uncertainty, assess severity and urgency separately, recommend useful tests, and update results as test findings are entered.

This is not a medical diagnostic engine or a clinically validated probability model. Estimates use database-configured priors and finding/test parameters where available; bounded proxies or defaults may be used when calibrated parameters are unavailable.

## 1. Database setup

The project defaults to SQLite for local development and can be configured for MySQL in the environment file.

MySQL example:

```bash
mysql -u root -p
CREATE DATABASE clinical_cdss;
CREATE USER 'cdss_user'@'localhost' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON clinical_cdss.* TO 'cdss_user'@'localhost';
FLUSH PRIVILEGES;
```

The schema is defined in `database/schema.sql` and is created by SQLAlchemy on startup when using the configured database URL.

## 2. Environment variables

Use `.env.example` as the template:

```text
CDSS_DATABASE_URL=mysql+pymysql://cdss_user:change_me@localhost:3306/clinical_cdss
CDSS_SQL_ECHO=false
CDSS_DEMO_DATA=false
```

The settings are loaded from `.env` by `app/config.py` and use the `CDSS_` prefix.

## 3. How to start MySQL

On Windows with a local MySQL installation, start the service from Services or use the MySQL client directly.

Example:

```powershell
net start MySQL80
```

Then verify connectivity:

```powershell
mysql -u cdss_user -p -D clinical_cdss
```

## 4. How to install Python dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## 5. How to start FastAPI

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive Swagger UI.

## 6. Available endpoints

Core endpoints:

- `GET /health`
- `POST /evaluate`
- `GET /conditions`
- `GET /conditions/{id}`
- `POST /conditions`
- `POST /conditions/complete`
- `GET /symptoms`
- `POST /symptoms`
- `GET /risk-factors`
- `POST /risk-factors`
- `GET /tests`
- `POST /tests`
- `GET /treatments`
- `POST /treatments`
- `POST /conditions/{condition_id}/symptoms`
- `POST /conditions/{condition_id}/risk-factors`
- `POST /conditions/{condition_id}/tests`
- `POST /conditions/{condition_id}/treatments`
- `GET /conditions/{condition_id}/symptoms`
- `GET /conditions/{condition_id}/risk-factors`
- `GET /conditions/{condition_id}/tests`
- `GET /conditions/{condition_id}/treatments`

## 7. Example POST /evaluate request

```json
{
  "symptoms": ["fever", "cough", "shortness of breath"],
  "risk_factors": {
    "smoking": true,
    "age": 65,
    "bmi": 28,
    "systolic_bp": 150,
    "diastolic_bp": 95
  }
}
```

Structured risk factors are normalized to the risk-factor names provided in the database. The system matches relationship names that are explicitly stored.

## 8. Example POST /evaluate response

```json
{
  "disclaimer": "Clinical decision-support prototype: Bayesian estimates and recommendations are not clinically validated.",
  "ranked_conditions": [
    {
      "condition": "Pneumonia",
      "likelihood_score": 0.82,
      "severity": 8,
      "urgency": 7,
      "priority_score": 0.71,
      "matched_symptoms": [
        {"name": "fever", "weight": 0.8},
        {"name": "cough", "weight": 0.9}
      ],
      "matched_risk_factors": [
        {"name": "smoking", "weight": 0.7}
      ],
      "recommended_tests": [
        {
          "test_id": 2,
          "name": "Chest X-ray",
          "description": "Radiographic assessment",
          "purpose": "Confirm pulmonary findings",
          "priority": 1,
          "associated_conditions": ["Pneumonia"]
        }
      ],
      "treatments": [
        {
          "treatment_id": 5,
          "name": "Antibiotic therapy",
          "description": "Standard treatment according to local protocol",
          "treatment_type": "medication",
          "priority": 1,
          "notes": "Use per clinician guidance",
          "associated_condition": "Pneumonia"
        }
      ],
      "explanation": "Posterior probability is based on the recorded patient findings and condition parameters; some values may be uncalibrated proxies."
    }
  ]
}
```

## 9. Example condition creation request

```json
{
  "name": "Pneumonia",
  "description": "Lower respiratory tract infection",
  "severity": 8,
  "urgency": 7
}
```

## 10. Diagnostic inference and test selection

The evaluation endpoint uses Bayesian inference to rank conditions from recorded positive and negative findings, risk factors, and entered test results. It returns posterior probabilities, supporting and conflicting evidence, parameter limitations, and posterior entropy as an uncertainty estimate. Severity and urgency are assessed separately from diagnostic likelihood.

Where sufficient condition-test performance parameters are available, test recommendations can include expected information gain, calculated as the expected reduction in diagnostic entropy. If information gain cannot be calculated because performance parameters are missing, the system identifies that limitation and falls back to the recorded relationship priority. Entered test results can be submitted through the sequential evaluation endpoint to update the diagnostic distribution and next recommendations.

Clinical parameters are taken from database records. Where calibrated probabilities are unavailable, the system may use documented proxies; these estimates are not clinically validated and should be interpreted accordingly. An optional heuristic ranking path remains available for callers that explicitly disable Bayesian inference; it is not used as a model-comparison baseline.

## 11. Explanation of severity and urgency

Each condition stores its own `severity` and `urgency` on a scale of 1 to 10. These values are not mixed into the diagnosis likelihood itself. They are used separately in a priority calculation so the system distinguishes:

- how strongly the patient matches the condition
- how clinically severe or urgent the condition is

The priority score is a software prioritization signal, not a medically validated triage tool.

## 12. Important warning

This software is a decision-support prototype, not a diagnostic or triage authority. Its probability parameters may include uncalibrated proxies, and available evidence can be incomplete. Clinicians must interpret results using appropriate clinical judgment and local guidance; recommendations do not replace professional assessment.

## 13. Tests

```powershell
python -m pytest -q
```

## 14. Frontend
## 14. Frontend and Local Launching

The frontend is a dependency-free browser app in `frontend/`. Start the API from
the `clinical_cdss` directory, then serve the frontend from the repository root
on one of the allowed local origins:
The frontend is directly served by FastAPI at the root URL, or can optionally be served independently.

### Option A: One-step launch (Recommended)

Run the unified launcher from the `clinical_cdss` directory:

```powershell
# Terminal 1
cd ..
.\.venv\Scripts\Activate.ps1
cd clinical_cdss
python run.py
```

Then open **http://127.0.0.1:8000** in your browser.

- **Unified Web UI**: http://127.0.0.1:8000
- **Interactive Swagger API Docs**: http://127.0.0.1:8000/docs

### Option B: Direct Uvicorn

```powershell
python -m uvicorn app.main:app --reload
```

# Terminal 2
cd clinical_cdss\frontend
Open **http://127.0.0.1:8000**.

### Option C: Independent frontend server

```powershell
# Terminal 1: Backend
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
python -m http.server 5500
```

Open http://127.0.0.1:5500. The browser app uses `GET /symptoms`,
`GET /risk-factors`, `POST /evaluate`, all five resource list endpoints, and
the matching resource creation endpoints. Condition result tests and treatments
come directly from the evaluation response. Resource detail editing and delete
actions are not shown because the current backend does not expose update/delete
routes.
Open **http://127.0.0.1:5500**. Full CORS support is enabled.

The test suite uses an in-memory SQLite database and verifies condition creation, relationships, evaluation, ranking order, duplicate rejection, invalid input, and transaction rollback.
### Features Available in the Frontend:
1. **Overview Dashboard**: Live database record counts (Conditions, Symptoms, Risk Factors, Tests, Treatments, Patient Records) and database status.
2. **Patient Evaluation**: Enter patient demographics, search and select symptoms and risk factors, and run diagnostic assessments.
3. **Evaluation Results**: View transparent condition ranking, likelihood match percentage, severity, urgency, recommended diagnostic tests, and potential treatments.
4. **Save to Patient Records**: Click "Save to Patient Records" to persist clinical assessments to the database.
5. **Patient Records History**: Browse and retrieve past patient evaluations, including demographics, symptoms, and top matched conditions.
6. **Knowledge Base Explorer**: Browse and search all 5 clinical resource tables with full severity, urgency, and purpose attributes.
7. **Add Records**: Add new Conditions, Symptoms, Risk Factors, Tests, and Treatments directly to the database via interactive modal dialogs.
8. **Condition Relationship Linking**: Click "View Details & Links" on any condition to view and add linked symptoms (with weights), risk factors, diagnostic tests (with priorities), and treatments.
9. **Sample Data Seeder**: Automatically seeds standard clinical conditions upon first run if empty, or on-demand via the "Load Sample Medical Knowledge" button.
