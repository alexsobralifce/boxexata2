from typing import Any
import pytest

from src.application.use_cases.notify_new_listings import NotifyNewListingsUseCase
from src.domain.entities.subscription import Subscription
from src.domain.entities.property_listing import PropertyListing
from src.domain.value_objects.money import Money
from tests.fakes.fake_property_repository import FakePropertyRepository
from tests.fakes.spy_message_gateway import SpyMessageGateway
from src.infrastructure.persistence.memory_subscription_store import MemorySubscriptionStore


@pytest.fixture
def notify_setup() -> tuple[
    NotifyNewListingsUseCase, FakePropertyRepository, SpyMessageGateway, MemorySubscriptionStore
]:
    property_repo = FakePropertyRepository()
    message_gateway = SpyMessageGateway()
    subscription_store = MemorySubscriptionStore()

    use_case = NotifyNewListingsUseCase(
        property_repo=property_repo,
        message_gateway=message_gateway,
        subscription_store=subscription_store,
    )
    return use_case, property_repo, message_gateway, subscription_store


@pytest.mark.asyncio
async def test_notify_new_listings_success(notify_setup: Any) -> None:
    use_case, property_repo, gateway, sub_store = notify_setup

    # 1. Cria assinatura
    sub = Subscription(
        phone="5588999990000",
        intent="Locação",
        property_type="Casa",
        neighborhood="Centro",
        max_value=1500.0,
    )
    await sub_store.save(sub)

    # 2. Adiciona imóvel correspondente no repositório
    p1 = PropertyListing(
        property_id="1",
        ref="REF1",
        property_type="Casa",
        address="Rua A, 10",
        neighborhood="Centro",
        value=Money(1200.0),
        url="http://site/1",
        photos=["http://site/img1.jpg"],
    )
    property_repo.add_property(p1)

    # 3. Executa caso de uso de notificações
    await use_case.execute()

    # Deve enviar 1 texto e 1 imagem de alerta
    assert len(gateway.sent_texts) == 1
    assert len(gateway.sent_images) == 1
    assert "REF1" in gateway.sent_texts[0]["text"]
    assert gateway.sent_images[0]["image_url"] == "http://site/img1.jpg"

    # 4. Executa novamente sem novos imóveis
    gateway.sent_texts.clear()
    gateway.sent_images.clear()
    await use_case.execute()

    # Não deve enviar duplicados
    assert len(gateway.sent_texts) == 0
    assert len(gateway.sent_images) == 0
