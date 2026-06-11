import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel import SQLModel
from src.domain.entities.message_log import MessageLog
from src.infrastructure.persistence.sql_broker_profile_repository import SqlBrokerProfileRepository
from src.infrastructure.persistence.sql_log_repository import SqlMessageLogRepository
from src.presentation.webhook import app
from src.shared.container import get_container
from src.shared.config import settings
from src.application.services.auth_service import get_password_hash


@pytest.fixture
async def setup_test_db() -> AsyncGenerator[AsyncEngine, None]:
    # Usamos SQLite em memória para os testes de API
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Injeta os repositórios reais de teste no container da aplicação global do webhook
    container = get_container()
    container["log_repo"] = SqlMessageLogRepository(engine)
    container["broker_repo"] = SqlBrokerProfileRepository(engine)

    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_login_success_and_failure(setup_test_db: AsyncEngine) -> None:
    # Arrange
    # Configura um hash conhecido para teste em settings temporariamente
    # Hash correspondente à senha "senha_admin"
    settings.admin_username = "admin_de_teste"
    settings.admin_password_hash = get_password_hash("senha_admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Caso de Falha: Senha errada
        response = await client.post(
            "/api/admin/login",
            data={"username": "admin_de_teste", "password": "senha_errada"},
        )
        assert response.status_code == 401
        assert "detail" in response.json()

        # 2. Caso de Sucesso: Credenciais corretas
        response = await client.post(
            "/api/admin/login",
            data={"username": "admin_de_teste", "password": "senha_admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_secured_endpoints_unauthorized(setup_test_db: AsyncEngine) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Acesso sem token deve retornar 401
        response = await client.get("/api/admin/logs")
        assert response.status_code == 401

        response = await client.get("/api/admin/subscriptions")
        assert response.status_code == 401

        response = await client.get("/api/admin/brokers")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logs_endpoints_authorized(setup_test_db: AsyncEngine) -> None:
    # Arrange: Popula banco de logs
    container = get_container()
    log_repo = container["log_repo"]
    log = MessageLog(phone="5588999999999", direction="in", text="Olá", step="START")
    await log_repo.save(log)

    settings.admin_username = "admin_de_teste"
    settings.admin_password_hash = get_password_hash("senha_admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Efetua login para obter token
        login_res = await client.post(
            "/api/admin/login",
            data={"username": "admin_de_teste", "password": "senha_admin"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Act: Consome logs
        response = await client.get("/api/admin/logs", headers=headers)

        # Assert
        assert response.status_code == 200
        logs_list = response.json()
        assert len(logs_list) == 1
        assert logs_list[0]["phone"] == "5588999999999"
        assert logs_list[0]["text"] == "Olá"


@pytest.mark.asyncio
async def test_brokers_crud_endpoints_authorized(setup_test_db: AsyncEngine) -> None:
    # Arrange
    settings.admin_username = "admin_de_teste"
    settings.admin_password_hash = get_password_hash("senha_admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/admin/login",
            data={"username": "admin_de_teste", "password": "senha_admin"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. POST - Criação de corretor
        broker_data = {
            "instance_id": "test_inst",
            "broker_name": "Broker Teste",
            "phone_number": "5511777777777",
            "site_base_url": "https://test.net",
            "bot_name": "Amanda",
            "is_active": True,
        }
        create_res = await client.post("/api/admin/brokers", json=broker_data, headers=headers)
        assert create_res.status_code == 200
        assert create_res.json()["status"] == "success"

        # 2. GET - Listagem de corretores
        list_res = await client.get("/api/admin/brokers", headers=headers)
        assert list_res.status_code == 200
        brokers_list = list_res.json()
        assert len(brokers_list) == 1
        assert brokers_list[0]["instance_id"] == "test_inst"
        assert brokers_list[0]["broker_name"] == "Broker Teste"

        # 3. DELETE - Remoção de corretor
        delete_res = await client.delete("/api/admin/brokers/test_inst", headers=headers)
        assert delete_res.status_code == 200

        # Verifica se foi deletado
        list_res_after = await client.get("/api/admin/brokers", headers=headers)
        assert len(list_res_after.json()) == 0
