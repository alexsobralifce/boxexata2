from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.subscription import Subscription


class ISubscriptionStore(ABC):
    """Interface abstrata para persistência de assinaturas de alerta e rastreamento de notificações."""

    @abstractmethod
    async def save(self, subscription: Subscription) -> None:
        """Salva ou atualiza a assinatura do usuário."""
        pass

    @abstractmethod
    async def get(self, phone: str) -> Optional[Subscription]:
        """Busca a assinatura ativa por número de telefone."""
        pass

    @abstractmethod
    async def delete(self, phone: str) -> None:
        """Exclui a assinatura de alertas associada ao telefone."""
        pass

    @abstractmethod
    async def list_all(self) -> list[Subscription]:
        """Lista todas as assinaturas registradas no sistema."""
        pass

    @abstractmethod
    async def is_notified(self, phone: str, property_id: str) -> bool:
        """Verifica se um determinado imóvel já foi enviado como alerta para o usuário."""
        pass

    @abstractmethod
    async def mark_notified(self, phone: str, property_id: str) -> None:
        """Registra que o imóvel foi notificado ao usuário para evitar duplicidade de mensagens."""
        pass
