from datetime import datetime, timezone
import json
from typing import Optional
from sqlmodel import Field, SQLModel
from src.domain.entities.message_log import MessageLog
from src.domain.entities.broker_profile import BrokerProfile
from src.domain.entities.property_listing import PropertyListing
from src.domain.value_objects.money import Money


class MessageLogs(SQLModel, table=True):
    """Modelo ORM SQLModel para persistência de logs de mensagens."""

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    phone: str = Field(index=True)
    direction: str
    text: str
    step: str
    intent: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(index=True)

    @classmethod
    def from_entity(cls, entity: MessageLog) -> "MessageLogs":
        """Cria um modelo ORM a partir da entidade de domínio."""
        created_at_naive = entity.created_at
        if created_at_naive and created_at_naive.tzinfo:
            created_at_naive = created_at_naive.replace(tzinfo=None)
        return cls(
            id=entity.id,
            phone=entity.phone,
            direction=entity.direction,
            text=entity.text,
            step=entity.step,
            intent=entity.intent,
            created_at=created_at_naive,
        )

    def to_entity(self) -> MessageLog:
        """Converte o modelo ORM para a entidade de domínio."""
        return MessageLog(
            log_id=self.id,
            phone=self.phone,
            direction=self.direction,
            text=self.text,
            step=self.step,
            intent=self.intent,
            created_at=self.created_at,
        )


class BrokerProfiles(SQLModel, table=True):
    """Modelo ORM SQLModel para persistência de perfis de corretores."""

    instance_id: str = Field(primary_key=True, index=True)
    broker_name: str
    phone_number: str
    site_base_url: str
    bot_name: str = Field(default="Ana")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(index=True)

    @classmethod
    def from_entity(cls, entity: BrokerProfile) -> "BrokerProfiles":
        """Cria um modelo ORM a partir da entidade de domínio."""
        created_at_naive = entity.created_at
        if created_at_naive and created_at_naive.tzinfo:
            created_at_naive = created_at_naive.replace(tzinfo=None)
        return cls(
            instance_id=entity.instance_id,
            broker_name=entity.broker_name,
            phone_number=entity.phone_number,
            site_base_url=entity.site_base_url,
            bot_name=entity.bot_name,
            is_active=entity.is_active,
            created_at=created_at_naive,
        )

    def to_entity(self) -> BrokerProfile:
        """Converte o modelo ORM para a entidade de domínio."""
        return BrokerProfile(
            instance_id=self.instance_id,
            broker_name=self.broker_name,
            phone_number=self.phone_number,
            site_base_url=self.site_base_url,
            bot_name=self.bot_name,
            is_active=self.is_active,
            created_at=self.created_at,
        )


class Properties(SQLModel, table=True):
    """Modelo ORM SQLModel para persistência de imóveis."""

    id: str = Field(primary_key=True, index=True)
    ref: str = Field(index=True)
    property_type: str
    address: str
    neighborhood: str
    value: float
    url: str
    fees: Optional[float] = Field(default=0.0, nullable=True)
    bedrooms: Optional[int] = Field(default=None, nullable=True)
    bathrooms: Optional[int] = Field(default=None, nullable=True)
    parking_spaces: Optional[int] = Field(default=None, nullable=True)
    description: Optional[str] = Field(default=None, nullable=True)
    photos: str = Field(default="[]")  # Armazenado como string JSON
    intent: Optional[str] = Field(default=None, nullable=True)
    is_available: bool = Field(default=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )

    @classmethod
    def from_entity(cls, entity: PropertyListing) -> "Properties":
        """Cria um modelo ORM a partir da entidade de domínio."""
        created_at_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        return cls(
            id=entity.id,
            ref=entity.ref,
            property_type=entity.property_type,
            address=entity.address,
            neighborhood=entity.neighborhood,
            value=entity.value.amount,
            url=entity.url,
            fees=entity.fees.amount if entity.fees else 0.0,
            bedrooms=entity.bedrooms,
            bathrooms=entity.bathrooms,
            parking_spaces=entity.parking_spaces,
            description=entity.description,
            photos=json.dumps(entity.photos or []),
            intent=entity.intent,
            is_available=entity.is_available,
            created_at=created_at_naive,
        )

    def to_entity(self) -> PropertyListing:
        """Converte o modelo ORM para a entidade de domínio."""
        try:
            photos_list = json.loads(self.photos)
        except Exception:
            photos_list = []
        return PropertyListing(
            property_id=self.id,
            ref=self.ref,
            property_type=self.property_type,
            address=self.address,
            neighborhood=self.neighborhood,
            value=Money(self.value),
            url=self.url,
            fees=Money(self.fees) if self.fees and self.fees > 0 else None,
            features=self.description.split("\n") if self.description else [],
            photos=photos_list,
            bedrooms=self.bedrooms,
            bathrooms=self.bathrooms,
            parking_spaces=self.parking_spaces,
            description=self.description,
            intent=self.intent,
            is_available=self.is_available,
        )
