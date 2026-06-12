from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from src.application.services.auth_service import verify_password, create_access_token
from src.domain.entities.broker_profile import BrokerProfile
from src.presentation.security import get_current_admin
from src.shared.config import settings
from src.shared.logger import logger

# Importação lazy do container para obter os repositórios injetados
from src.shared.container import get_container

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Modelos Pydantic para validação de entrada/saída das requisições
class Token(BaseModel):
    access_token: str
    token_type: str


class BrokerProfileCreate(BaseModel):
    instance_id: str = Field(
        ..., min_length=2, description="ID único da instância do WhatsApp na Evolution API"
    )
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


class PropertySave(BaseModel):
    id: str = Field(..., description="ID/Código do imóvel")
    ref: str = Field(..., description="Referência do imóvel (ex: C763)")
    property_type: str = Field(..., description="Tipo do imóvel (ex: Casa)")
    address: str = Field(..., description="Endereço do imóvel")
    neighborhood: str = Field(..., description="Bairro do imóvel")
    value: float = Field(..., description="Valor")
    url: str = Field(..., description="URL")
    fees: Optional[float] = Field(default=0.0, description="Taxas / IPTU")
    bedrooms: Optional[int] = Field(default=None)
    bathrooms: Optional[int] = Field(default=None)
    parking_spaces: Optional[int] = Field(default=None)
    description: Optional[str] = Field(default=None)
    photos: list[str] = Field(default_factory=list)
    intent: Optional[str] = Field(default="Locação")
    is_available: bool = Field(default=True, description="Disponibilidade")


class ScrapeRequest(BaseModel):
    ref: str = Field(..., description="Código de referência do imóvel (ex: C763)")


@router.get("/properties", response_model=list[dict[str, Any]])
async def list_properties(
    property_type: Optional[str] = None,
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
    parking_spaces: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    neighborhood: Optional[str] = None,
    intent: Optional[str] = None,
    ref: Optional[str] = None,
    is_available: Optional[bool] = None,
    _: str = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    """Lista os imóveis armazenados no banco de dados com suporte a filtros avançados."""
    container = get_container()
    property_repo = container["property_repo"]

    # Se a tabela properties estiver totalmente vazia, realiza uma carga inicial de listagem básica
    # para povoar o banco e facilitar a vida do administrador
    from src.infrastructure.persistence.models import Properties
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlmodel import select

    if property_repo.engine:
        async with AsyncSession(property_repo.engine) as session:
            statement = select(Properties).limit(1)
            result = await session.execute(statement)
            if not result.scalars().first():
                # Dispara a busca geral para criar os registros iniciais no banco
                logger.info("Carga inicial de imóveis executada (banco de dados vazio)")
                await property_repo._scrape_all_basic_listings()
                # Salva as básicas no banco
                all_basics = await property_repo._scrape_all_basic_listings()
                from src.domain.entities.property_listing import PropertyListing
                from src.domain.value_objects.money import Money
                for pid, basic in all_basics.items():
                    listing = PropertyListing(
                        property_id=pid,
                        ref=basic["ref"],
                        property_type="Imóvel",
                        address=basic["address"],
                        neighborhood=basic["neighborhood"],
                        value=Money(basic["price"]),
                        url=basic["url"],
                        photos=[basic["cover_image"]] if basic["cover_image"] else [],
                        intent=basic["intent"]
                    )
                    await property_repo.save(listing)

    properties = await property_repo.list_stored_properties(
        property_type=property_type,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        parking_spaces=parking_spaces,
        min_price=min_price,
        max_price=max_price,
        neighborhood=neighborhood,
        intent=intent,
        ref=ref,
        is_available=is_available,
    )
    base = property_repo.site_base_url
    result = []
    for p in properties:
        d = p.to_dict()
        d["photos"] = [
            property_repo._absolutize_url(base, ph) for ph in (d.get("photos") or [])
        ]
        result.append(d)
    return result


@router.post("/properties/scrape", response_model=dict[str, Any])
async def scrape_property_by_ref(
    req: ScrapeRequest,
    _: str = Depends(get_current_admin),
) -> dict[str, Any]:
    """Executa o web scraper dinâmico para importar/atualizar um imóvel por referência."""
    container = get_container()
    property_repo = container["property_repo"]

    try:
        scraped = await property_repo.scrape_by_ref(req.ref)
        if not scraped:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imóvel com referência {req.ref} não encontrado no site Exata.",
            )
        base = property_repo.site_base_url
        d = scraped.to_dict()
        d["photos"] = [property_repo._absolutize_url(base, ph) for ph in (d.get("photos") or [])]
        return {"status": "success", "property": d}
    except Exception as e:
        logger.error("Falha ao raspar imóvel via admin API", ref=req.ref, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar scraper: {e}",
        )


