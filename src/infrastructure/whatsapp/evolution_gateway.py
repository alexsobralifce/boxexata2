import httpx

from src.domain.repositories.i_message_gateway import IMessageGateway
from src.shared.config import settings
from src.shared.logger import logger


class EvolutionGateway(IMessageGateway):
    """Implementação concreta do gateway de comunicação via Evolution API v2."""

    def __init__(self) -> None:
        self.base_url = settings.evolution_api_url.rstrip("/")
        self.instance = settings.evolution_instance
        self.headers = {
            "apikey": settings.evolution_api_key,
            "Content-Type": "application/json",
        }
        self.timeout_send_text = 10.0
        self.timeout_send_media = 15.0

    def _format_phone(self, phone: str) -> str:
        """Formata o número de telefone no padrão esperado pela Evolution API (DDI + DDD + Número)."""
        # Remove caracteres não numéricos
        clean_phone = "".join(filter(str.isdigit, phone))
        # Garante que não contenha sufixos como @s.whatsapp.net se vier cru
        return clean_phone

    async def send_text(self, phone: str, text: str, typing_delay: float = 1.2) -> None:
        """Envia uma mensagem de texto com indicador de digitação simulado via delay."""
        formatted_phone = self._format_phone(phone)
        delay_ms = int(typing_delay * 1000)

        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": formatted_phone,
            "text": text,
            "delay": delay_ms,
        }

        logger.info("Enviando mensagem de texto via WhatsApp", phone=formatted_phone, text_preview=text[:30])

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout_send_text) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Mensagem de texto enviada com sucesso", phone=formatted_phone)
        except Exception as e:
            logger.error("Falha ao enviar mensagem de texto via Evolution API", phone=formatted_phone, error=str(e))

    async def send_image(self, phone: str, image_url: str, caption: str = "") -> None:
        """Envia uma imagem com uma legenda opcional."""
        formatted_phone = self._format_phone(phone)
        url = f"{self.base_url}/message/sendMedia/{self.instance}"

        # Deduz mimetype simples a partir do final da URL
        mimetype = "image/jpeg"
        if image_url.lower().endswith(".png"):
            mimetype = "image/png"
        elif image_url.lower().endswith(".gif"):
            mimetype = "image/gif"

        payload = {
            "number": formatted_phone,
            "mediatype": "image",
            "mimetype": mimetype,
            "caption": caption,
            "media": image_url,
        }

        logger.info("Enviando imagem via WhatsApp", phone=formatted_phone, url=image_url)

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout_send_media) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Imagem enviada com sucesso", phone=formatted_phone)
        except Exception as e:
            logger.error("Falha ao enviar imagem via Evolution API", phone=formatted_phone, error=str(e))

    async def send_typing(self, phone: str, duration_ms: int = 1500) -> None:
        """Dispara o estado de digitando na conversa por um tempo determinado."""
        formatted_phone = self._format_phone(phone)
        url = f"{self.base_url}/chat/sendPresence/{self.instance}"

        payload = {
            "number": formatted_phone,
            "delay": duration_ms,
            "presence": "composing",
        }

        logger.info("Disparando estado de digitando (composing)", phone=formatted_phone, duration=duration_ms)

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout_send_text) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Estado de digitando enviado com sucesso", phone=formatted_phone)
        except Exception as e:
            logger.error("Falha ao enviar estado de digitando via Evolution API", phone=formatted_phone, error=str(e))
