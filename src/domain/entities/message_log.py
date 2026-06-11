from datetime import datetime, timezone
from typing import Optional, Any


class MessageLog:
    """Entidade que representa o registro de uma mensagem enviada ou recebida pelo bot."""

    def __init__(
        self,
        phone: str,
        direction: str,
        text: str,
        step: str,
        intent: Optional[str] = None,
        created_at: Optional[datetime] = None,
        log_id: Optional[int] = None,
    ) -> None:
        self.id = log_id
        self.phone = phone
        self.direction = direction  # "in" ou "out"
        self.text = text
        self.step = step
        self.intent = intent
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Converte o log em dicionário para facilitar serialização e logging."""
        return {
            "id": self.id,
            "phone": self.phone,
            "direction": self.direction,
            "text": self.text,
            "step": self.step,
            "intent": self.intent,
            "created_at": self.created_at.isoformat(),
        }