@router.post("/properties/scrape-all", response_model=dict[str, Any])
async def scrape_all_properties(
    _: str = Depends(get_current_admin),
) -> dict[str, Any]:
    """Faz o scrape detalhado de todos os imóveis atualmente listados no site Exata Serviços."""
    container = get_container()
    property_repo = container["property_repo"]

    try:
        logger.info("Iniciando raspagem completa de todos os imóveis do site")
        basics = await property_repo._scrape_all_basic_listings()
        total_scraped = 0
        scraped_refs = []
        
        for pid, basic in basics.items():
            try:
                # Realiza scrape completo do detalhe e salva no banco
                url = f"{property_repo.site_base_url}/detalhe_imovel.php?codigo={pid}"
                html = await property_repo._fetch_html(url)
                listing = await property_repo._parse_detail_html(pid, html, basic)
                if listing:
                    await property_repo.save(listing)
                    total_scraped += 1
                    scraped_refs.append(listing.ref)
                    # Limpa cache do detalhe
                    cache_key = f"property_detail_{pid}"
                    await property_repo.cache.delete(cache_key)
            except Exception as ex:
                logger.error("Falha ao raspar detalhes do imóvel individual na carga total", pid=pid, error=str(ex))
                
        return {"status": "success", "total_scraped": total_scraped, "scraped_refs": scraped_refs}
    except Exception as e:
        logger.error("Erro geral na raspagem de todos os imóveis", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar raspagem geral: {e}",
        )


@router.put("/properties/{property_id}", response_model=dict[str, Any])
async def save_or_update_property(
    property_id: str,
    data: PropertySave,
    _: str = Depends(get_current_admin),
) -> dict[str, Any]:
    """Salva ou edita manualmente as informações estruturadas de um imóvel no banco."""
    container = get_container()
    property_repo = container["property_repo"]

    from src.domain.entities.property_listing import PropertyListing
    from src.domain.value_objects.money import Money

    listing = PropertyListing(
        property_id=property_id,
        ref=data.ref,
        property_type=data.property_type,
        address=data.address,
        neighborhood=data.neighborhood,
        value=Money(data.value),
        url=data.url,
        fees=Money(data.fees) if data.fees and data.fees > 0 else None,
        features=data.description.split("\n") if data.description else [],
        photos=data.photos,
        bedrooms=data.bedrooms,
        bathrooms=data.bathrooms,
        parking_spaces=data.parking_spaces,
        description=data.description,
        intent=data.intent,
        is_available=data.is_available,
    )

    await property_repo.save(listing)
    base = property_repo.site_base_url
    d = listing.to_dict()
    d["photos"] = [property_repo._absolutize_url(base, ph) for ph in (d.get("photos") or [])]
    return {"status": "success", "property": d}


@router.delete("/properties/{property_id}", response_model=dict[str, str])
async def delete_property(
    property_id: str,
    _: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Exclui o registro de um imóvel do banco de dados."""
    container = get_container()
    property_repo = container["property_repo"]

    await property_repo.delete(property_id)
    return {"status": "success", "message": f"Imóvel {property_id} removido."}
