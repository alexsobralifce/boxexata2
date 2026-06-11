import pytest
from src.domain.value_objects.money import Money


def test_money_creation_success() -> None:
    money = Money(1500.0)
    assert money.amount == 1500.0


def test_money_negative_amount_raises_error() -> None:
    with pytest.raises(ValueError, match="Valor não pode ser negativo"):
        Money(-100.0)


def test_money_is_within() -> None:
    rent = Money(1500.0)
    max_budget = Money(2000.0)
    assert rent.is_within(max_budget) is True
    assert max_budget.is_within(rent) is False


def test_money_formatting() -> None:
    assert Money(1500.0).formatted() == "R$ 1.500,00"
    assert Money(800.5).formatted() == "R$ 800,50"
    assert Money(12500450.75).formatted() == "R$ 12.500.450,75"
