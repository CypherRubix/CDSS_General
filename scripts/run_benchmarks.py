#!/usr/bin/env python3
"""
Research Benchmark Runner for Clinical Decision Support System.
Compares Model A (Baseline Weighted Scoring), Model B (Bayesian + Info Gain),
and Model C (Sequential Uncertainty & Severity-Aware CDSS).
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.database import SessionLocal, init_db
from app.research_evaluation import run_research_benchmark
from app.services import seed_initial_clinical_data


def main():
    print("=" * 80)
    print("   CLINICAL DECISION SUPPORT SYSTEM: REPRODUCIBLE RESEARCH BENCHMARK")
    print("=" * 80)

    init_db()
    with SessionLocal() as db:
        seed_initial_clinical_data(db)
        print("\nRunning comparative evaluation across standard clinical benchmark cases...\n")
        benchmark_res = run_research_benchmark(db)

    print("-" * 80)
    print(f"Benchmark Cases Evaluated: {benchmark_res.benchmark_cases_count}")
    print("-" * 80)
    print(f"{'Metric':<35} | {'Model A (Baseline)':<18} | {'Model B (Bayesian)':<18} | {'Model C (Proposed)':<18}")
    print("-" * 80)

    mA = benchmark_res.models_evaluated[0]
    mB = benchmark_res.models_evaluated[1]
    mC = benchmark_res.models_evaluated[2]

    metrics_list = [
        ("Top-1 Diagnostic Accuracy", f"{mA.top1_accuracy:.1%}", f"{mB.top1_accuracy:.1%}", f"{mC.top1_accuracy:.1%}"),
        ("Top-3 Diagnostic Accuracy", f"{mA.top3_accuracy:.1%}", f"{mB.top3_accuracy:.1%}", f"{mC.top3_accuracy:.1%}"),
        ("Mean Reciprocal Rank (MRR)", f"{mA.mean_reciprocal_rank:.4f}", f"{mB.mean_reciprocal_rank:.4f}", f"{mC.mean_reciprocal_rank:.4f}"),
        ("Brier Score (Lower is better)", f"{mA.brier_score:.4f}", f"{mB.brier_score:.4f}", f"{mC.brier_score:.4f}"),
        ("High-Severity Condition Recall", f"{mA.high_severity_recall:.1%}", f"{mB.high_severity_recall:.1%}", f"{mC.high_severity_recall:.1%}"),
        ("Average Residual Entropy (bits)", f"{mA.average_residual_entropy:.2f}", f"{mB.average_residual_entropy:.2f}", f"{mC.average_residual_entropy:.2f}"),
        ("Average Recommended Tests", f"{mA.average_tests_recommended:.1f}", f"{mB.average_tests_recommended:.1f}", f"{mC.average_tests_recommended:.1f}"),
        ("Missing Data Resilience Score", f"{mA.missing_data_resilience_score:.1f}", f"{mB.missing_data_resilience_score:.1f}", f"{mC.missing_data_resilience_score:.1f}"),
    ]

    for label, vA, vB, vC in metrics_list:
        print(f"{label:<35} | {vA:<18} | {vB:<18} | {vC:<18}")

    print("-" * 80)
    print("\nSummary Rationale:")
    print(benchmark_res.comparative_summary)
    print("\nScientific Disclaimer:")
    print(benchmark_res.evaluation_disclaimer)
    print("=" * 80)


if __name__ == "__main__":
    main()

