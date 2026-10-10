import pytest
from app.database import Base, engine, get_db
from app.services import seed_initial_data
from app.research_evaluation import (
    evaluate_case_model_a,
    evaluate_case_model_b,
    evaluate_case_model_c,
    run_research_benchmark,
    BENCHMARK_CASES,
)

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    seed_initial_data(db)
    yield db
    db.close()

def test_benchmark_cases_structure():
    assert len(BENCHMARK_CASES) >= 5
    for case in BENCHMARK_CASES:
        assert "case_id" in case
        assert "true_condition" in case
        assert "symptoms" in case
        assert "test_sequence" in case

def test_evaluate_single_case_all_models(test_db):
    case = BENCHMARK_CASES[0]
    
    res_a = evaluate_case_model_a(test_db, case)
    assert res_a["rank"] >= 1
    assert 0.0 <= res_a["reciprocal_rank"] <= 1.0
    
    res_b = evaluate_case_model_b(test_db, case)
    assert res_b["rank"] >= 1
    assert 0.0 <= res_b["reciprocal_rank"] <= 1.0
    assert res_b["brier_score"] >= 0.0
    assert res_b["entropy"] >= 0.0

    res_c = evaluate_case_model_c(test_db, case)
    assert res_c["rank"] >= 1
    assert 0.0 <= res_c["reciprocal_rank"] <= 1.0
    assert res_c["brier_score"] >= 0.0
    assert res_c["entropy"] >= 0.0
    assert res_c["tests_administered"] >= 0

def test_run_research_benchmark(test_db):
    results = run_research_benchmark(test_db)
    assert "model_a_baseline" in results
    assert "model_b_bayesian_ig" in results
    assert "model_c_sequential_cdss" in results
    assert "case_count" in results
    assert results["case_count"] == len(BENCHMARK_CASES)

    for key in ["model_a_baseline", "model_b_bayesian_ig", "model_c_sequential_cdss"]:
        metrics = results[key]
        assert 0.0 <= metrics.top_1_accuracy <= 1.0
        assert 0.0 <= metrics.top_3_accuracy <= 1.0
        assert 0.0 <= metrics.mean_reciprocal_rank <= 1.0
        assert 0.0 <= metrics.high_severity_recall <= 1.0

