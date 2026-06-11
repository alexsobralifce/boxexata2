from abc import ABC, abstractmethod
from typing import Any


class IPreferenceExtractor(ABC):
    """Interface abstrata para extração de preferências da conversa."""

    @abstractmethod
    async def extract(self, text: str, history: list[str]) -> dict[str, Any]:
        """Extrai preferências do cliente (nome, finalidade, tipo, bairro, valor_max) a partir do texto e histórico."""
        pass
