from typing import Any
from src.domain.repositories.i_message_gateway import IMessageGateway


class SpyMessageGateway(IMessageGateway):
    """Implementação espiã (Spy) do gateway de mensagens para verificar chamadas em testes unitários."""

    def __init__(self) -> None:
        self.sent_texts: list[dict[str, Any]] = []
        self.sent_images: list[dict[str, Any]] = []
        self.sent_typings: list[dict[str, Any]] = []

    async def send_text(self, phone: str, text: str, typing_delay: float = 1.2) -> None:
        """Registra o envio de uma mensagem de texto."""
        self.sent_texts.append(
            {
                "phone": phone,
                "text": text,
                "typing_delay": typing_delay,
            }
        )

    async def send_image(self, phone: str, image_url: str, caption: str = "") -> None:
        """Registra o envio de uma imagem."""
        self.sent_images.append(
            {
                "phone": phone,
                "image_url": image_url,
                "caption": caption,
            }
        )

    async def send_typing(self, phone: str, duration_ms: int = 1500) -> None:
        """Registra o disparo do indicador de digitação."""
        self.sent_typings.append(
            {
                "phone": phone,
                "duration_ms": duration_ms,
            }
        )

    def reset(self) -> None:
        """Limpa todos os registros de mensagens enviadas."""
        self.sent_texts.clear()
        self.sent_images.clear()
        self.sent_typings.clear()
