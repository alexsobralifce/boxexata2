from abc import ABC, abstractmethod
from src.domain.entities.session import Session


class ISessionStore(ABC):
    """Contrato abstrato para persistência e recuperação de sessões de chat."""

    @abstractmethod
    async def get_or_create(self, phone: str) -> Session:
        """Recupera a sessão existente do telefone ou cria uma nova se não existir."""
        pass

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Salva o estado atual da sessão no repositório."""
        pass
