import asyncio
from typing import Optional, Any
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException, Query
from src.shared.config import settings
from src.shared.container import create_container
from src.shared.logger import logger
from src.domain.entities.session import Session, ConversationStep
from tests.fakes.spy_message_gateway import SpyMessageGateway
from src.application.use_cases.handle_message import HandleMessageUseCase

app = FastAPI(
    title="ExataBot API",
    description="Webhook e API de testes para o chatbot imobiliário da Exata Serviços",
    version="0.3.0",
)

_container = None


def get_container() -> dict:
    global _container
    if _container is None:
        _container = create_container(settings)
    return _container


@app.get("/health")
async def health() -> dict[str, Any]:
    """Retorna o status geral do bot e configurações básicas."""
    container = get_container()
    return {
        "status": "ok",
        "bot_name": settings.bot_name,
        "llm_provider": settings.llm_provider,
        "instance": settings.evolution_instance,
        "site_url": settings.site_base_url,
    }


@app.get("/test-scraping")
async def test_scraping(
    finalidade: str = "Locação",
    bairro: str = "",
    tipo: Optional[str] = None
) -> list[dict[str, Any]]:
    """Endpoint de debug para testar o scraping diretamente no site."""
    container = get_container()
    property_repo = container["property_repo"]

    fake_session = Session(
        phone="test_scraping",
        step=ConversationStep.PREFERENCES,
        intent=finalidade,
        neighborhood=bairro,
        property_type=tipo,
    )

    try:
        results = await property_repo.find_by_preferences(fake_session)
        return [r.to_dict() for r in results]
    except Exception as e:
        logger.error("Falha no teste de scraping", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro no scraping: {e}")


@app.post("/test-mensagem")
async def test_mensagem(
    numero: str = Query(..., description="Número do telefone do remetente"),
    mensagem: str = Query(..., description="Texto da mensagem enviada pelo remetente")
) -> dict[str, Any]:
    """Simula o envio de uma mensagem pelo usuário e captura as mensagens de resposta da Ana."""
    container = get_container()

    # Usamos o SpyMessageGateway para interceptar e capturar o que a Ana responderia
    spy_gateway = SpyMessageGateway()

    # Criamos um orquestrador de teste temporário que usa o spy gateway
    test_use_case = HandleMessageUseCase(
        session_store=container["session_store"],
        property_repo=container["property_repo"],
        message_gateway=spy_gateway,
        extractor=container["extractor"],
    )

    try:
        # Ignora a verificação de horário para fins de teste manual local
        await test_use_case.execute(numero, mensagem, bypass_hours=True)

        return {
            "phone": numero,
            "sent_texts": [item["text"] for item in spy_gateway.sent_texts],
            "sent_images": [
                {"url": item["image_url"], "caption": item["caption"]} for item in spy_gateway.sent_images
            ],
        }
    except Exception as e:
        logger.error("Falha ao simular envio de mensagem", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook")
async def webhook(request: Request) -> dict[str, str]:
    """Recebe eventos e mensagens enviados pela Evolution API v2."""
    # Valida apikey se fornecido nas configurações
    if settings.evolution_api_key:
        api_key_header = request.headers.get("apikey")
        if api_key_header != settings.evolution_api_key:
            logger.warning("Tentativa de acesso ao webhook com apikey inválido ou ausente")
            raise HTTPException(status_code=401, detail="Unauthorized api key")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event = payload.get("event")
    if event != "messages.upsert":
        return {"status": "ignored", "reason": f"Event '{event}' is not messages.upsert"}

    data = payload.get("data", {})
    key = data.get("key", {})
    from_me = key.get("fromMe", False)
    remote_jid = key.get("remoteJid", "")

    # Ignora mensagens enviadas pelo próprio bot
    if from_me:
        return {"status": "ignored", "reason": "Message is fromMe"}

    # Ignora mensagens de grupos
    if "@g.us" in remote_jid:
        return {"status": "ignored", "reason": "Message is from a group"}

    phone = remote_jid.split("@")[0]
    message = data.get("message", {})

    # Extrai o conteúdo de texto da mensagem dependendo do tipo
    text = ""
    if "conversation" in message:
        text = message["conversation"]
    elif "extendedTextMessage" in message:
        text = message["extendedTextMessage"].get("text", "")
    elif "buttonsResponseMessage" in message:
        btn_resp = message["buttonsResponseMessage"]
        text = btn_resp.get("selectedDisplayText", btn_resp.get("selectedButtonId", ""))
    elif "listResponseMessage" in message:
        list_resp = message["listResponseMessage"]
        text = list_resp.get("title", "")

    text = text.strip()
    if not text:
        return {"status": "ignored", "reason": "Empty message content or unsupported message type"}

    # Dispara o processamento em segundo plano para liberar o webhook da Evolution API imediatamente
    container = get_container()
    use_case = container["handle_message"]
    asyncio.create_task(use_case.execute(phone, text))

    return {"status": "processing"}
