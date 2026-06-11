import asyncio
import httpx

from src.domain.repositories.i_message_gateway import IMessageGateway
from src.shared.config import settings
from src.shared.logger import logger


class ZApiGateway(IMessageGateway):
    """Implementação do gateway de comunicação via Z-API.

    A Z-API é uma plataforma SaaS (não auto-hospedada) com URL fixa:
        https://api.z-api.io/instances/{instance_id}/token/{token}/{endpoint}

    Autenticação dupla:
        - instance_id e token: identificam a "linha" WhatsApp (embutidos na URL)
        - Client-Token: header obrigatório para autenticação da conta Z-API
    """

    BASE_URL = "https://api.z-api.io"

    def __init__(self) -> None:
        self.instance_id = settings.zapi_instance_id
        self.token = settings.zapi_token
        self.client_token = settings.zapi_client_token
        self.headers = {
            "Content-Type": "application/json",
            "Client-Token": self.client_token,
        }
        self.timeout_send_text = 10.0
        self.timeout_send_media = 15.0

    def _instance_url(self, endpoint: str) -> str:
        """Monta a URL completa para um endpoint da instância."""
        return f"{self.BASE_URL}/instances/{self.instance_id}/token/{self.token}/{endpoint}"

    def _format_phone(self, phone: str) -> str:
        """Remove qualquer caractere não-numérico do número de telefone."""
        return "".join(filter(str.isdigit, phone))

    async def send_text(self, phone: str, text: str, typing_delay: float = 1.2) -> None:
        """Envia mensagem de texto com atraso simulado de digitação.

        A Z-API aceita `delayMessage` em segundos (inteiro, 1-15).
        O valor mínimo aceito é 1 segundo.
        """
        formatted_phone = self._format_phone(phone)
        delay_seconds = max(1, int(typing_delay))

        url = self._instance_url("send-text")
        payload = {
            "phone": formatted_phone,
            "message": text,
            "delayMessage": delay_seconds,
        }

        logger.info(
            "Enviando mensagem de texto via Z-API",
            phone=formatted_phone,
            text_preview=text[:40],
        )

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=self.timeout_send_text
            ) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info(
                    "Mensagem de texto enviada com sucesso via Z-API", phone=formatted_phone
                )
        except Exception as e:
            logger.error(
                "Falha ao enviar mensagem de texto via Z-API",
                phone=formatted_phone,
                error=str(e),
            )

    async def send_image(self, phone: str, image_url: str, caption: str = "") -> None:
        """Envia uma imagem por URL com legenda opcional.

        Endpoint Z-API: POST /send-image
        A imagem deve ser uma URL pública acessível pelo servidor da Z-API.
        """
        formatted_phone = self._format_phone(phone)
        url = self._instance_url("send-image")

        payload = {
            "phone": formatted_phone,
            "image": image_url,
            "caption": caption,
        }

        logger.info("Enviando imagem via Z-API", phone=formatted_phone, url=image_url)

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=self.timeout_send_media
            ) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Imagem enviada com sucesso via Z-API", phone=formatted_phone)
        except Exception as e:
            logger.error(
                "Falha ao enviar imagem via Z-API",
                phone=formatted_phone,
                error=str(e),
            )

    async def send_typing(self, phone: str, duration_ms: int = 1500) -> None:
        """Simula o estado de digitação via delay antes da próxima mensagem.

        A Z-API não possui um endpoint de "composing" dedicado como a Evolution API.
        Simulamos o comportamento com uma espera assíncrona local.
        A duração máxima útil é limitada a 5 segundos para não bloquear demais o fluxo.
        """
        wait_seconds = min(duration_ms / 1000, 5.0)
        logger.info(
            "Simulando digitação (sleep local) via Z-API",
            phone=phone,
            duration_seconds=wait_seconds,
        )
        await asyncio.sleep(wait_seconds)
