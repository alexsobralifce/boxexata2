import pytest
from src.domain.entities.property_listing import PropertyListing
from src.domain.entities.session import Session, ConversationStep
from src.domain.value_objects.money import Money
from tests.fakes.fake_property_repository import FakePropertyRepository
from tests.fakes.spy_message_gateway import SpyMessageGateway
from tests.fakes.fake_session_store import FakeSessionStore


@pytest.mark.asyncio
async def test_fake_property_repository() -> None:
    """Verifica que o repositório fictício armazena e filtra dados corretamente em testes."""
    repo = FakePropertyRepository()

    listing1 = PropertyListing(
        property_id="101",
        ref="C001",
        property_type="Casa",
        address="Rua A, 123",
        neighborhood="Centro",
        value=Money(1500.0),
        url="http://localhost/101",
    )

    listing2 = PropertyListing(
        property_id="102",
        ref="A002",
        property_type="Apartamento",
        address="Av. B, 456",
        neighborhood="Junco",
        value=Money(800.0),
        url="http://localhost/102",
    )

    repo.add_property(listing1)
    repo.add_property(listing2)

    # Busca por ID
    found = await repo.find_by_id("101")
    assert found == listing1

    not_found = await repo.find_by_id("999")
    assert not_found is None

    # Filtros na sessão
    session = Session(
        phone="12345",
        step=ConversationStep.PREFERENCES,
        property_type="Apartamento",
        neighborhood="Junco",
    )

    filtered = await repo.find_by_preferences(session)
    assert len(filtered) == 1
    assert filtered[0].id == "102"


@pytest.mark.asyncio
async def test_spy_message_gateway() -> None:
    """Verifica se o espião grava corretamente todas as chamadas de mensagem."""
    spy = SpyMessageGateway()

    await spy.send_text(phone="5588999999999", text="Olá", typing_delay=1.0)
    await spy.send_image(phone="5588999999999", image_url="http://image.jpg", caption="Foto")
    await spy.send_typing(phone="5588999999999", duration_ms=2000)

    # Verifica os registros
    assert len(spy.sent_texts) == 1
    assert spy.sent_texts[0]["text"] == "Olá"
    assert spy.sent_texts[0]["typing_delay"] == 1.0

    assert len(spy.sent_images) == 1
    assert spy.sent_images[0]["image_url"] == "http://image.jpg"
    assert spy.sent_images[0]["caption"] == "Foto"

    assert len(spy.sent_typings) == 1
    assert spy.sent_typings[0]["duration_ms"] == 2000

    # Reset
    spy.reset()
    assert len(spy.sent_texts) == 0
    assert len(spy.sent_images) == 0
    assert len(spy.sent_typings) == 0


@pytest.mark.asyncio
async def test_fake_session_store() -> None:
    """Verifica a criação e persistência de sessões no fake store."""
    store = FakeSessionStore()

    session = await store.get_or_create("5588999999999")
    assert session.phone == "5588999999999"
    assert session.step == ConversationStep.START

    session.update_preferences(client_name="Alexandre")
    await store.save(session)

    # Recupera novamente
    retrieved = await store.get_or_create("5588999999999")
    assert retrieved.client_name == "Alexandre"
