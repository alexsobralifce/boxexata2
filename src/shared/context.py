from contextvars import ContextVar
from typing import Optional, Any
from src.domain.entities.broker_profile import BrokerProfile

# ContextVar global para armazenar o perfil do corretor ativo na corotina atual
current_broker: ContextVar[Optional[BrokerProfile]] = ContextVar("current_broker", default=None)


def get_current_broker() -> Optional[BrokerProfile]:
    """Retorna o perfil do corretor ativo no contexto assíncrono atual."""
    return current_broker.get()


def set_current_broker(profile: Optional[BrokerProfile]) -> Any:
    """Define o perfil do corretor para o contexto assíncrono atual e retorna o token de restauração."""
    return current_broker.set(profile)
