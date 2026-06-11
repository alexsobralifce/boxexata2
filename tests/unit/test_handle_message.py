import pytest
from src.application.use_cases.handle_message import HandleMessageUseCase
from src.domain.entities.session import ConversationStep
from src.domain.entities.property_listing import PropertyListing
from src.domain.value_objects.money import Money
from src.application.services.regex_extractor import RegexPreferenceExtractor
from tests.fakes.fake_property_repository import FakePropertyRepository
from tests.fakes.fake_session_store import FakeSessionStore
from tests.fakes.spy_message_gateway import SpyMessageGateway


@pytest.fixture
def test_setup() -> tuple[HandleMessageUseCase, FakePropertyRepository, SpyMessageGateway, FakeSessionStore]:
    session_store = FakeSessionStore()
    property_repo = FakePropertyRepository()
    message_gateway = SpyMessageGateway()
    extractor = RegexPreferenceExtractor()

    # Adiciona imóveis fake ao repositório
    p1 = PropertyListing(
        property_id="101",
        ref="REF101",
        property_type="Casa",
        address="Rua A, 100",
        neighborhood="Centro",
        value=Money(1200.0),
        url="http://site/101",
        features=["2 quartos", "garagem"],
        photos=["http://site/101_img1.jpg"]
    )
    p2 = PropertyListing(
        property_id="102",
        ref="REF102",
        property_type="Apartamento",
        address="Rua B, 200",
        neighborhood="Derby",
        value=Money(1800.0),
        url="http://site/102",
        features=["3 quartos", "piscina"],
        photos=["http://site/102_img1.jpg"]
    )
    p3 = PropertyListing(
        property_id="103",
        ref="REF103",
        property_type="Quitinete",
        address="Rua C, 300",
        neighborhood="Centro",
        value=Money(800.0),
        url="http://site/103",
        features=["1 quarto"],
        photos=["http://site/103_img1.jpg"]
    )

    property_repo.add_property(p1)
    property_repo.add_property(p2)
    property_repo.add_property(p3)

    use_case = HandleMessageUseCase(
        session_store=session_store,
        property_repo=property_repo,
        message_gateway=message_gateway,
        extractor=extractor
    )

    return use_case, property_repo, message_gateway, session_store


@pytest.mark.asyncio
async def test_full_dialog_flow(test_setup) -> None:
    use_case, property_repo, gateway, session_store = test_setup
    phone = "5588999999999"

    # Step 1: Saudação inicial
    await use_case.execute(phone, "oi", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.START
    assert len(gateway.sent_texts) == 1
    assert "qual o seu nome" in gateway.sent_texts[-1]["text"].lower()

    # Step 2: Enviar nome
    await use_case.execute(phone, "Francisco", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.client_name == "Francisco"
    assert session.step == ConversationStep.INTENT
    assert len(gateway.sent_texts) == 3  # Anterior (1) + Saudação Prazer (1) + Pergunta Locação (1)
    assert "venda" in gateway.sent_texts[-1]["text"].lower()

    # Step 3: Escolher intent
    await use_case.execute(phone, "quero alugar", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.intent == "Locação"
    assert session.step == ConversationStep.PREFERENCES
    assert "tipo" in gateway.sent_texts[-1]["text"].lower()

    # Step 4: Enviar preferências e exibir resultados
    await use_case.execute(phone, "casa no centro ate 1500", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.SHOWING
    assert session.property_type == "Casa"
    assert session.neighborhood == "Centro"
    assert session.max_value == 1500.0
    assert len(session.results) == 1
    assert "REF101" in gateway.sent_texts[-1]["text"]

    # Step 5: Selecionar o imóvel 1 (absoluto ou relativo)
    await use_case.execute(phone, "1", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.DETAIL
    assert session.selected_property_id == "101"
    # Deve enviar fotos e detalhes
    assert len(gateway.sent_images) == 1
    assert gateway.sent_images[0]["image_url"] == "http://site/101_img1.jpg"
    assert "Rua A, 100" in gateway.sent_texts[-1]["text"]

    # Step 6: Voltar para a lista
    await use_case.execute(phone, "voltar", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.SHOWING
    assert "REF101" in gateway.sent_texts[-1]["text"]

    # Step 7: Reiniciar busca
    await use_case.execute(phone, "reiniciar", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.INTENT
    assert session.intent is None
    assert session.property_type is None
    assert "Locação" in gateway.sent_texts[-1]["text"]
