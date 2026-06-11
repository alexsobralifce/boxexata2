import json
from typing import Any, Optional
from redis.asyncio import Redis

from src.domain.entities.property_listing import PropertyListing
from src.domain.value_objects.money import Money
from src.shared.logger import logger


def _serialize_cache_value(value: Any) -> str:
    """Serializa dados complexos para armazenamento no Redis de forma segura (JSON)."""
    if isinstance(value, PropertyListing):
        return json.dumps({
            "__type__": "PropertyListing",
            "__data__": value.to_dict()
        })
    elif isinstance(value, set):
        return json.dumps({
            "__type__": "set",
            "__data__": list(value)
        })
    else:
        return json.dumps({
            "__type__": "raw",
            "__data__": value
        })


def _deserialize_cache_value(serialized: str) -> Any:
    """Deserializa dados lidos do Redis de volta para os tipos Python originais."""
    data = json.loads(serialized)
    if not isinstance(data, dict) or "__type__" not in data:
        return data

    t = data["__type__"]
    val = data["__data__"]

    if t == "PropertyListing":
        return PropertyListing(
            property_id=val["id"],
            ref=val["ref"],
            property_type=val["property_type"],
            address=val["address"],
            neighborhood=val["neighborhood"],
            value=Money(val["value"]),
            url=val["url"],
            fees=Money(val["fees"]) if val.get("fees") else None,
            features=val.get("features", []),
            photos=val.get("photos", [])
        )
    elif t == "set":
        return set(val)
    elif t == "raw":
        return val
    return data


class RedisCache:
    """Implementação distribuída do Cache utilizando o Redis com suporte a TTL."""

    def __init__(self, redis_client: Redis, default_ttl_seconds: int = 1800) -> None:
        self.client = redis_client
        self.default_ttl = default_ttl_seconds

    async def get(self, key: str) -> Optional[Any]:
        """Recupera e deserializa um valor do Redis."""
        try:
            serialized = await self.client.get(key)
            if serialized is None:
                return None
            return _deserialize_cache_value(serialized.decode("utf-8") if isinstance(serialized, bytes) else serialized)
        except Exception as e:
            logger.error("Erro ao obter chave do RedisCache", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Serializa e armazena um valor no Redis com TTL."""
        try:
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
            serialized = _serialize_cache_value(value)
            await self.client.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.error("Erro ao salvar chave no RedisCache", key=key, error=str(e))

    async def delete(self, key: str) -> None:
        """Remove uma chave do Redis."""
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.error("Erro ao remover chave do RedisCache", key=key, error=str(e))

    async def clear(self) -> None:
        """Limpa todas as chaves do Redis (namespace exatabot:cache:* se aplicável)."""
        try:
            # Para segurança, limpamos apenas chaves com padrão do exatabot se estivéssemos usando prefixo,
            # ou limpamos tudo com flushdb se o Redis for dedicado. Faremos flushdb por simplicidade de cache.
            await self.client.flushdb()
        except Exception as e:
            logger.error("Erro ao limpar RedisCache", error=str(e))
