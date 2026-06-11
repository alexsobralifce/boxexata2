import asyncio
from typing import Optional
from src.domain.entities.message_log import MessageLog
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_message_log_repository import IMessageLogRepository
from src.domain.repositories.i_session_store import ISessionStore
from src.shared.logger import logger


class MessageLogMiddleware(IMessageGateway):
    """Middleware que atua como decorador do IMessageGateway para interceptar e persistir

    mensagens de saída (enviadas pelo bot) e registrar logs de entrada.
    """

    def __init__(
        self,
        gateway: IMessageGateway,
        log_repo: IMessageLogRepository,
        session_store: Optional[ISessionStore] = None,
    ) -> None:
        self._gateway = gateway
        self._log_repo = log_repo
        self._session_store = session_store

    async def send_text(self, phone: str, text: str, typing_delay: float = 1.2) -> None:
        """Delega o envio de texto e inicia o log em segundo plano."""
        # Envia a mensagem pelo gateway real
        await self._gateway.send_text(phone, text, typing_delay)
        # Registra o log em segundo plano
        asyncio.create_task(self._log_outgoing(phone, text))

    async def send_image(self, phone: str, image_url: str, caption: str = "") -> None:
        """Delega o envio de imagem e inicia o log em segundo plano."""
        await self._gateway.send_image(phone, image_url, caption)
        log_text = f"[Imagem] Legenda: {caption}" if caption else f"[Imagem] URL: {image_url}"
        asyncio.create_task(self._log_outgoing(phone, log_text))

    async def send_typing(self, phone: str, duration_ms: int = 1500) -> None:
        """Delega a sinalização de digitação (sem registrar logs)."""
        await self._gateway.send_typing(phone, duration_ms)

    async def log_incoming(
        self, phone: str, text: str, step: str, intent: Optional[str] = None
    ) -> None:
        """Registra uma mensagem recebida em segundo plano."""
        asyncio.create_task(self._save_log(phone, "in", text, step, intent))

    async def _log_outgoing(self, phone: str, text: str) -> None:
        """Consulta o estado atual da sessão e salva o log da mensagem de saída."""
        step = "START"
        intent = None
        if self._session_store:
            try:
                session = await self._session_store.get_or_create(phone)
                if session:
                    step = session.step.name if hasattr(session.step, "name") else str(session.step)
                    intent = session.intent
            except Exception as e:
                logger.error("Erro ao ler sessão para log de saída", error=str(e), phone=phone)

        await self._save_log(phone, "out", text, step, intent)

    async def _save_log(
        self, phone: str, direction: str, text: str, step: str, intent: Optional[str] = None
    ) -> None:
        """Executa a gravação do log usando o repositório, capturando erros."""
        try:
            log = MessageLog(
                phone=phone,
                direction=direction,
                text=text,
                step=step,
                intent=intent,
            )
            await self._log_repo.save(log)
        except Exception as e:
            logger.error("Falha ao persistir log de mensagem no banco", error=str(e), phone=phone)
