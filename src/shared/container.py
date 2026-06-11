from src.infrastructure.scraper.exata_property_repository import ExataPropertyRepository, RateLimiter
from src.infrastructure.whatsapp.evolution_gateway import EvolutionGateway
from src.infrastructure.persistence.memory_session_store import MemorySessionStore
from src.infrastructure.cache.memory_cache import MemoryCache
from src.application.services.regex_extractor import RegexPreferenceExtractor
from src.application.services.llm_extractor import LLMPreferenceExtractor
from src.application.use_cases.handle_message import HandleMessageUseCase
from src.shared.config import Settings


def create_container(settings: Settings) -> dict:
    """Dependency Injection Container - Factory que monta o grafo de dependências."""
    cache = MemoryCache(default_ttl_seconds=settings.cache_ttl_minutes * 60)
    rate_limiter = RateLimiter(min_delay_seconds=1.0)

    property_repo = ExataPropertyRepository(
        cache=cache,
        rate_limiter=rate_limiter,
    )

    message_gateway = EvolutionGateway()
    session_store = MemorySessionStore()

    if settings.llm_provider in ("openai", "deepseek"):
        extractor = LLMPreferenceExtractor()
    else:
        extractor = RegexPreferenceExtractor()

    use_case = HandleMessageUseCase(
        session_store=session_store,
        property_repo=property_repo,
        message_gateway=message_gateway,
        extractor=extractor,
    )

    return {
        "cache": cache,
        "property_repo": property_repo,
        "message_gateway": message_gateway,
        "session_store": session_store,
        "extractor": extractor,
        "handle_message": use_case,
    }
