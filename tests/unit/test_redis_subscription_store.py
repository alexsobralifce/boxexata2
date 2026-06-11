from typing import Any
import pytest
from unittest.mock import AsyncMock

from src.domain.entities.subscription import Subscription
from src.infrastructure.persistence.redis_subscription_store import RedisSubscriptionStore


@pytest.mark.asyncio
async def test_redis_subscription_store_get_not_found() -> None:
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    store = RedisSubscriptionStore(mock_redis)
    sub = await store.get("5588999990000")

    assert sub is None
    mock_redis.get.assert_called_once_with("exatabot:subscription:5588999990000")


@pytest.mark.asyncio
async def test_redis_subscription_store_save_and_get() -> None:
    mock_redis = AsyncMock()
    storage: dict[str, bytes] = {}
    sets: dict[str, set[str]] = {}

    async def mock_set(key: str, value: Any, ex: Any = None) -> bool:
        storage[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    async def mock_get(key: str) -> Any:
        return storage.get(key)

    async def mock_delete(*keys: str) -> int:
        for k in keys:
            storage.pop(k, None)
            sets.pop(k, None)
        return len(keys)

    async def mock_keys(pattern: str) -> list[bytes]:
        return [k.encode("utf-8") for k in storage.keys() if k.startswith("exatabot:subscription:")]

    async def mock_sadd(key: str, *members: str) -> int:
        if key not in sets:
            sets[key] = set()
        count = 0
        for m in members:
            if m not in sets[key]:
                sets[key].add(m)
                count += 1
        return count

    async def mock_sismember(key: str, member: str) -> bool:
        return member in sets.get(key, set())

    mock_redis.set.side_effect = mock_set
    mock_redis.get.side_effect = mock_get
    mock_redis.delete.side_effect = mock_delete
    mock_redis.keys.side_effect = mock_keys
    mock_redis.sadd.side_effect = mock_sadd
    mock_redis.sismember.side_effect = mock_sismember

    store = RedisSubscriptionStore(mock_redis, ttl_notified_seconds=3600)

    original_sub = Subscription(
        phone="5588999990000",
        intent="Locação",
        property_type="Casa",
        neighborhood="Centro",
        max_value=1500.0,
    )

    await store.save(original_sub)

    mock_redis.set.assert_called_once()
    assert mock_redis.set.call_args[0][0] == "exatabot:subscription:5588999990000"

    # Recupera a assinatura
    retrieved = await store.get("5588999990000")
    assert retrieved is not None
    assert retrieved.phone == "5588999990000"
    assert retrieved.intent == "Locação"
    assert retrieved.property_type == "Casa"
    assert retrieved.neighborhood == "Centro"
    assert retrieved.max_value == 1500.0

    # Teste list_all
    all_subs = await store.list_all()
    assert len(all_subs) == 1
    assert all_subs[0].phone == "5588999990000"

    # Teste notificações
    assert await store.is_notified("5588999990000", "prop1") is False
    await store.mark_notified("5588999990000", "prop1")
    assert await store.is_notified("5588999990000", "prop1") is True
    mock_redis.sadd.assert_called_once_with("exatabot:notified:5588999990000", "prop1")
    mock_redis.expire.assert_called_once_with("exatabot:notified:5588999990000", 3600)

    # Teste delete
    await store.delete("5588999990000")
    assert await store.get("5588999990000") is None
