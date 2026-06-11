import pytest
import asyncio
from typing import Optional
from src.domain.entities.message_log import MessageLog
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_log_repository import IMessageLogRepository
from src.domain.repositories.i_session_store import ISessionStore
from src.application.services.message_log_middleware import MessageLogMiddleware
from tests.fakes.spy_message_gateway import SpyMessageGateway


class FakeMessageLogRepository(IMessageLogRepository):
    def __init__(self, fail: bool = False) -> None:
        self.logs: list[MessageLog] = []
        self._fail = fail

    async def save(self, log: MessageLog) -> None:
        if self._fail:
            raise Exception("Database failure")
        self.logs.append(log)

    async def list_by_phone(self, phone: str, limit: int = 50) -> list[MessageLog]:
        return [log for log in self.logs if log.phone == phone][:limit]


class FakeSessionStore(ISessionStore):
    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    async def get(self, phone: str) -> Optional[Session]:
        return self._session

    async def get_or_create(self, phone: str) -> Session:
        return self._session or Session(phone)

    async def save(self, session: Session) -> None:
        self._session = session

    async def delete(self, phone: str) -> None:
        self._session = None


@pytest.mark.asyncio
async def test_middleware_delegates_and_logs_text() -> None:
    # Arrange
    spy_gateway = SpyMessageGateway()
    fake_repo = FakeMessageLogRepository()
    session = Session(phone="5511999999999", step=ConversationStep.PREFERENCES, intent="Locação")
    fake_store = FakeSessionStore(session)

    middleware = MessageLogMiddleware(
        gateway=spy_gateway,
        log_repo=fake_repo,
        session_store=fake_store,
    )

    # Act
    await middleware.send_text("5511999999999", "Olá, como posso ajudar?")
    # Damos um pequeno sleep para permitir que a task de segundo plano termine
    await asyncio.sleep(0.05)

    # Assert
    # 1. Verifica que a mensagem foi enviada pelo gateway real
    assert len(spy_gateway.sent_texts) == 1
    assert spy_gateway.sent_texts[0]["text"] == "Olá, como posso ajudar?"

    # 2. Verifica que o log foi persistido
    assert len(fake_repo.logs) == 1
    log = fake_repo.logs[0]
    assert log.phone == "5511999999999"
    assert log.direction == "out"
    assert log.text == "Olá, como posso ajudar?"
    assert log.step == "PREFERENCES"
    assert log.intent == "Locação"


@pytest.mark.asyncio
async def test_middleware_logs_image_with_caption() -> None:
    # Arrange
    spy_gateway = SpyMessageGateway()
    fake_repo = FakeMessageLogRepository()
    session = Session(phone="5511999999999", step=ConversationStep.SHOWING, intent="Venda")
    fake_store = FakeSessionStore(session)

    middleware = MessageLogMiddleware(
        gateway=spy_gateway,
        log_repo=fake_repo,
        session_store=fake_store,
    )

    # Act
    await middleware.send_image("5511999999999", "http://image.url", "Linda casa!")
    await asyncio.sleep(0.05)

    # Assert
    assert len(spy_gateway.sent_images) == 1
    assert spy_gateway.sent_images[0]["image_url"] == "http://image.url"
    assert spy_gateway.sent_images[0]["caption"] == "Linda casa!"

    assert len(fake_repo.logs) == 1
    log = fake_repo.logs[0]
    assert log.direction == "out"
    assert log.text == "[Imagem] Legenda: Linda casa!"
    assert log.step == "SHOWING"
    assert log.intent == "Venda"


@pytest.mark.asyncio
async def test_middleware_failure_does_not_propagate() -> None:
    # Arrange
    spy_gateway = SpyMessageGateway()
    # Criamos um repo que falha ao salvar no banco
    failing_repo = FakeMessageLogRepository(fail=True)
    session = Session(phone="5511999999999", step=ConversationStep.START)
    fake_store = FakeSessionStore(session)

    middleware = MessageLogMiddleware(
        gateway=spy_gateway,
        log_repo=failing_repo,
        session_store=fake_store,
    )

    # Act & Assert
    # A chamada de send_text não deve lançar exceção mesmo se a gravação de logs falhar
    try:
        await middleware.send_text("5511999999999", "Oi")
        await asyncio.sleep(0.05)
    except Exception as e:
        pytest.fail(f"O middleware deveria capturar o erro do banco, mas lançou: {e}")

    # A mensagem deve ter sido enviada de qualquer forma
    assert len(spy_gateway.sent_texts) == 1
