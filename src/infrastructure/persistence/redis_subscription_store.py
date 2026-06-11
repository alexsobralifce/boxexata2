import json
from typing import Optional
from redis.asyncio import Redis

from src.domain.entities.subscription import Subscription
from src.domain.repositories.i_subscription_store import ISubscriptionStore
from src.shared.logger import logger


class RedisSubscriptionStore(ISubscriptionStore):
    """Implementação assíncrona de persistência de assinaturas de alerta e rastreamento no Redis."""

    def __init__(self, redis_client: Redis, ttl_notified_seconds: int = 604800) -> None:
        self.client = redis_client
        self.ttl_notified = ttl_notified_seconds
        self.prefix_sub = "exatabot:subscription:"
        self.prefix_notified = "exatabot:notified:"

    def _get_sub_key(self, phone: str) -> str:
        return f"{self.prefix_sub}{phone}"

    def _get_notified_key(self, phone: str) -> str:
        return f"{self.prefix_notified}{phone}"

    async def save(self, subscription: Subscription) -> None:
        """Salva a assinatura de alertas do usuário no Redis."""
        key = self._get_sub_key(subscription.phone)
        try:
            data = {
                "phone": subscription.phone,
                "intent": subscription.intent,
                "property_type": subscription.property_type,
                "neighborhood": subscription.neighborhood,
                "max_value": subscription.max_value,
                "created_at": subscription.created_at,
            }
            serialized = json.dumps(data)
            await self.client.set(key, serialized)
        except Exception as e:
            logger.error(
                "Erro ao salvar assinatura no RedisSubscriptionStore",
                phone=subscription.phone,
                error=str(e),
            )

    async def get(self, phone: str) -> Optional[Subscription]:
        """Busca a assinatura ativa por número de telefone."""
        key = self._get_sub_key(phone)
        try:
            data_bytes = await self.client.get(key)
            if data_bytes:
                data = json.loads(
                    data_bytes.decode("utf-8") if isinstance(data_bytes, bytes) else data_bytes
                )
                return Subscription(
                    phone=data["phone"],
                    intent=data["intent"],
                    property_type=data["property_type"],
                    neighborhood=data["neighborhood"],
                    max_value=data.get("max_value"),
                    created_at=data.get("created_at"),
                )
        except Exception as e:
            logger.error(
                "Erro ao buscar assinatura no RedisSubscriptionStore",
                phone=phone,
                error=str(e),
            )
        return None

    async def delete(self, phone: str) -> None:
        """Exclui a assinatura de alertas associada ao telefone."""
        key_sub = self._get_sub_key(phone)
        key_notified = self._get_notified_key(phone)
        try:
            await self.client.delete(key_sub, key_notified)
        except Exception as e:
            logger.error(
                "Erro ao deletar assinatura no RedisSubscriptionStore",
                phone=phone,
                error=str(e),
            )

    async def list_all(self) -> list[Subscription]:
        """Lista todas as assinaturas registradas no Redis."""
        subscriptions = []
        try:
            pattern = f"{self.prefix_sub}*"
            keys = await self.client.keys(pattern)
            for key in keys:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                phone = key_str.replace(self.prefix_sub, "")
                sub = await self.get(phone)
                if sub:
                    subscriptions.append(sub)
        except Exception as e:
            logger.error("Erro ao listar assinaturas no RedisSubscriptionStore", error=str(e))
        return subscriptions

    async def is_notified(self, phone: str, property_id: str) -> bool:
        """Verifica se um determinado imóvel já foi enviado como alerta para o usuário."""
        key = self._get_notified_key(phone)
        try:
            return bool(await self.client.sismember(key, property_id))
        except Exception as e:
            logger.error(
                "Erro ao verificar notificação no RedisSubscriptionStore",
                phone=phone,
                property_id=property_id,
                error=str(e),
            )
        return False

    async def mark_notified(self, phone: str, property_id: str) -> None:
        """Registra que o imóvel foi notificado ao usuário com expiração programada."""
        key = self._get_notified_key(phone)
        try:
            await self.client.sadd(key, property_id)
            await self.client.expire(key, self.ttl_notified)
        except Exception as e:
            logger.error(
                "Erro ao marcar imóvel como notificado no RedisSubscriptionStore",
                phone=phone,
                property_id=property_id,
                error=str(e),
            )
