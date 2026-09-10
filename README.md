# Clinical Decision Support System

This project implements a physician-support backend for a normalized CDSS knowledge base. It stores conditions, symptoms, risk factors, tests, and treatments in MySQL-compatible SQLAlchemy models and exposes the core APIs needed to rank candidate diagnoses from patient information.

This is not a medical diagnostic engine and it is not a clinically validated probability model. It only combines relationships and weights explicitly stored in the database.

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
  "disclaimer": "This is an initial software ranking model for physician support only; it is not a medically validated diagnostic probability model.",
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
      "explanation": "This result is based on the weighted relationship values explicitly stored for the condition, not a medically validated probability model."
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

## 10. Explanation of the ranking algorithm

The ranking is intentionally transparent:

- It matches supplied symptoms to `condition_symptoms` rows.
- It matches supplied risk factors to `condition_risk_factors` rows.
- It computes a normalized symptom score as the matched symptom weight divided by the total relevant symptom weight for the condition.
- It computes a normalized risk-factor score as the matched risk-factor weight divided by the total risk-factor weight for the condition.
- It combines them with configurable weights:

```text
final_score = (symptom_score * 0.70) + (risk_factor_score * 0.30)
```

These constants are stored in the ranking module and are easy to adjust later as evidence or clinical logic is added.

## 11. Explanation of severity and urgency

Each condition stores its own `severity` and `urgency` on a scale of 1 to 10. These values are not mixed into the diagnosis likelihood itself. They are used separately in a priority calculation so the system distinguishes:

- how strongly the patient matches the condition
- how clinically severe or urgent the condition is

The priority score is a software prioritization signal, not a medically validated triage tool.

## 12. Important warning

The scoring model is an initial software model and is NOT a medically validated diagnostic probability model.

It is only intended to make stored clinical relationships and weights explainable, traceable, and easy to extend with future evidence sources, Bayesian logic, likelihood ratios, audit logging, patient records, and authentication.

## 13. Tests

```powershell
python -m pytest -q
```

## 14. Frontend and Local Launching

The frontend is directly served by FastAPI at the root URL, or can optionally be served independently.

### Option A: One-step launch (Recommended)

Run the unified launcher from the `clinical_cdss` directory:

```powershell
python run.py
```

Then open **http://127.0.0.1:8000** in your browser.

- **Unified Web UI**: http://127.0.0.1:8000
- **Interactive Swagger API Docs**: http://127.0.0.1:8000/docs

### Option B: Direct Uvicorn

```powershell
python -m uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**.

### Option C: Independent frontend server

```powershell
# Terminal 1: Backend
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
python -m http.server 5500
```

Open **http://127.0.0.1:5500**. Full CORS support is enabled.

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
