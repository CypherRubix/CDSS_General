-- DEMONSTRATION DATA ONLY. These rows are not medical evidence and must be replaced.
INSERT INTO evidence (title, source, evidence_level, notes, is_demo)
VALUES ('DEMO: placeholder relationship reference', 'Local demonstration fixture', 'demo', 'Replace with a properly sourced publication before clinical use.', TRUE);

INSERT INTO conditions (name, description, severity, urgency, prior_probability, is_demo)
VALUES ('DEMO Condition A', 'Synthetic condition for local API demonstrations.', 50, 40, 0.10, TRUE),
       ('DEMO Condition B', 'Synthetic condition for local API demonstrations.', 80, 70, 0.05, TRUE);

INSERT INTO symptoms (name, description)
VALUES ('DEMO symptom one', 'Synthetic symptom.'), ('DEMO symptom two', 'Synthetic symptom.');

INSERT INTO risk_factors (name, description, type)
VALUES ('DEMO age factor', 'Synthetic age-related input key.', 'demographic'),
       ('DEMO measurement', 'Synthetic physiological input key.', 'physiological');

INSERT INTO tests (name, description, purpose, type)
VALUES ('DEMO laboratory test', 'Synthetic test.', 'Demonstrate test recommendations.', 'laboratory'),
       ('DEMO imaging test', 'Synthetic test.', 'Demonstrate test recommendations.', 'imaging');

INSERT INTO condition_symptoms (condition_id, symptom_id, weight, evidence_id)
SELECT c.condition_id, s.symptom_id, 2.00, e.evidence_id
FROM conditions c CROSS JOIN symptoms s CROSS JOIN evidence e
WHERE c.name = 'DEMO Condition A' AND s.name = 'DEMO symptom one'
    AND e.title = 'DEMO: placeholder relationship reference';

INSERT INTO condition_symptoms (condition_id, symptom_id, weight, evidence_id)
SELECT c.condition_id, s.symptom_id, 1.00, e.evidence_id
FROM conditions c CROSS JOIN symptoms s CROSS JOIN evidence e
WHERE c.name = 'DEMO Condition B' AND s.name = 'DEMO symptom two'
    AND e.title = 'DEMO: placeholder relationship reference';

INSERT INTO condition_risk_factors (condition_id, risk_factor_id, weight, relationship_description, evidence_id)
SELECT c.condition_id, r.risk_factor_id, 1.00, 'Synthetic relationship for local testing.', e.evidence_id
FROM conditions c CROSS JOIN risk_factors r CROSS JOIN evidence e
WHERE c.name = 'DEMO Condition A' AND r.name = 'DEMO age factor'
    AND e.title = 'DEMO: placeholder relationship reference';

INSERT INTO condition_tests (condition_id, test_id, priority, purpose, evidence_id)
SELECT c.condition_id, t.test_id, 1, 'Synthetic recommendation for local testing.', e.evidence_id
FROM conditions c CROSS JOIN tests t CROSS JOIN evidence e
WHERE c.name = 'DEMO Condition A' AND t.name = 'DEMO laboratory test'
    AND e.title = 'DEMO: placeholder relationship reference';
