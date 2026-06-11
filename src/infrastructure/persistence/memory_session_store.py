from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_session_store import ISessionStore


class MemorySessionStore(ISessionStore):
    """Implementação em memória para persistência de sessões de conversa (útil para desenvolvimento/testes)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def get_or_create(self, phone: str) -> Session:
        """Recupera ou cria uma nova sessão para o número fornecido."""
        if phone not in self._sessions:
            self._sessions[phone] = Session(phone=phone, step=ConversationStep.START)
        return self._sessions[phone]

    async def save(self, session: Session) -> None:
        """Salva a sessão em memória."""
        self._sessions[session.phone] = session
