from src.sums import sum_to


def test_sum_to_three():
    assert sum_to(3) == 6


def test_sum_to_one():
    assert sum_to(1) == 1


def test_sum_to_zero():
    assert sum_to(0) == 0
