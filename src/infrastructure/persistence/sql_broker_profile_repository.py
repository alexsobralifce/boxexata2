from typing import Optional
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlmodel import select
from src.domain.entities.broker_profile import BrokerProfile
from src.domain.repositories.i_broker_profile_repository import IBrokerProfileRepository
from src.infrastructure.persistence.models import BrokerProfiles


class SqlBrokerProfileRepository(IBrokerProfileRepository):
    """Repositório assíncrono que persiste perfis de corretores no banco usando SQLModel."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, profile: BrokerProfile) -> None:
        """Salva ou atualiza um perfil de corretor no banco de dados."""
        model = BrokerProfiles.from_entity(profile)
        async with AsyncSession(self._engine) as session:
            # Como a chave primária é str (instance_id) informada pelo usuário,
            # precisamos verificar se ela já existe e fazer um merge
            existing = await session.get(BrokerProfiles, profile.instance_id)
            if existing:
                existing.broker_name = model.broker_name
                existing.phone_number = model.phone_number
                existing.site_base_url = model.site_base_url
                existing.bot_name = model.bot_name
                existing.is_active = model.is_active
                # Mantém o created_at original
                session.add(existing)
            else:
                session.add(model)
            await session.commit()

    async def get_by_instance(self, instance_id: str) -> Optional[BrokerProfile]:
        """Recupera um perfil de corretor pelo ID da instância."""
        async with AsyncSession(self._engine) as session:
            model = await session.get(BrokerProfiles, instance_id)
            if model:
                return model.to_entity()
            return None

    async def delete(self, instance_id: str) -> None:
        """Exclui o perfil associado à instância do WhatsApp."""
        async with AsyncSession(self._engine) as session:
            model = await session.get(BrokerProfiles, instance_id)
            if model:
                await session.delete(model)
                await session.commit()

    async def list_all(self) -> list[BrokerProfile]:
        """Lista todos os perfis de corretores cadastrados."""
        async with AsyncSession(self._engine) as session:
            statement = select(BrokerProfiles)
            result = await session.execute(statement)
            models = result.scalars().all()
            return [model.to_entity() for model in models]
