from typing import Any
import pytest
from unittest.mock import AsyncMock

from src.domain.entities.session import Session, ConversationStep
from src.infrastructure.persistence.redis_session_store import RedisSessionStore


@pytest.mark.asyncio
async def test_redis_session_store_get_not_found() -> None:
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    store = RedisSessionStore(mock_redis)
    session = await store.get_or_create("5588999990000")

    assert session.phone == "5588999990000"
    assert session.step == ConversationStep.START
    mock_redis.get.assert_called_once_with("exatabot:session:5588999990000")


@pytest.mark.asyncio
async def test_redis_session_store_save_and_get() -> None:
    mock_redis = AsyncMock()
    storage: dict[str, bytes] = {}

    async def mock_set(key: str, value: Any, ex: Any = None) -> bool:
        storage[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    async def mock_get(key: str) -> Any:
        return storage.get(key)

    mock_redis.set.side_effect = mock_set
    mock_redis.get.side_effect = mock_get

    store = RedisSessionStore(mock_redis, ttl_seconds=3600)

    original_session = Session(
        phone="5588999990000",
        step=ConversationStep.PREFERENCES,
        client_name="Maria",
        intent="Locação",
        neighborhood="Centro",
        max_value=1500.0,
        history=["oi", "tudo bem"],
    )

    await store.save(original_session)

    # Verifica se salvou a chave correta com expiração
    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args[0]
    call_kwargs = mock_redis.set.call_args[1]
    assert call_args[0] == "exatabot:session:5588999990000"
    assert call_kwargs["ex"] == 3600

    # Recupera a sessão
    retrieved = await store.get_or_create("5588999990000")
    assert retrieved.phone == "5588999990000"
    assert retrieved.step == ConversationStep.PREFERENCES
    assert retrieved.client_name == "Maria"
    assert retrieved.intent == "Locação"
    assert retrieved.neighborhood == "Centro"
    assert retrieved.max_value == 1500.0
    assert retrieved.history == ["oi", "tudo bem"]
