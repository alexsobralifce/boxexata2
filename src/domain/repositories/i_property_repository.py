from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.property_listing import PropertyListing
from src.domain.entities.session import Session


class IPropertyRepository(ABC):
    """Contrato abstrato para a busca e recuperação de imóveis."""

    @abstractmethod
    async def find_by_preferences(self, session: Session) -> list[PropertyListing]:
        """Busca imóveis com base nas preferências registradas na sessão."""
        pass

    @abstractmethod
    async def find_by_id(self, property_id: str) -> Optional[PropertyListing]:
        """Busca informações detalhadas de um imóvel pelo seu ID."""
        pass
