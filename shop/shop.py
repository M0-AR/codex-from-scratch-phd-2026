"""Tiny shop — integer cents, coupon percent off. Contains the planted bug."""
from __future__ import annotations


def total(subtotal_cents: int, coupon_percent: int) -> int:
    """Return total after coupon. BUG: subtracts coupon number itself."""
    discount = coupon_percent
    return subtotal_cents - discount


def format_cents(cents: int) -> str:
    dollars, rest = divmod(cents, 100)
    return f"${dollars}.{rest:02d}"
