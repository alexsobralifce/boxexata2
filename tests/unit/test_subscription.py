import pytest
from src.domain.entities.subscription import Subscription
from src.domain.entities.property_listing import PropertyListing
from src.domain.value_objects.money import Money
from src.infrastructure.persistence.memory_subscription_store import MemorySubscriptionStore


def test_subscription_creation() -> None:
    sub = Subscription(
        phone="5588999990000",
        intent="Locação",
        property_type="Casa",
        neighborhood="Centro",
        max_value=1500.0,
    )
    assert sub.phone == "5588999990000"
    assert sub.intent == "Locação"
    assert sub.property_type == "Casa"
    assert sub.neighborhood == "Centro"
    assert sub.max_value == 1500.0
    assert sub.created_at is not None


def test_subscription_matches() -> None:
    sub = Subscription(
        phone="5588999990000",
        intent="Locação",
        property_type="Casa",
        neighborhood="Centro",
        max_value=1500.0,
    )

    p_match = PropertyListing(
        property_id="1",
        ref="REF1",
        property_type="Casa",
        address="Rua A, 10",
        neighborhood="Centro",
        value=Money(1200.0),
        url="http://site/1",
    )

    p_no_match_price = PropertyListing(
        property_id="2",
        ref="REF2",
        property_type="Casa",
        address="Rua B, 20",
        neighborhood="Centro",
        value=Money(1600.0),
        url="http://site/2",
    )

    p_no_match_neigh = PropertyListing(
        property_id="3",
        ref="REF3",
        property_type="Casa",
        address="Rua C, 30",
        neighborhood="Derby",
        value=Money(1000.0),
        url="http://site/3",
    )

    p_no_match_type = PropertyListing(
        property_id="4",
        ref="REF4",
        property_type="Apartamento",
        address="Rua D, 40",
        neighborhood="Centro",
        value=Money(1100.0),
        url="http://site/4",
    )

    assert sub.matches(p_match) is True
    assert sub.matches(p_no_match_price) is False
    assert sub.matches(p_no_match_neigh) is False
    assert sub.matches(p_no_match_type) is False


@pytest.mark.asyncio
async def test_memory_subscription_store() -> None:
    store = MemorySubscriptionStore()
    sub = Subscription(
        phone="5588999990000",
        intent="Locação",
        property_type="Casa",
        neighborhood="Centro",
        max_value=1500.0,
    )

    await store.save(sub)

    retrieved = await store.get("5588999990000")
    assert retrieved is not None
    assert retrieved.phone == "5588999990000"

    all_subs = await store.list_all()
    assert len(all_subs) == 1

    # Testa rastreamento de notificados
    assert await store.is_notified("5588999990000", "prop1") is False
    await store.mark_notified("5588999990000", "prop1")
    assert await store.is_notified("5588999990000", "prop1") is True

    await store.delete("5588999990000")
    assert await store.get("5588999990000") is None
