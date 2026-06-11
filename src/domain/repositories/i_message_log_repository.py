from abc import ABC, abstractmethod
from src.domain.entities.message_log import MessageLog


class IMessageLogRepository(ABC):
    """Interface abstrata para persistência de logs de mensagens."""

    @abstractmethod
    async def save(self, log: MessageLog) -> None:
        """Salva um log de mensagem."""
        pass

    @abstractmethod
    async def list_by_phone(self, phone: str, limit: int = 50) -> list[MessageLog]:
        """Lista os logs mais recentes de um telefone específico."""
        pass
