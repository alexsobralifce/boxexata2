from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from src.domain.entities.message_log import MessageLog
from src.domain.entities.broker_profile import BrokerProfile


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
        return cls(
            id=entity.id,
            phone=entity.phone,
            direction=entity.direction,
            text=entity.text,
            step=entity.step,
            intent=entity.intent,
            created_at=entity.created_at,
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
        return cls(
            instance_id=entity.instance_id,
            broker_name=entity.broker_name,
            phone_number=entity.phone_number,
            site_base_url=entity.site_base_url,
            bot_name=entity.bot_name,
            is_active=entity.is_active,
            created_at=entity.created_at,
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
