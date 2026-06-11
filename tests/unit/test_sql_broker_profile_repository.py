import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel import SQLModel
from src.domain.entities.broker_profile import BrokerProfile
from src.infrastructure.persistence.sql_broker_profile_repository import SqlBrokerProfileRepository


@pytest.fixture
async def async_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    # Usamos SQLite em memória
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_broker_profile_crud(async_db_engine: AsyncEngine) -> None:
    # Arrange
    repo = SqlBrokerProfileRepository(async_db_engine)
    profile1 = BrokerProfile(
        instance_id="corretor_antonio",
        broker_name="Antônio Silva Corretor",
        phone_number="5511999999999",
        site_base_url="https://antonio.exataservicos.net",
        bot_name="Carol",
    )
    profile2 = BrokerProfile(
        instance_id="corretor_maria",
        broker_name="Maria Imóveis",
        phone_number="5511888888888",
        site_base_url="https://maria.exataservicos.net",
        bot_name="Mariana",
    )

    # Act - Inserção
    await repo.save(profile1)
    await repo.save(profile2)

    # Assert - Busca por instância
    retrieved1 = await repo.get_by_instance("corretor_antonio")
    assert retrieved1 is not None
    assert retrieved1.broker_name == "Antônio Silva Corretor"
    assert retrieved1.bot_name == "Carol"
    assert retrieved1.site_base_url == "https://antonio.exataservicos.net"

    retrieved2 = await repo.get_by_instance("corretor_maria")
    assert retrieved2 is not None
    assert retrieved2.broker_name == "Maria Imóveis"
    assert retrieved2.bot_name == "Mariana"

    # Act - Atualização (Save no existente)
    profile1.broker_name = "Antônio S. Corretor Atualizado"
    await repo.save(profile1)

    updated = await repo.get_by_instance("corretor_antonio")
    assert updated is not None
    assert updated.broker_name == "Antônio S. Corretor Atualizado"

    # Assert - Listar todos
    all_profiles = await repo.list_all()
    assert len(all_profiles) == 2

    # Act - Exclusão
    await repo.delete("corretor_maria")
    deleted = await repo.get_by_instance("corretor_maria")
    assert deleted is None

    assert len(await repo.list_all()) == 1
