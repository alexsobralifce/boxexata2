from typing import Optional
from src.domain.entities.property_listing import PropertyListing
from src.domain.entities.session import Session
from src.domain.repositories.i_property_repository import IPropertyRepository


class FakePropertyRepository(IPropertyRepository):
    """Implementação fictícia (Fake) do repositório de imóveis para uso em testes unitários."""

    def __init__(self) -> None:
        self.properties: list[PropertyListing] = []

    def add_property(self, property_listing: PropertyListing) -> None:
        """Adiciona um imóvel fictício ao repositório."""
        self.properties.append(property_listing)

    async def find_by_preferences(self, session: Session) -> list[PropertyListing]:
        """Filtra os imóveis fictícios em memória seguindo a lógica das preferências da sessão."""
        results: list[PropertyListing] = []
        for prop in self.properties:
            # Filtro de finalidade (intent: Locação / Venda)
            if session.intent and session.intent.lower().strip() not in prop.property_type.lower() and session.intent.lower().strip() not in (prop.ref or "").lower():
                # Nota: A finalidade fictícia pode vir no ref ou tipo no mockup, vamos fazer correspondência genérica
                # ou verificar se o matching_preferences passa
                pass
            
            # Se matches_preferences do domínio retornar True, mantemos
            if prop.matches_preferences(
                intent=session.intent,
                property_type=session.property_type,
                neighborhood=session.neighborhood,
                max_value=session.max_value,
            ):
                results.append(prop)
        return results

    async def find_by_id(self, property_id: str) -> Optional[PropertyListing]:
        """Recupera o imóvel pelo ID em memória."""
        for prop in self.properties:
            if prop.id == property_id:
                return prop
        return None
