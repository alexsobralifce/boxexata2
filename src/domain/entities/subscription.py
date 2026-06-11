import time
from typing import Optional
from src.domain.entities.property_listing import PropertyListing


class Subscription:
    """Entidade que representa uma assinatura de alerta de novos imóveis por usuário."""

    def __init__(
        self,
        phone: str,
        intent: str,
        property_type: str,
        neighborhood: str,
        max_value: Optional[float] = None,
        created_at: Optional[float] = None,
    ) -> None:
        self.phone = phone
        self.intent = intent
        self.property_type = property_type
        self.neighborhood = neighborhood
        self.max_value = max_value
        self.created_at = created_at if created_at is not None else time.time()

    def matches(self, listing: PropertyListing) -> bool:
        """Verifica se o anúncio do imóvel corresponde aos critérios desta assinatura."""
        # Filtra por valor máximo se informado
        if self.max_value is not None and listing.value.amount > self.max_value:
            return False

        # Filtra por bairro (case-insensitive substring match)
        if self.neighborhood.strip().lower() not in listing.neighborhood.lower():
            return False

        # Filtra por tipo (ex: casa, apartamento)
        if self.property_type.strip().lower() not in listing.property_type.lower():
            return False

        return True
