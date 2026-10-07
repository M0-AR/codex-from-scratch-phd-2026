"""Tiny shop tests: 600 cents with 10% coupon must be 540."""
from shop import total


def test_ten_percent_off_600():
    assert total(600, 10) == 540


def test_zero_coupon():
    assert total(600, 0) == 600


def test_full_coupon():
    assert total(600, 100) == 0
