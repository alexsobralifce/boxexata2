from datetime import datetime, timezone
from typing import Optional, Any


class BrokerProfile:
    """Entidade que representa o perfil de um corretor / inquilino (tenant) no ExataBot."""

    def __init__(
        self,
        instance_id: str,
        broker_name: str,
        phone_number: str,
        site_base_url: str,
        bot_name: str = "Ana",
        is_active: bool = True,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.instance_id = instance_id
        self.broker_name = broker_name
        self.phone_number = phone_number
        self.site_base_url = site_base_url
        self.bot_name = bot_name
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Converte a entidade para dicionário."""
        return {
            "instance_id": self.instance_id,
            "broker_name": self.broker_name,
            "phone_number": self.phone_number,
            "site_base_url": self.site_base_url,
            "bot_name": self.bot_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
