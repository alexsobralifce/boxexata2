from typing import Any
import pytest
from unittest.mock import AsyncMock

from src.domain.entities.property_listing import PropertyListing
from src.domain.value_objects.money import Money
from src.infrastructure.cache.redis_cache import RedisCache


@pytest.mark.asyncio
async def test_redis_cache_set_and_get_raw() -> None:
    mock_redis = AsyncMock()
    storage: dict[str, bytes] = {}

    async def mock_set(key: str, value: Any, ex: Any = None) -> bool:
        storage[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    async def mock_get(key: str) -> Any:
        return storage.get(key)

    mock_redis.set.side_effect = mock_set
    mock_redis.get.side_effect = mock_get

    cache = RedisCache(mock_redis, default_ttl_seconds=600)

    # Testa dados simples
    await cache.set("simple_key", {"a": 1, "b": "hello"})
    res = await cache.get("simple_key")
    assert res == {"a": 1, "b": "hello"}
    mock_redis.set.assert_called_with(
        "simple_key", '{"__type__": "raw", "__data__": {"a": 1, "b": "hello"}}', ex=600
    )


@pytest.mark.asyncio
async def test_redis_cache_set_and_get_set() -> None:
    mock_redis = AsyncMock()
    storage: dict[str, bytes] = {}

    async def mock_set(key: str, value: Any, ex: Any = None) -> bool:
        storage[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    async def mock_get(key: str) -> Any:
        return storage.get(key)

    mock_redis.set.side_effect = mock_set
    mock_redis.get.side_effect = mock_get

    cache = RedisCache(mock_redis)

    # Testa objeto set
    await cache.set("my_set", {"id1", "id2"})
    res = await cache.get("my_set")
    assert res == {"id1", "id2"}


@pytest.mark.asyncio
async def test_redis_cache_set_and_get_property_listing() -> None:
    mock_redis = AsyncMock()
    storage: dict[str, bytes] = {}

    async def mock_set(key: str, value: Any, ex: Any = None) -> bool:
        storage[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    async def mock_get(key: str) -> Any:
        return storage.get(key)

    mock_redis.set.side_effect = mock_set
    mock_redis.get.side_effect = mock_get

    cache = RedisCache(mock_redis)

    listing = PropertyListing(
        property_id="123",
        ref="REF456",
        property_type="Casa",
        address="Rua X, 100",
        neighborhood="Centro",
        value=Money(1200.0),
        url="http://example.com/123",
        fees=Money(50.0),
        features=["2 quartos", "garagem"],
        photos=["http://example.com/photo.jpg"],
    )

    await cache.set("prop_123", listing)
    res = await cache.get("prop_123")

    assert isinstance(res, PropertyListing)
    assert res.id == "123"
    assert res.ref == "REF456"
    assert res.value.amount == 1200.0
    assert res.fees is not None
    assert res.fees.amount == 50.0
    assert res.features == ["2 quartos", "garagem"]
    assert res.photos == ["http://example.com/photo.jpg"]


@pytest.mark.asyncio
async def test_redis_cache_delete_and_clear() -> None:
    mock_redis = AsyncMock()
    cache = RedisCache(mock_redis)

    await cache.delete("key_to_delete")
    mock_redis.delete.assert_called_once_with("key_to_delete")

    await cache.clear()
    mock_redis.flushdb.assert_called_once()
