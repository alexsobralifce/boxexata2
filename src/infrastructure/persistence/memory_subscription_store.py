from typing import Optional
from src.domain.entities.subscription import Subscription
from src.domain.repositories.i_subscription_store import ISubscriptionStore


class MemorySubscriptionStore(ISubscriptionStore):
    """Implementação em memória para o armazenamento de assinaturas de alertas (útil para desenvolvimento e testes)."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}
        self._notified_properties: dict[str, set[str]] = {}

    async def save(self, subscription: Subscription) -> None:
        self._subscriptions[subscription.phone] = subscription

    async def get(self, phone: str) -> Optional[Subscription]:
        return self._subscriptions.get(phone)

    async def delete(self, phone: str) -> None:
        if phone in self._subscriptions:
            del self._subscriptions[phone]
        if phone in self._notified_properties:
            del self._notified_properties[phone]

    async def list_all(self) -> list[Subscription]:
        return list(self._subscriptions.values())

    async def is_notified(self, phone: str, property_id: str) -> bool:
        return property_id in self._notified_properties.get(phone, set())

    async def mark_notified(self, phone: str, property_id: str) -> None:
        if phone not in self._notified_properties:
            self._notified_properties[phone] = set()
        self._notified_properties[phone].add(property_id)
