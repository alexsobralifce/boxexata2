import pytest
import asyncio
from src.domain.entities.broker_profile import BrokerProfile
from src.infrastructure.whatsapp.evolution_gateway import EvolutionGateway
from src.infrastructure.scraper.exata_property_repository import ExataPropertyRepository
from src.shared.context import set_current_broker, current_broker


@pytest.mark.asyncio
async def test_multi_tenant_context_concurrency() -> None:
    # Arrange - Dois perfis de corretores
    profile_a = BrokerProfile(
        instance_id="corretor_a",
        broker_name="Broker A",
        phone_number="5511000000001",
        site_base_url="https://site-a.com",
        bot_name="Bot A",
    )
    profile_b = BrokerProfile(
        instance_id="corretor_b",
        broker_name="Broker B",
        phone_number="5511000000002",
        site_base_url="https://site-b.com",
        bot_name="Bot B",
    )

    gateway = EvolutionGateway()
    scraper = ExataPropertyRepository()

    # Cada corotina simula um request isolado que define seu ContextVar e faz chamadas
    async def task_a() -> None:
        tok = set_current_broker(profile_a)
        try:
            # Damos pequenos yields no loop de eventos para misturar a execução das corotinas
            await asyncio.sleep(0.01)
            # Verifica que o gateway lê o instance_id do corretor A
            assert gateway.instance == "corretor_a"
            await asyncio.sleep(0.02)
            # Verifica que o scraper lê a URL base do corretor A
            assert scraper.site_base_url == "https://site-a.com"
        finally:
            current_broker.reset(tok)

    async def task_b() -> None:
        tok = set_current_broker(profile_b)
        try:
            await asyncio.sleep(0.02)
            # Verifica que o gateway lê o instance_id do corretor B
            assert gateway.instance == "corretor_b"
            await asyncio.sleep(0.01)
            # Verifica que o scraper lê a URL base do corretor B
            assert scraper.site_base_url == "https://site-b.com"
        finally:
            current_broker.reset(tok)

    # Act - Roda as duas tarefas concorrentemente em paralelo
    await asyncio.gather(task_a(), task_b())
