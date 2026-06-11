from abc import ABC, abstractmethod


class IMessageGateway(ABC):
    """Contrato abstrato para envio de mensagens/mídias para o WhatsApp."""

    @abstractmethod
    async def send_text(self, phone: str, text: str, typing_delay: float = 1.2) -> None:
        """Envia uma mensagem de texto com indicador de digitação."""
        pass

    @abstractmethod
    async def send_image(self, phone: str, image_url: str, caption: str = "") -> None:
        """Envia uma imagem com uma legenda opcional."""
        pass

    @abstractmethod
    async def send_typing(self, phone: str, duration_ms: int = 1500) -> None:
        """Dispara o estado de digitando na conversa por um tempo determinado."""
        pass
