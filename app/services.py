from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Condition,
    ConditionRiskFactor,
    ConditionSymptom,
    ConditionTest,
    ConditionTreatment,
    EvaluationRecord,
    Evidence,
    RiskFactor,
    Symptom,
    Test,
    Treatment,
)


class ResourceNotFoundError(Exception):
    pass


class DuplicateResourceError(Exception):
    pass


class InvalidInputError(Exception):
    pass


class KnowledgeRepository:
    """Data access layer for the CDSS knowledge tables."""

    def __init__(self, db: Session):
        self.db = db

    def conditions(self) -> list[Condition]:
        statement = select(Condition).order_by(Condition.name)
        return list(self.db.scalars(statement).all())

    def conditions_with_relations(self) -> list[Condition]:
        statement = select(Condition).options(
            selectinload(Condition.symptoms).selectinload(ConditionSymptom.symptom),
            selectinload(Condition.risk_factors).selectinload(ConditionRiskFactor.risk_factor),
            selectinload(Condition.tests).selectinload(ConditionTest.test),
            selectinload(Condition.treatments).selectinload(ConditionTreatment.treatment),
        )
        return list(self.db.scalars(statement).unique().all())

    def symptoms(self) -> list[Symptom]:
        return list(self.db.scalars(select(Symptom).order_by(Symptom.name)).all())

    def risk_factors(self) -> list[RiskFactor]:
        return list(self.db.scalars(select(RiskFactor).order_by(RiskFactor.name)).all())

    def tests(self) -> list[Test]:
        return list(self.db.scalars(select(Test).order_by(Test.name)).all())

    def treatments(self) -> list[Treatment]:
        return list(self.db.scalars(select(Treatment).order_by(Treatment.name)).all())

    def get_condition(self, condition_id: int) -> Condition | None:
        return self.db.get(Condition, condition_id)

    def get_condition_by_name(self, name: str) -> Condition | None:
        return self.db.scalar(select(Condition).where(Condition.name == name))

    def get_symptom(self, symptom_id: int) -> Symptom | None:
        return self.db.get(Symptom, symptom_id)

    def get_symptom_by_name(self, name: str) -> Symptom | None:
        return self.db.scalar(select(Symptom).where(Symptom.name == name))

    def get_risk_factor(self, risk_factor_id: int) -> RiskFactor | None:
        return self.db.get(RiskFactor, risk_factor_id)

    def get_risk_factor_by_name(self, name: str) -> RiskFactor | None:
        return self.db.scalar(select(RiskFactor).where(RiskFactor.name == name))

    def get_test(self, test_id: int) -> Test | None:
        return self.db.get(Test, test_id)

    def get_test_by_name(self, name: str) -> Test | None:
        return self.db.scalar(select(Test).where(Test.name == name))

    def get_treatment(self, treatment_id: int) -> Treatment | None:
        return self.db.get(Treatment, treatment_id)

    def get_treatment_by_name(self, name: str) -> Treatment | None:
        return self.db.scalar(select(Treatment).where(Treatment.name == name))

    def get_condition_detail(self, condition_id: int) -> Condition | None:
        statement = (
            select(Condition)
            .where(Condition.condition_id == condition_id)
            .options(
                selectinload(Condition.symptoms).selectinload(ConditionSymptom.symptom),
                selectinload(Condition.risk_factors).selectinload(ConditionRiskFactor.risk_factor),
                selectinload(Condition.tests).selectinload(ConditionTest.test),
                selectinload(Condition.treatments).selectinload(ConditionTreatment.treatment),
            )
        )
        return self.db.scalar(statement)

    def stats(self) -> dict[str, int]:
        return {
            "conditions": int(self.db.scalar(select(func.count(Condition.condition_id))) or 0),
            "symptoms": int(self.db.scalar(select(func.count(Symptom.symptom_id))) or 0),
            "risk_factors": int(self.db.scalar(select(func.count(RiskFactor.risk_factor_id))) or 0),
            "tests": int(self.db.scalar(select(func.count(Test.test_id))) or 0),
            "treatments": int(self.db.scalar(select(func.count(Treatment.treatment_id))) or 0),
            "evaluations": int(self.db.scalar(select(func.count(EvaluationRecord.id))) or 0),
        }

    def save_evaluation(
        self,
        symptoms: list[str],
        risk_factors: list[str],
        age: int | None = None,
        sex: str | None = None,
        top_condition: str | None = None,
        likelihood_score: float | None = None,
        priority_score: float | None = None,
        results_json: str | None = None,
    ) -> EvaluationRecord:
        record = EvaluationRecord(
            age=age,
            sex=sex,
            symptoms=json.dumps(symptoms),
            risk_factors=json.dumps(risk_factors),
            top_condition=top_condition,
            likelihood_score=likelihood_score,
            priority_score=priority_score,
            results_json=results_json,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def list_evaluations(self, limit: int = 50) -> list[EvaluationRecord]:
        statement = select(EvaluationRecord).order_by(EvaluationRecord.created_at.desc()).limit(limit)
        return list(self.db.scalars(statement).all())


def seed_initial_clinical_data(db: Session, force: bool = False) -> int:
    """Populates standard clinical knowledge base records if empty or forced."""
    repo = KnowledgeRepository(db)
    if not force and repo.stats()["conditions"] > 0:
        return 0

    # 1. Evidence
    evidence = db.scalar(select(Evidence).limit(1))
    if not evidence:
        evidence = Evidence(
            title="Consensus Clinical Guidelines & Evidence Base",
            authors="CDSS Medical Advisory Board",
            publication_year=2024,
            source="Clinical Decision Support Standard Reference",
            is_demo=False,
        )
        db.add(evidence)
        db.flush()

    # 2. Symptoms
    symptom_defs = [
        ("Fever", "Elevated body temperature above 38.0°C (100.4°F)"),
        ("Cough", "Sudden reflex expulsion of air from the lungs, dry or productive"),
        ("Shortness of breath", "Subjective sensation of uncomfortable or difficult breathing (dyspnea)"),
        ("Chest pain", "Pain, pressure, or tightness across anterior chest wall"),
        ("Wheezing", "High-pitched musical adventitious sound during exhalation"),
        ("Fatigue", "Generalized lethargy, malaise, or lack of energy"),
        ("Headache", "Diffuse or localized cranial pain"),
        ("Sore throat", "Painful, dry, or scratchy feeling in the pharynx"),
        ("Sputum production", "Expectorated mucus or phlegm from lower respiratory tract"),
        ("Dizziness", "Lightheadedness, unsteadiness, or presyncopal sensation"),
        ("Muscle aches", "Diffuse myalgia or body soreness"),
        ("Chest tightness", "Constrictive pressure in the thorax without sharp pleuritic quality"),
    ]
    symptom_map: dict[str, Symptom] = {}
    for name, desc in symptom_defs:
        sym = repo.get_symptom_by_name(name)
        if not sym:
            sym = Symptom(name=name, description=desc)
            db.add(sym)
            db.flush()
        symptom_map[name.casefold()] = sym

    # 3. Risk factors
    risk_defs = [
        ("Smoking", "Current or significant past tobacco smoke exposure", "lifestyle"),
        ("Age > 65", "Elderly patient demographic associated with heightened vulnerability", "demographic"),
        ("Hypertension history", "Documented history of essential or secondary high blood pressure", "medical_history"),
        ("Asthma history", "Diagnosed reactive airway disease or prior bronchospasm history", "medical_history"),
        ("Diabetes", "Type 1 or Type 2 diabetes mellitus", "medical_history"),
        ("Immunocompromised", "Active immunosuppressive medication or immunodeficiency", "medical_history"),
        ("Chronic lung disease", "COPD, bronchiectasis, or interstitial lung disease", "medical_history"),
    ]
    risk_map: dict[str, RiskFactor] = {}
    for name, desc, f_type in risk_defs:
        rf = repo.get_risk_factor_by_name(name)
        if not rf:
            rf = RiskFactor(name=name, description=desc, factor_type=f_type)
            db.add(rf)
            db.flush()
        risk_map[name.casefold()] = rf

    # 4. Tests
    test_defs = [
        ("Chest X-Ray", "Standard PA and lateral radiographic view of thorax", "Assess pulmonary infiltrate, consolidation, or effusions", "imaging"),
        ("Complete Blood Count (CBC)", "Hematologic analysis including WBC and differential", "Identify leukocytosis or markers of systemic infection", "laboratory"),
        ("Spirometry / Peak Flow", "Pulmonary function assessment measuring FEV1 and peak expiratory flow", "Assess airway obstruction reversibility", "pulmonary"),
        ("Pulse Oximetry", "Non-invasive transcutaneous arterial oxygen saturation measurement", "Detect hypoxemia and track SpO2", "physiological"),
        ("Rapid Influenza PCR", "Multiplex molecular test for Influenza A and B viral RNA", "Confirm viral influenza infection", "laboratory"),
        ("Blood Pressure Monitoring", "Serial or continuous non-invasive arterial pressure measurement", "Assess systolic and diastolic hypertension severity", "physiological"),
        ("12-Lead ECG", "Standard electrocardiogram recording cardiac electrical vectors", "Rule out acute myocardial ischemia or dysrhythmia", "cardiac"),
    ]
    test_map: dict[str, Test] = {}
    for name, desc, purpose, t_type in test_defs:
        tst = repo.get_test_by_name(name)
        if not tst:
            tst = Test(name=name, description=desc, purpose=purpose, type=t_type)
            db.add(tst)
            db.flush()
        test_map[name.casefold()] = tst

    # 5. Treatments
    treatment_defs = [
        ("Antibiotic therapy", "Broad-spectrum or guideline-concordant antimicrobial therapy", "medication"),
        ("Albuterol Inhaler", "Short-acting beta-2 adrenergic receptor agonist", "medication"),
        ("Oral Corticosteroids", "Systemic anti-inflammatory glucocorticoid (prednisone/prednisolone)", "medication"),
        ("Oseltamivir (Tamiflu)", "Antiviral neuraminidase inhibitor for influenza", "medication"),
        ("Supplemental Oxygen", "High or low flow oxygen delivery to maintain SpO2 >= 92%", "respiratory_support"),
        ("Supportive Hydration & Rest", "Oral fluids, antipyretics, and supportive recovery protocol", "supportive_care"),
        ("IV Antihypertensive Therapy", "Carefully titrated parenteral labetalol or nicardipine", "medication"),
        ("ICU Admission", "Continuous hemodynamics and arterial line monitoring in intensive care", "procedure"),
    ]
    treatment_map: dict[str, Treatment] = {}
    for name, desc, t_type in treatment_defs:
        tx = repo.get_treatment_by_name(name)
        if not tx:
            tx = Treatment(name=name, description=desc, treatment_type=t_type)
            db.add(tx)
            db.flush()
        treatment_map[name.casefold()] = tx

    # 6. Conditions & Relationships
    condition_configs = [
        {
            "name": "Pneumonia",
            "description": "Acute infection of the pulmonary parenchyma causing alveolar inflammation.",
            "severity": 8,
            "urgency": 7,
            "symptoms": [("Fever", 0.85), ("Cough", 0.90), ("Shortness of breath", 0.80), ("Chest pain", 0.65), ("Fatigue", 0.50)],
            "risks": [("Smoking", 0.70), ("Age > 65", 0.60), ("Immunocompromised", 0.80), ("Chronic lung disease", 0.75)],
            "tests": [("Chest X-Ray", 1, "Confirm pulmonary infiltrate"), ("Complete Blood Count (CBC)", 2, "Check leukocytosis"), ("Pulse Oximetry", 1, "Detect hypoxemia")],
            "treatments": [("Antibiotic therapy", 1, "Empiric community-acquired pneumonia regimen"), ("Supplemental Oxygen", 2, "Titrate SpO2 >= 92%"), ("Supportive Hydration & Rest", 3, "Encourage oral rehydration")],
        },
        {
            "name": "Asthma Exacerbation",
            "description": "Acute or subacute progressive worsening of shortness of breath, wheezing, and chest tightness.",
            "severity": 7,
            "urgency": 7,
            "symptoms": [("Wheezing", 0.95), ("Shortness of breath", 0.85), ("Cough", 0.70), ("Chest tightness", 0.80)],
            "risks": [("Asthma history", 0.95), ("Smoking", 0.50), ("Age > 65", 0.40)],
            "tests": [("Spirometry / Peak Flow", 1, "Assess degree of airflow limitation"), ("Pulse Oximetry", 1, "Assess oxygen saturation")],
            "treatments": [("Albuterol Inhaler", 1, "Administer 4-8 puffs via spacer or nebulizer"), ("Oral Corticosteroids", 2, "5-day course to accelerate resolution")],
        },
        {
            "name": "Influenza (Flu)",
            "description": "Acute viral respiratory infection characterized by sudden onset of fever, myalgia, and fatigue.",
            "severity": 5,
            "urgency": 4,
            "symptoms": [("Fever", 0.90), ("Fatigue", 0.85), ("Muscle aches", 0.80), ("Headache", 0.70), ("Cough", 0.75), ("Sore throat", 0.60)],
            "risks": [("Age > 65", 0.60), ("Immunocompromised", 0.70), ("Diabetes", 0.50)],
            "tests": [("Rapid Influenza PCR", 1, "Differentiate Flu A / B from other viral syndromes")],
            "treatments": [("Oseltamivir (Tamiflu)", 1, "Start within 48 hours of symptom onset"), ("Supportive Hydration & Rest", 2, "Fluids and antipyretics for fever")],
        },
        {
            "name": "Acute Bronchitis",
            "description": "Transient inflammation of the tracheobronchial tree presenting with productive cough.",
            "severity": 4,
            "urgency": 3,
            "symptoms": [("Cough", 0.90), ("Sputum production", 0.75), ("Fatigue", 0.50), ("Sore throat", 0.45)],
            "risks": [("Smoking", 0.65), ("Chronic lung disease", 0.50)],
            "tests": [("Chest X-Ray", 2, "Exclude pneumonia if high fever or tachypnea present")],
            "treatments": [("Supportive Hydration & Rest", 1, "Self-limiting condition; hydration and honey/lozenges")],
        },
        {
            "name": "Hypertensive Crisis",
            "description": "Severe arterial blood pressure elevation with risk of acute organ dysfunction.",
            "severity": 9,
            "urgency": 9,
            "symptoms": [("Headache", 0.80), ("Chest pain", 0.75), ("Shortness of breath", 0.70), ("Dizziness", 0.75)],
            "risks": [("Hypertension history", 0.95), ("Smoking", 0.55), ("Diabetes", 0.60)],
            "tests": [("Blood Pressure Monitoring", 1, "Serial readings in both arms"), ("12-Lead ECG", 1, "Screen for left ventricular strain or acute ischemia")],
            "treatments": [("IV Antihypertensive Therapy", 1, "Controlled MAP reduction by max 25% in hour 1"), ("ICU Admission", 2, "Continuous hemodynamic monitoring")],
        },
    ]

    count = 0
    for cfg in condition_configs:
        cond = repo.get_condition_by_name(cfg["name"])
        if not cond:
            cond = Condition(name=cfg["name"], description=cfg["description"], severity=cfg["severity"], urgency=cfg["urgency"])
            db.add(cond)
            db.flush()
            count += 1

            for s_name, weight in cfg["symptoms"]:
                sym_obj = symptom_map.get(s_name.casefold())
                if sym_obj:
                    db.add(ConditionSymptom(condition_id=cond.condition_id, symptom_id=sym_obj.symptom_id, weight=weight, evidence_id=evidence.evidence_id))

            for r_name, weight in cfg["risks"]:
                rf_obj = risk_map.get(r_name.casefold())
                if rf_obj:
                    db.add(ConditionRiskFactor(condition_id=cond.condition_id, risk_factor_id=rf_obj.risk_factor_id, weight=weight, evidence_id=evidence.evidence_id))

            for t_name, priority, purpose in cfg["tests"]:
                tst_obj = test_map.get(t_name.casefold())
                if tst_obj:
                    db.add(ConditionTest(condition_id=cond.condition_id, test_id=tst_obj.test_id, priority=priority, purpose=purpose, evidence_id=evidence.evidence_id))

            for tx_name, priority, notes in cfg["treatments"]:
                tx_obj = treatment_map.get(tx_name.casefold())
                if tx_obj:
                    db.add(ConditionTreatment(condition_id=cond.condition_id, treatment_id=tx_obj.treatment_id, priority=priority, notes=notes))

    db.commit()
    return count


def _lower(value: str | None) -> str:
    return (value or "").strip().casefold()


def _matching_name(values: Iterable[str], target: str) -> bool:
    return any(_lower(item) == _lower(target) for item in values)


from dataclasses import dataclass, field

from .ranking import rank_conditions as _rank_conditions


@dataclass
class LegacyTestRecommendation:
    name: str
    purpose: str | None = None
    type: str | None = None
    priority: int = 1
    evidence: list = field(default_factory=list)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


@dataclass
class LegacyRankedCondition:
    condition: str
    likelihood_score: float
    severity: float
    urgency: float
    clinical_priority_score: float
    matched_symptoms: list[str] = field(default_factory=list)
    relevant_risk_factors: list[str] = field(default_factory=list)
    recommended_tests: list[LegacyTestRecommendation] = field(default_factory=list)
    evidence: list = field(default_factory=list)
    explanation: str = ""

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


def rank_conditions_legacy(
    conditions: Iterable[Condition],
    symptoms: Iterable[str],
    risk_factors: Iterable[str],
) -> list[LegacyRankedCondition]:
    supplied_symptoms = {value.casefold().strip() for value in symptoms}
    supplied_risks = {value.casefold().strip() for value in risk_factors}
    ranked: list[LegacyRankedCondition] = []

    for condition in conditions:
        matched_symptom_relations = [
            relation for relation in condition.symptoms if relation.symptom.name.casefold() in supplied_symptoms
        ]
        matched_risk_relations = [
            relation for relation in condition.risk_factors if relation.risk_factor.name.casefold() in supplied_risks
        ]
        if not matched_symptom_relations:
            continue

        symptom_score = sum(float(item.weight) for item in matched_symptom_relations)
        risk_score = sum(float(item.weight) for item in matched_risk_relations)
        prior_score = float(condition.prior_probability or 0)
        likelihood = round(symptom_score + risk_score + prior_score, 4)
        severity = float(condition.severity)
        urgency = float(condition.urgency)
        priority = round(likelihood * (1 + (severity + urgency) / 200), 4)
        matched_names = [item.symptom.name for item in matched_symptom_relations]
        risk_names = [item.risk_factor.name for item in matched_risk_relations]

        ranked.append(
            LegacyRankedCondition(
                condition=condition.name,
                likelihood_score=likelihood,
                severity=severity,
                urgency=urgency,
                clinical_priority_score=priority,
                matched_symptoms=matched_names,
                relevant_risk_factors=risk_names,
                recommended_tests=[
                    LegacyTestRecommendation(
                        name=relation.test.name,
                        purpose=relation.purpose or relation.test.purpose,
                        type=relation.test.type,
                        priority=relation.priority,
                        evidence=[],
                    )
                    for relation in sorted(condition.tests, key=lambda item: item.priority)
                ],
                evidence=[],
                explanation=(
                    f"Matched {len(matched_names)} supplied symptom(s) with configurable contribution {symptom_score:.2f}; "
                    f"matched {len(risk_names)} risk factor(s) with contribution {risk_score:.2f}. "
                    f"The stored prior contribution is {prior_score:.4f}. Severity and urgency are applied separately to "
                    "clinical priority. These are ranking signals, not validated clinical probabilities."
                ),
            )
        )

    return sorted(ranked, key=lambda item: (-item.clinical_priority_score, -item.likelihood_score, item.condition))


# Backwards-compatible export expected by older code.
rank_conditions = rank_conditions_legacy

