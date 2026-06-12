import asyncio
from typing import Optional, Any, AsyncGenerator
from fastapi import FastAPI, Request, HTTPException, Query
from contextlib import asynccontextmanager
import os
from fastapi.staticfiles import StaticFiles
from src.shared.config import settings
from src.shared.logger import logger
from src.domain.entities.session import Session, ConversationStep
from tests.fakes.spy_message_gateway import SpyMessageGateway
from src.application.use_cases.handle_message import HandleMessageUseCase
from src.presentation.admin_router import router as admin_router

from src.shared.container import get_container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup:
    container = get_container()

    # Inicializa banco de dados se ativado (Fase 8A)
    db_engine = container.get("db_engine")
    if db_engine:
        from sqlmodel import SQLModel

        async with db_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

            # Auto-migration fallback for existing databases:
            # Ensure the is_available column exists in the properties table
            try:
                from sqlmodel import text

                if conn.dialect.name == "postgresql":
                    await conn.execute(
                        text(
                            "ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_available BOOLEAN NOT NULL DEFAULT TRUE"
                        )
                    )
                else:
                    try:
                        await conn.execute(
                            text(
                                "ALTER TABLE properties ADD COLUMN is_available BOOLEAN NOT NULL DEFAULT TRUE"
                            )
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error("Falha ao auto-migrar coluna is_available no startup", error=str(e))
        logger.info("Tabelas do banco de dados inicializadas com sucesso")

    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()

    notify_use_case = container["notify_new_listings"]
    scheduler.add_job(
        notify_use_case.execute,
        "interval",
        minutes=settings.notify_check_interval_minutes,
        id="notify_new_listings",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler iniciado com sucesso",
        interval_minutes=settings.notify_check_interval_minutes,
    )

    yield

    # Shutdown:
    scheduler.shutdown()
    logger.info("Scheduler finalizado com sucesso")

    if db_engine:
        await db_engine.dispose()
        logger.info("Pool de conexões do banco de dados finalizado com sucesso")


app = FastAPI(
    title="ExataBot API",
    description="Webhook e API de testes para o chatbot imobiliário da Exata Serviços",
    version="0.3.0",
    lifespan=lifespan,
)

# Inclui rotas administrativas protegidas por JWT (Fase 8C)
app.include_router(admin_router)

# Monta o diretório contendo o Dashboard administrativo na rota /admin
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/admin", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/health")
async def health() -> dict[str, Any]:
    """Retorna o status geral do bot e configurações básicas."""
    return {
        "status": "ok",
        "bot_name": settings.bot_name,
        "llm_provider": settings.llm_provider,
        "instance": settings.evolution_instance,
        "site_url": settings.site_base_url,
    }


@app.get("/test-scraping")
async def test_scraping(
    finalidade: str = "Locação", bairro: str = "", tipo: Optional[str] = None
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
    mensagem: str = Query(..., description="Texto da mensagem enviada pelo remetente"),
    instancia: Optional[str] = Query(
        None, description="Nome da instância do corretor para multi-tenant"
    ),
) -> dict[str, Any]:
    """Simula o envio de uma mensagem pelo usuário e captura as mensagens de resposta do bot."""
    container = get_container()

    # Usamos o SpyMessageGateway para interceptar e capturar o que a Ana responderia
    spy_gateway = SpyMessageGateway()

    # Criamos um orquestrador de teste temporário que usa o spy gateway
    test_use_case = HandleMessageUseCase(
        session_store=container["session_store"],
        property_repo=container["property_repo"],
        message_gateway=spy_gateway,
        extractor=container["extractor"],
        subscription_store=container["subscription_store"],
        log_repo=container["log_repo"],
    )

    profile = None
    if instancia:
        profile = await container["broker_repo"].get_by_instance(instancia)

    from src.shared.context import set_current_broker, current_broker

    token = set_current_broker(profile)

    try:
        # Ignora a verificação de horário para fins de teste manual local
        await test_use_case.execute(numero, mensagem, bypass_hours=True)

        return {
            "phone": numero,
            "sent_texts": [item["text"] for item in spy_gateway.sent_texts],
            "sent_images": [
                {"url": item["image_url"], "caption": item["caption"]}
                for item in spy_gateway.sent_images
            ],
        }
    except Exception as e:
        logger.error("Falha ao simular envio de mensagem", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        current_broker.reset(token)


async def _process_webhook_message(instance_id: str, phone: str, text: str) -> None:
    """Executa o processamento da mensagem com o contexto do broker correto."""
    cont = get_container()
    broker_repo = cont["broker_repo"]
    broker_profile = await broker_repo.get_by_instance(instance_id)

    from src.shared.context import set_current_broker, current_broker

    tok = set_current_broker(broker_profile)
    try:
        uc = cont["handle_message"]
        await uc.execute(phone, text)
    except Exception as ex:
        logger.error("Erro ao processar mensagem do webhook", error=str(ex), phone=phone)
    finally:
        current_broker.reset(tok)


@app.post("/webhook")
async def webhook(request: Request) -> dict[str, str]:
    """Recebe eventos da Evolution API v2."""
    if settings.evolution_api_key and request.headers.get("apikey") != settings.evolution_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    payload = await request.json()
    if payload.get("event") != "messages.upsert" or payload.get("data", {}).get("key", {}).get(
        "fromMe"
    ):
        return {"status": "ignored"}

    data = payload["data"]
    remote_jid = data["key"]["remoteJid"]
    if "@g.us" in remote_jid:
        return {"status": "ignored"}

    phone = remote_jid.split("@")[0]
    message = data.get("message", {})
    text = message.get("conversation") or message.get("extendedTextMessage", {}).get("text", "")

    if text:
        asyncio.create_task(
            _process_webhook_message(payload.get("instance", ""), phone, text.strip())
        )

    return {"status": "processing"}


@app.post("/webhook/zapi")
async def webhook_zapi(request: Request) -> dict[str, str]:
    """Recebe eventos da Z-API."""
    payload = await request.json()
    logger.info("Recebido webhook da Z-API", payload=payload)

    # Corrigido: Z-API structure para callbacks de recebimento reais
    phone = payload.get("phone", "")
    text_obj = payload.get("text", {})
    text = text_obj.get("message", "") if isinstance(text_obj, dict) else ""
    instance_id = payload.get("instanceId", "")

    if not phone or not text:
        logger.info("Ignorando webhook Z-API: telefone ou texto ausente", phone=phone, text=text)
        return {"status": "ignored"}

    asyncio.create_task(_process_webhook_message(instance_id, phone, text.strip()))
    return {"status": "processing"}
