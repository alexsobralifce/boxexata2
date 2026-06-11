import time
from typing import Any, Optional


class MemoryCache:
    """Implementação simples de cache em memória com suporte a TTL (Time-To-Live)."""

    def __init__(self, default_ttl_seconds: int = 1800) -> None:
        self.default_ttl = default_ttl_seconds
        self._cache: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Recupera um valor do cache se não estiver expirado."""
        if key not in self._cache:
            return None
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Armazena um valor no cache com um TTL opcional."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        """Remove um item do cache."""
        if key in self._cache:
            del self._cache[key]

    async def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()
