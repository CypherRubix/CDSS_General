import pytest
from decimal import Decimal

from app.models import Condition, ConditionTest, Test
from app.test_selection import calculate_entropy, select_and_rank_tests


def test_hand_calculated_information_gain_example():
    """
    Mathematically verifiable Information Gain calculation:
    2 candidate conditions: C1 and C2 with P(C1) = 0.5, P(C2) = 0.5.
    Initial Shannon Entropy:
    H(C) = - (0.5 * log2(0.5) + 0.5 * log2(0.5)) = 1.0 bit.

    Test 1 (High discriminatory power):
    P(T1=+ | C1) = 0.99, P(T1=+ | C2) = 0.01 (Specificity 0.99)
    P(T1=+) = 0.5 * 0.99 + 0.5 * 0.01 = 0.50
    Posterior entropy will be near 0.
    Expected Information Gain ~ 1.0 bit.

    Test 2 (Low discriminatory power):
    Equally unhelpful across both conditions.
    """
    c1 = Condition(condition_id=1, name="Condition 1")
    c2 = Condition(condition_id=2, name="Condition 2")

    t1 = Test(test_id=101, name="Discriminating Test", purpose="Distinguish C1 from C2")
    rel_t1 = ConditionTest(condition_id=1, test_id=101, test=t1, priority=1, sensitivity=Decimal("0.99"), specificity=Decimal("0.99"))
    c1.tests = [rel_t1]
    c2.tests = []

    candidates = [(c1, 0.5), (c2, 0.5)]
    ranked_tests = select_and_rank_tests(candidates, [t1])

    assert len(ranked_tests) == 1
    eval_t1 = ranked_tests[0]
    assert eval_t1.is_information_gain_calculated
    assert eval_t1.information_gain is not None
    # Information gain should be close to 1.0 bit
    assert eval_t1.information_gain > 0.85
    assert not eval_t1.missing_parameters


def test_completed_tests_are_excluded():
    """Tests already completed by the patient must be excluded from recommendations."""
    c1 = Condition(condition_id=1, name="Pneumonia")
    c2 = Condition(condition_id=2, name="Bronchitis")

    t_xray = Test(test_id=1, name="Chest X-Ray")
    t_cbc = Test(test_id=2, name="CBC")

    rel_xray = ConditionTest(condition_id=1, test_id=1, test=t_xray, priority=1, sensitivity=Decimal("0.85"))
    rel_cbc = ConditionTest(condition_id=1, test_id=2, test=t_cbc, priority=2, sensitivity=Decimal("0.75"))
    c1.tests = [rel_xray, rel_cbc]
    c2.tests = []

    candidates = [(c1, 0.7), (c2, 0.3)]

    # Patient has already completed Chest X-Ray
    ranked_tests = select_and_rank_tests(
        conditions_with_probabilities=candidates,
        all_tests=[t_xray, t_cbc],
        completed_test_names=["Chest X-Ray"],
    )

    names = [t.name for t in ranked_tests]
    assert "Chest X-Ray" not in names
    assert "CBC" in names


def test_missing_test_parameters_are_flagged_without_fabricated_ig():
    """Tests lacking sensitivity/specificity must be flagged transparently and not report uncalibrated IG as validated."""
    c1 = Condition(condition_id=1, name="Asthma")
    c2 = Condition(condition_id=2, name="COPD")

    t_uncalibrated = Test(test_id=1, name="Experimental Biomarker")
    rel = ConditionTest(condition_id=1, test_id=1, test=t_uncalibrated, priority=1, sensitivity=None, specificity=None)
    c1.tests = [rel]
    c2.tests = []

    ranked = select_and_rank_tests([(c1, 0.6), (c2, 0.4)], [t_uncalibrated])

    assert len(ranked) == 1
    assert ranked[0].missing_parameters
    assert not ranked[0].is_information_gain_calculated
    assert ranked[0].information_gain is None
    assert any("not calibrated" in lim for lim in ranked[0].limitations)

