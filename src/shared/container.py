from typing import Any, Optional
from src.infrastructure.scraper.exata_property_repository import (
    ExataPropertyRepository,
    RateLimiter,
)
from src.infrastructure.whatsapp.evolution_gateway import EvolutionGateway
from src.infrastructure.whatsapp.zapi_gateway import ZApiGateway
from src.infrastructure.persistence.memory_session_store import MemorySessionStore
from src.infrastructure.cache.memory_cache import MemoryCache
from src.application.services.i_preference_extractor import IPreferenceExtractor
from src.application.services.regex_extractor import RegexPreferenceExtractor
from src.application.services.llm_extractor import LLMPreferenceExtractor
from src.application.use_cases.handle_message import HandleMessageUseCase
from src.shared.config import Settings
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_message_log_repository import IMessageLogRepository
from src.infrastructure.persistence.sql_log_repository import SqlMessageLogRepository
from src.infrastructure.persistence.null_log_repository import NullMessageLogRepository
from src.application.services.message_log_middleware import MessageLogMiddleware
from src.domain.repositories.i_broker_profile_repository import IBrokerProfileRepository
from src.infrastructure.persistence.sql_broker_profile_repository import SqlBrokerProfileRepository
from src.infrastructure.persistence.memory_broker_profile_repository import (
    MemoryBrokerProfileRepository,
)
from sqlalchemy.ext.asyncio import AsyncEngine


def create_container(settings: Settings) -> dict[str, Any]:
    """Dependency Injection Container - Factory que monta o grafo de dependências."""
    redis_client = None
    if (
        settings.cache_type == "redis"
        or settings.session_store_type == "redis"
        or settings.subscription_store_type == "redis"
    ):
        from redis.asyncio import Redis

        redis_client = Redis.from_url(settings.redis_url)

    # Inicializa Cache
    cache: Any
    if settings.cache_type == "redis":
        from src.infrastructure.cache.redis_cache import RedisCache

        assert redis_client is not None
        cache = RedisCache(redis_client, default_ttl_seconds=settings.cache_ttl_minutes * 60)
    else:
        cache = MemoryCache(default_ttl_seconds=settings.cache_ttl_minutes * 60)

    # Inicializa engine do banco de dados (se houver URL configurada)
    db_engine: Optional[AsyncEngine] = None
    if settings.database_url:
        from sqlalchemy.ext.asyncio import create_async_engine

        db_engine = create_async_engine(settings.database_url)

    rate_limiter = RateLimiter(min_delay_seconds=1.0)

    property_repo = ExataPropertyRepository(
        cache=cache,
        rate_limiter=rate_limiter,
        engine=db_engine,
    )

    # Seleciona o gateway de WhatsApp conforme a variável WHATSAPP_PROVIDER
    message_gateway: IMessageGateway
    if settings.whatsapp_provider == "zapi":
        message_gateway = ZApiGateway()
    else:
        message_gateway = EvolutionGateway()

    # Inicializa Session Store
    session_store: Any
    if settings.session_store_type == "redis":
        from src.infrastructure.persistence.redis_session_store import RedisSessionStore

        assert redis_client is not None
        session_store = RedisSessionStore(redis_client, ttl_seconds=86400)
    else:
        session_store = MemorySessionStore()

    # Inicializa Subscription Store
    subscription_store: Any
    if settings.subscription_store_type == "redis":
        from src.infrastructure.persistence.redis_subscription_store import RedisSubscriptionStore

        assert redis_client is not None
        subscription_store = RedisSubscriptionStore(redis_client, ttl_notified_seconds=604800)
    else:
        from src.infrastructure.persistence.memory_subscription_store import MemorySubscriptionStore

        subscription_store = MemorySubscriptionStore()

    extractor: IPreferenceExtractor
    if settings.llm_provider in ("openai", "deepseek"):
        extractor = LLMPreferenceExtractor()
    else:
        extractor = RegexPreferenceExtractor()

    # Inicializa persistência de logs (Fase 8A)
    log_repo: IMessageLogRepository

    if settings.message_log_enabled and db_engine:
        log_repo = SqlMessageLogRepository(db_engine)
        # Decorador do gateway para registrar logs de saída automaticamente
        message_gateway = MessageLogMiddleware(
            gateway=message_gateway,
            log_repo=log_repo,
            session_store=session_store,
        )
    else:
        log_repo = NullMessageLogRepository()

    # Inicializa repositório de perfis de corretores (Fase 8B)
    broker_repo: IBrokerProfileRepository
    if db_engine:
        broker_repo = SqlBrokerProfileRepository(db_engine)
    else:
        broker_repo = MemoryBrokerProfileRepository()

    use_case = HandleMessageUseCase(
        session_store=session_store,
        property_repo=property_repo,
        message_gateway=message_gateway,
        extractor=extractor,
        subscription_store=subscription_store,
        log_repo=log_repo,
    )

    from src.application.use_cases.notify_new_listings import NotifyNewListingsUseCase

    notify_use_case = NotifyNewListingsUseCase(
        property_repo=property_repo,
        message_gateway=message_gateway,
        subscription_store=subscription_store,
    )

    return {
        "redis_client": redis_client,
        "cache": cache,
        "property_repo": property_repo,
        "message_gateway": message_gateway,
        "session_store": session_store,
        "subscription_store": subscription_store,
        "extractor": extractor,
        "handle_message": use_case,
        "notify_new_listings": notify_use_case,
        "log_repo": log_repo,
        "db_engine": db_engine,
        "broker_repo": broker_repo,
    }


_container: Optional[dict[str, Any]] = None


def get_container() -> dict[str, Any]:
    """Retorna a instância global do container de injeção de dependências (singleton)."""
    global _container
    if _container is None:
        from src.shared.config import settings

        _container = create_container(settings)
    return _container
