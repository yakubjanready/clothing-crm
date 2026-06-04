"""services/order.py state machine pure testlari."""
from __future__ import annotations

import pytest

from app.models.order import OrderStatus
from app.services.order import (
    ALLOWED_TRANSITIONS,
    InvalidOrderTransitionError,
    assert_transition,
    generate_order_number,
)


def test_allowed_transitions_map_completeness() -> None:
    # Har bir status uchun yozuv bo'lishi kerak
    assert set(ALLOWED_TRANSITIONS) == set(OrderStatus)
    # Final holatlar — bo'sh
    assert ALLOWED_TRANSITIONS[OrderStatus.COMPLETED] == set()
    assert ALLOWED_TRANSITIONS[OrderStatus.CANCELLED] == set()


@pytest.mark.parametrize(
    "current,target",
    [
        (OrderStatus.DRAFT, OrderStatus.CONFIRMED),
        (OrderStatus.DRAFT, OrderStatus.CANCELLED),
        (OrderStatus.CONFIRMED, OrderStatus.PAID),
        (OrderStatus.CONFIRMED, OrderStatus.SHIPPED),
        (OrderStatus.CONFIRMED, OrderStatus.CANCELLED),
        (OrderStatus.PAID, OrderStatus.SHIPPED),
        (OrderStatus.PAID, OrderStatus.CANCELLED),
        (OrderStatus.SHIPPED, OrderStatus.COMPLETED),
        (OrderStatus.SHIPPED, OrderStatus.CANCELLED),
    ],
)
def test_valid_transitions_pass(current: OrderStatus, target: OrderStatus) -> None:
    assert_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [
        (OrderStatus.DRAFT, OrderStatus.PAID),
        (OrderStatus.DRAFT, OrderStatus.SHIPPED),
        (OrderStatus.PAID, OrderStatus.DRAFT),
        (OrderStatus.SHIPPED, OrderStatus.CONFIRMED),
        (OrderStatus.COMPLETED, OrderStatus.CANCELLED),
        (OrderStatus.COMPLETED, OrderStatus.SHIPPED),
        (OrderStatus.CANCELLED, OrderStatus.CONFIRMED),
        (OrderStatus.CANCELLED, OrderStatus.DRAFT),
    ],
)
def test_invalid_transitions_raise(current: OrderStatus, target: OrderStatus) -> None:
    with pytest.raises(InvalidOrderTransitionError):
        assert_transition(current, target)


def test_generate_order_number_format() -> None:
    n = generate_order_number()
    parts = n.split("-")
    assert parts[0] == "ORD"
    assert len(parts[1]) == 6 and parts[1].isdigit()  # YYYYMM
    assert len(parts[2]) == 6  # hex


def test_generate_invoice_and_return_prefixes() -> None:
    assert generate_order_number("INV").startswith("INV-")
    assert generate_order_number("RET").startswith("RET-")


def test_generate_order_number_unique_per_call() -> None:
    seen = {generate_order_number() for _ in range(100)}
    assert len(seen) == 100
