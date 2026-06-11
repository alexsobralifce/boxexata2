from src.domain.entities.message_log import MessageLog
from src.domain.repositories.i_message_log_repository import IMessageLogRepository


class NullMessageLogRepository(IMessageLogRepository):
    """Implementação do padrão Null Object para o repositório de logs.

    Descarta gravações e retorna listas vazias para listagens.
    """

    async def save(self, log: MessageLog) -> None:
        """No-op: ignora o log e não faz nada."""
        pass

    async def list_by_phone(self, phone: str, limit: int = 50) -> list[MessageLog]:
        """No-op: retorna uma lista vazia de logs."""
        return []
