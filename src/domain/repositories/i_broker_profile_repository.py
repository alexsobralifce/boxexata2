from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.broker_profile import BrokerProfile


class IBrokerProfileRepository(ABC):
    """Interface abstrata para persistência de perfis de corretores."""

    @abstractmethod
    async def save(self, profile: BrokerProfile) -> None:
        """Salva ou atualiza um perfil de corretor."""
        pass

    @abstractmethod
    async def get_by_instance(self, instance_id: str) -> Optional[BrokerProfile]:
        """Recupera um perfil de corretor pelo ID da instância do WhatsApp."""
        pass

    @abstractmethod
    async def delete(self, instance_id: str) -> None:
        """Exclui o perfil associado à instância do WhatsApp."""
        pass

    @abstractmethod
    async def list_all(self) -> list[BrokerProfile]:
        """Lista todos os perfis de corretores cadastrados."""
        pass
