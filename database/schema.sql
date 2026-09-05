CREATE TABLE evidence (
    evidence_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    authors VARCHAR(500),
    publication_year SMALLINT,
    source VARCHAR(255),
    doi VARCHAR(255) UNIQUE,
    url VARCHAR(1000),
    evidence_level VARCHAR(100),
    notes TEXT,
    is_demo BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE conditions (
    condition_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    severity DECIMAL(5,2) NOT NULL DEFAULT 0,
    urgency DECIMAL(5,2) NOT NULL DEFAULT 0,
    prior_probability DECIMAL(8,6),
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_conditions_name (name)
);

CREATE TABLE symptoms (
    symptom_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    INDEX idx_symptoms_name (name)
);

CREATE TABLE risk_factors (
    risk_factor_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    factor_type VARCHAR(100) NOT NULL,
    INDEX idx_risk_factors_factor_type (factor_type)
);

CREATE TABLE tests (
    test_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    purpose TEXT
);

CREATE TABLE treatments (
    treatment_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    treatment_type VARCHAR(100) NOT NULL,
    INDEX idx_treatments_type (treatment_type)
);

CREATE TABLE condition_symptoms (
    condition_id INT NOT NULL,
    symptom_id INT NOT NULL,
    weight DECIMAL(5,2) NOT NULL DEFAULT 1,
    frequency DECIMAL(5,2),
    sensitivity DECIMAL(5,2),
    specificity DECIMAL(5,2),
    evidence_id INT,
    PRIMARY KEY (condition_id, symptom_id),
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id) ON DELETE CASCADE,
    FOREIGN KEY (symptom_id) REFERENCES symptoms(symptom_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id) ON DELETE SET NULL
);

CREATE TABLE condition_risk_factors (
    condition_id INT NOT NULL,
    risk_factor_id INT NOT NULL,
    weight DECIMAL(5,2) NOT NULL DEFAULT 1,
    relationship_description TEXT,
    evidence_id INT,
    PRIMARY KEY (condition_id, risk_factor_id),
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id) ON DELETE CASCADE,
    FOREIGN KEY (risk_factor_id) REFERENCES risk_factors(risk_factor_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id) ON DELETE SET NULL
);

CREATE TABLE condition_tests (
    condition_id INT NOT NULL,
    test_id INT NOT NULL,
    priority INT NOT NULL DEFAULT 1,
    purpose TEXT,
    evidence_id INT,
    PRIMARY KEY (condition_id, test_id),
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES tests(test_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id) ON DELETE SET NULL
);

CREATE TABLE condition_treatments (
    condition_id INT NOT NULL,
    treatment_id INT NOT NULL,
    priority INT NOT NULL DEFAULT 1,
    notes TEXT,
    PRIMARY KEY (condition_id, treatment_id),
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id) ON DELETE CASCADE,
    FOREIGN KEY (treatment_id) REFERENCES treatments(treatment_id) ON DELETE CASCADE
);
