from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from src.application.services.auth_service import verify_password, create_access_token
from src.domain.entities.broker_profile import BrokerProfile
from src.presentation.security import get_current_admin
from src.shared.config import settings

# Importação lazy do container para obter os repositórios injetados
from src.shared.container import get_container

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Modelos Pydantic para validação de entrada/saída das requisições
class Token(BaseModel):
    access_token: str
    token_type: str


class BrokerProfileCreate(BaseModel):
    instance_id: str = Field(..., min_length=2, description="ID único da instância do WhatsApp na Evolution API")
    broker_name: str = Field(..., min_length=2, description="Nome do corretor ou imobiliária")
    phone_number: str = Field(..., description="Número de telefone do corretor")
    site_base_url: str = Field(..., description="URL base do site do corretor para scraping")
    bot_name: str = Field(default="Ana", description="Nome da atendente virtual")
    is_active: bool = Field(default=True, description="Status de ativação do corretor")


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    """Realiza o login administrativo verificando usuário e senha e retornando um token JWT."""
    username = form_data.username
    password = form_data.password

    # Validação do Usuário
    if username != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validação da Senha (com hash bcrypt)
    if not verify_password(password, settings.admin_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Gera token de acesso JWT
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/logs", response_model=list[dict[str, Any]])
async def list_logs(
    phone: Optional[str] = None,
    limit: int = 100,
    _: str = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    """Lista os logs de interações com o bot no banco de dados (ordenados por data)."""
    container = get_container()
    log_repo = container["log_repo"]

    if phone:
        logs = await log_repo.list_by_phone(phone, limit=limit)
    else:
        # Se não houver telefone, podemos listar registros gerais do banco.
        # No repositório de logs assíncrono definimos apenas list_by_phone.
        # Se quisermos listar todos de forma global, podemos buscar na tabela.
        # Como o repositório IMessageLogRepository exige apenas list_by_phone,
        # para visualização geral nós podemos consultar todas as linhas se for SqlMessageLogRepository.
        # Vamos verificar se o log_repo é do tipo SqlMessageLogRepository e tem acesso ao engine.
        from src.infrastructure.persistence.sql_log_repository import SqlMessageLogRepository
        if isinstance(log_repo, SqlMessageLogRepository):
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlmodel import select
            from sqlalchemy import desc
            from src.infrastructure.persistence.models import MessageLogs
            async with AsyncSession(log_repo._engine) as session:
                statement = select(MessageLogs).order_by(desc(MessageLogs.created_at)).limit(limit)  # type: ignore[arg-type]
                result = await session.execute(statement)
                models = result.scalars().all()
                return [m.to_entity().to_dict() for m in models]
        return []

    return [log.to_dict() for log in logs]


@router.get("/subscriptions", response_model=list[dict[str, Any]])
async def list_subscriptions(
    _: str = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    """Retorna todas as assinaturas proativas de alertas ativas."""
    container = get_container()
    store = container["subscription_store"]
    subs = await store.list_all()
    # Converte para dicionário
    return [
        {
            "phone": sub.phone,
            "intent": sub.intent,
            "property_type": sub.property_type,
            "neighborhood": sub.neighborhood,
            "max_value": sub.max_value,
        }
        for sub in subs
    ]


@router.delete("/subscriptions/{phone}")
async def delete_subscription(
    phone: str,
    _: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Cancela a assinatura de alerta ativo de um usuário."""
    container = get_container()
    store = container["subscription_store"]
    await store.delete(phone)
    return {"status": "success", "message": f"Assinatura do telefone {phone} removida."}


@router.get("/brokers", response_model=list[dict[str, Any]])
async def list_brokers(
    _: str = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    """Lista todos os perfis de corretores cadastrados."""
    container = get_container()
    broker_repo = container["broker_repo"]
    brokers = await broker_repo.list_all()
    return [b.to_dict() for b in brokers]


@router.post("/brokers", response_model=dict[str, Any])
async def save_broker(
    data: BrokerProfileCreate,
    _: str = Depends(get_current_admin),
) -> dict[str, Any]:
    """Cria ou atualiza um perfil de corretor no banco de dados."""
    container = get_container()
    broker_repo = container["broker_repo"]

    profile = BrokerProfile(
        instance_id=data.instance_id,
        broker_name=data.broker_name,
        phone_number=data.phone_number,
        site_base_url=data.site_base_url,
        bot_name=data.bot_name,
        is_active=data.is_active,
        created_at=datetime.now(timezone.utc),
    )

    await broker_repo.save(profile)
    return {"status": "success", "broker": profile.to_dict()}


@router.delete("/brokers/{instance_id}")
async def delete_broker(
    instance_id: str,
    _: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Exclui o perfil de um corretor do sistema."""
    container = get_container()
    broker_repo = container["broker_repo"]

    existing = await broker_repo.get_by_instance(instance_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de corretor não encontrado",
        )

    await broker_repo.delete(instance_id)
    return {"status": "success", "message": f"Corretor com instância {instance_id} excluído."}
