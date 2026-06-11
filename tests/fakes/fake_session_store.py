from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_session_store import ISessionStore


class FakeSessionStore(ISessionStore):
    """Implementação fictícia (Fake) do repositório de sessões para testes unitários."""

    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    async def get_or_create(self, phone: str) -> Session:
        """Cria ou retorna uma sessão na memória do teste."""
        if phone not in self.sessions:
            self.sessions[phone] = Session(phone=phone, step=ConversationStep.START)
        return self.sessions[phone]

    async def save(self, session: Session) -> None:
        """Salva a sessão em memória."""
        self.sessions[session.phone] = session
