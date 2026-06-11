import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel import SQLModel
from src.domain.entities.message_log import MessageLog
from src.infrastructure.persistence.sql_log_repository import SqlMessageLogRepository


@pytest.fixture
async def async_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    # Usamos SQLite em memória para testes rápidos sem depender de Postgres
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_log_repository_save_and_list(async_db_engine: AsyncEngine) -> None:
    # Arrange
    repo = SqlMessageLogRepository(async_db_engine)
    log1 = MessageLog(
        phone="5511999999999",
        direction="in",
        text="Gostaria de ver casas em Centro",
        step="PREFERENCES",
        intent="Locação",
    )
    log2 = MessageLog(
        phone="5511999999999",
        direction="out",
        text="Encontrei 3 casas para você!",
        step="SHOWING",
        intent="Locação",
    )
    # Log de outro telefone
    log_other = MessageLog(
        phone="5521888888888",
        direction="in",
        text="Oi",
        step="START",
    )

    # Act
    await repo.save(log1)
    await repo.save(log2)
    await repo.save(log_other)

    # Assert
    assert log1.id is not None
    assert log2.id is not None
    assert log_other.id is not None

    # Listar logs do primeiro telefone
    logs = await repo.list_by_phone("5511999999999")
    assert len(logs) == 2
    # Deve vir ordenado por created_at desc (log2 primeiro)
    assert logs[0].text == "Encontrei 3 casas para você!"
    assert logs[0].direction == "out"
    assert logs[0].step == "SHOWING"
    assert logs[0].intent == "Locação"

    assert logs[1].text == "Gostaria de ver casas em Centro"
    assert logs[1].direction == "in"
    assert logs[1].step == "PREFERENCES"

    # Listar logs do outro telefone
    other_logs = await repo.list_by_phone("5521888888888")
    assert len(other_logs) == 1
    assert other_logs[0].text == "Oi"
    assert other_logs[0].step == "START"
    assert other_logs[0].intent is None
