from typing import Any, Optional
from src.domain.value_objects.money import Money


class PropertyListing:
    """Entidade que representa o anúncio de um imóvel."""

    def __init__(
        self,
        property_id: str,
        ref: str,
        property_type: str,
        address: str,
        neighborhood: str,
        value: Money,
        url: str,
        fees: Optional[Money] = None,
        features: Optional[list[str]] = None,
        photos: Optional[list[str]] = None,
    ) -> None:
        self.id = property_id
        self.ref = ref
        self.property_type = property_type
        self.address = address
        self.neighborhood = neighborhood
        self.value = value
        self.url = url
        self.fees = fees
        self.features = features if features is not None else []
        self.photos = photos if photos is not None else []

    def matches_preferences(
        self,
        intent: Optional[str] = None,
        property_type: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_value: Optional[float] = None,
    ) -> bool:
        """Verifica se o imóvel corresponde às preferências informadas."""
        # Filtra por valor máximo se informado
        if max_value is not None and self.value.amount > max_value:
            return False

        # Filtra por bairro (case-insensitive substring match)
        if neighborhood is not None:
            clean_neigh = neighborhood.strip().lower()
            if clean_neigh not in self.neighborhood.lower():
                return False

        # Filtra por tipo (ex: casa, apartamento)
        if property_type is not None:
            clean_type = property_type.strip().lower()
            # O tipo do anúncio pode ser "Apartamento", "Casa residencial", etc.
            if clean_type not in self.property_type.lower():
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Converte a entidade para dicionário (facilitando serialização)."""
        return {
            "id": self.id,
            "ref": self.ref,
            "property_type": self.property_type,
            "address": self.address,
            "neighborhood": self.neighborhood,
            "value": self.value.amount,
            "url": self.url,
            "fees": self.fees.amount if self.fees else 0.0,
            "features": self.features,
            "photos": self.photos,
        }
