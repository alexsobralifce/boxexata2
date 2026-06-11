from abc import ABC, abstractmethod
from src.domain.entities.session import Session


class BaseHandler(ABC):
    """Classe base abstrata para os handlers de estado da conversa."""

    @abstractmethod
    async def handle(self, session: Session, text: str) -> bool:
        """Processa a mensagem recebida, envia respostas via gateway e retorna True se deve prosseguir para o próximo estado imediatamente."""
        pass
