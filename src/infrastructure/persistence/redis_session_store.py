import json
from redis.asyncio import Redis

from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_session_store import ISessionStore
from src.shared.logger import logger


class RedisSessionStore(ISessionStore):
    """Implementação assíncrona de persistência de sessões no Redis com expiração configurável."""

    def __init__(self, redis_client: Redis, ttl_seconds: int = 86400) -> None:
        self.client = redis_client
        self.ttl = ttl_seconds
        self.prefix = "exatabot:session:"

    def _get_key(self, phone: str) -> str:
        return f"{self.prefix}{phone}"

    async def get_or_create(self, phone: str) -> Session:
        """Recupera ou cria uma nova sessão de conversa para o telefone fornecido."""
        key = self._get_key(phone)
        try:
            data_bytes = await self.client.get(key)
            if data_bytes:
                data = json.loads(
                    data_bytes.decode("utf-8") if isinstance(data_bytes, bytes) else data_bytes
                )
                return Session(
                    phone=data["phone"],
                    step=ConversationStep[data["step"]],
                    client_name=data.get("client_name"),
                    intent=data.get("intent"),
                    property_type=data.get("property_type"),
                    neighborhood=data.get("neighborhood"),
                    max_value=data.get("max_value"),
                    results=data.get("results"),
                    result_offset=data.get("result_offset", 0),
                    message_count=data.get("message_count", 0),
                    selected_property_id=data.get("selected_property_id"),
                    history=data.get("history"),
                )
        except Exception as e:
            logger.error("Erro ao buscar sessão no RedisSessionStore", phone=phone, error=str(e))

        return Session(phone=phone, step=ConversationStep.START)

    async def save(self, session: Session) -> None:
        """Salva a sessão de conversa no Redis definindo tempo limite (TTL)."""
        key = self._get_key(session.phone)
        try:
            data = {
                "phone": session.phone,
                "step": session.step.name,
                "client_name": session.client_name,
                "intent": session.intent,
                "property_type": session.property_type,
                "neighborhood": session.neighborhood,
                "max_value": session.max_value,
                "results": session.results,
                "result_offset": session.result_offset,
                "message_count": session.message_count,
                "selected_property_id": session.selected_property_id,
                "history": session.history,
            }
            serialized = json.dumps(data)
            await self.client.set(key, serialized, ex=self.ttl)
        except Exception as e:
            logger.error(
                "Erro ao salvar sessão no RedisSessionStore", phone=session.phone, error=str(e)
            )
