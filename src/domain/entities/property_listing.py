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
        bedrooms: Optional[int] = None,
        bathrooms: Optional[int] = None,
        parking_spaces: Optional[int] = None,
        area_m2: Optional[float] = None,
        description: Optional[str] = None,
        intent: Optional[str] = None,
        is_available: bool = True,
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
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.parking_spaces = parking_spaces
        self.area_m2 = area_m2
        self.description = description
        self.intent = intent
        self.is_available = is_available

    def matches_preferences(
        self,
        intent: Optional[str] = None,
        property_type: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_value: Optional[float] = None,
        bedrooms: Optional[int] = None,
        bathrooms: Optional[int] = None,
        parking_spaces: Optional[int] = None,
        parking: Optional[bool] = None,
        pet_friendly: Optional[bool] = None,
    ) -> bool:
        """Verifica se o imóvel corresponde às preferências informadas."""
        # Filtra imóveis indisponíveis (vendidos ou alugados)
        if not self.is_available:
            return False

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
            if clean_type not in self.property_type.lower():
                return False

        # Filtra por finalidade (intent)
        if intent is not None and self.intent is not None:
            clean_intent = intent.strip().lower()
            if clean_intent not in self.intent.lower():
                return False

        # Filtra por quartos mínimos
        if bedrooms is not None and (self.bedrooms is None or self.bedrooms < bedrooms):
            return False

        # Filtra por banheiros mínimos
        if bathrooms is not None and (self.bathrooms is None or self.bathrooms < bathrooms):
            return False

        # Filtra por vagas de garagem mínimas
        if parking_spaces is not None and (self.parking_spaces is None or self.parking_spaces < parking_spaces):
            return False

        # Filtra por exigência de garagem (pelo menos 1 vaga)
        if parking is True and (self.parking_spaces is None or self.parking_spaces < 1):
            return False

        # Filtra por pet friendly (verifica nas features do imóvel)
        if pet_friendly is True:
            features_lower = " ".join(self.features).lower() if self.features else ""
            desc_lower = (self.description or "").lower()
            if "pet" not in features_lower and "pet" not in desc_lower:
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
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "parking_spaces": self.parking_spaces,
            "area_m2": self.area_m2,
            "description": self.description,
            "intent": self.intent,
            "is_available": self.is_available,
        }
