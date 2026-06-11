from typing import Optional
from src.domain.entities.broker_profile import BrokerProfile
from src.domain.repositories.i_broker_profile_repository import IBrokerProfileRepository


class MemoryBrokerProfileRepository(IBrokerProfileRepository):
    """Implementação em memória de IBrokerProfileRepository para testes e modo offline."""

    def __init__(self, initial_profiles: Optional[list[BrokerProfile]] = None) -> None:
        self._profiles: dict[str, BrokerProfile] = {}
        if initial_profiles:
            for p in initial_profiles:
                self._profiles[p.instance_id] = p

    async def save(self, profile: BrokerProfile) -> None:
        self._profiles[profile.instance_id] = profile

    async def get_by_instance(self, instance_id: str) -> Optional[BrokerProfile]:
        return self._profiles.get(instance_id)

    async def delete(self, instance_id: str) -> None:
        if instance_id in self._profiles:
            del self._profiles[instance_id]

    async def list_all(self) -> list[BrokerProfile]:
        return list(self._profiles.values())
