from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlmodel import select
from src.domain.entities.message_log import MessageLog
from src.domain.repositories.i_message_log_repository import IMessageLogRepository
from src.infrastructure.persistence.models import MessageLogs


class SqlMessageLogRepository(IMessageLogRepository):
    """Repositório assíncrono que persiste logs de mensagens no banco de dados usando SQLModel."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, log: MessageLog) -> None:
        """Salva um log de mensagem de forma assíncrona no banco."""
        model = MessageLogs.from_entity(log)
        async with AsyncSession(self._engine) as session:
            session.add(model)
            await session.commit()
            await session.refresh(model)
            log.id = model.id

    async def list_by_phone(self, phone: str, limit: int = 50) -> list[MessageLog]:
        """Lista os logs de mensagem mais recentes de um telefone específico."""
        async with AsyncSession(self._engine) as session:
            statement = (
                select(MessageLogs)
                .where(MessageLogs.phone == phone)
                .order_by(desc(MessageLogs.created_at))  # type: ignore[arg-type]
                .limit(limit)
            )
            result = await session.execute(statement)
            models = result.scalars().all()
            return [model.to_entity() for model in models]
