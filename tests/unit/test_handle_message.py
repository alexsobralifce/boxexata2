import pytest
from typing import Any
from unittest.mock import patch
from src.application.use_cases.handle_message import HandleMessageUseCase
from src.domain.entities.session import ConversationStep
from src.domain.entities.property_listing import PropertyListing
from src.domain.value_objects.money import Money
from src.application.services.regex_extractor import RegexPreferenceExtractor
from tests.fakes.fake_property_repository import FakePropertyRepository
from tests.fakes.fake_session_store import FakeSessionStore
from tests.fakes.spy_message_gateway import SpyMessageGateway


@pytest.fixture(autouse=True)
def mock_random_choice() -> Any:
    with patch("random.choice", side_effect=lambda x: x[0]):
        yield


@pytest.fixture

def test_setup() -> tuple[
    HandleMessageUseCase, FakePropertyRepository, SpyMessageGateway, FakeSessionStore
]:
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
        photos=["http://site/101_img1.jpg"],
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
        photos=["http://site/102_img1.jpg"],
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
        photos=["http://site/103_img1.jpg"],
    )

    property_repo.add_property(p1)
    property_repo.add_property(p2)
    property_repo.add_property(p3)

    from src.infrastructure.persistence.memory_subscription_store import MemorySubscriptionStore

    subscription_store = MemorySubscriptionStore()

    use_case = HandleMessageUseCase(
        session_store=session_store,
        property_repo=property_repo,
        message_gateway=message_gateway,
        extractor=extractor,
        subscription_store=subscription_store,
    )

    return use_case, property_repo, message_gateway, session_store


@pytest.mark.asyncio
async def test_full_dialog_flow(test_setup: Any) -> None:
    use_case, property_repo, gateway, session_store = test_setup
    phone = "5588999999999"

    # Step 1: Saudação inicial
    await use_case.execute(phone, "oi", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.START
    assert len(gateway.sent_texts) == 1
    assert "qual" in gateway.sent_texts[-1]["text"].lower() and "seu nome" in gateway.sent_texts[-1]["text"].lower()

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

    # Step 4: Enviar preferências → bot exibe confirmação de critérios
    await use_case.execute(phone, "casa no centro ate 1500", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.CONFIRM_CRITERIA
    assert session.property_type == "Casa"
    assert session.neighborhood == "Centro"
    assert session.max_value == 1500.0
    assert "confirmando sua busca" in gateway.sent_texts[-1]["text"].lower()

    # Step 4b: Cliente confirma os critérios → bot busca e exibe resultados
    await use_case.execute(phone, "sim", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.SHOWING
    assert len(session.results) == 1
    assert any("REF101" in msg["text"] for msg in gateway.sent_texts)
    assert len(gateway.sent_images) == 1

    # Step 5: Selecionar o imóvel 1 (absoluto ou relativo)
    await use_case.execute(phone, "1", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.DETAIL
    assert session.selected_property_id == "101"
    # Deve enviar fotos e detalhes (1 cover image from step 4 + 1 detailed view photo = 2 total)
    assert len(gateway.sent_images) == 2
    assert gateway.sent_images[-1]["image_url"] == "http://site/101_img1.jpg"
    assert "Rua A, 100" in gateway.sent_texts[-1]["text"]

    # Step 6: Voltar para a lista
    await use_case.execute(phone, "voltar", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.SHOWING
    assert any("REF101" in msg["text"] for msg in gateway.sent_texts[-4:])

    # Step 7: Reiniciar busca
    await use_case.execute(phone, "reiniciar", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.INTENT
    assert session.intent is None
    assert session.property_type is None
    assert "Locação" in gateway.sent_texts[-1]["text"]


@pytest.mark.asyncio
async def test_intent_handler_invalid_inputs(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999999998"

    await use_case.execute(phone, "oi", bypass_hours=True)
    await use_case.execute(phone, "Francisco", bypass_hours=True)

    # Envia uma mensagem inválida para a escolha da intent
    await use_case.execute(phone, "qualquer coisa", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.INTENT
    assert "por favor, francisco, digite **locação**" in gateway.sent_texts[-1]["text"].lower()


@pytest.mark.asyncio
async def test_preferences_handler_missing_type_and_neighborhood(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999999997"

    # Criamos manualmente uma sessão em PREFERENCES sem tipo/bairro
    session = await session_store.get_or_create(phone)
    session.client_name = "Francisco"
    session.intent = "Locação"
    session.step = ConversationStep.PREFERENCES
    await session_store.save(session)

    # Executa sem tipo definido
    await use_case.execute(phone, "olá", bypass_hours=True)
    assert "qual tipo de imóvel" in gateway.sent_texts[-1]["text"].lower()

    # Define o tipo, mas deixa o bairro vazio
    session.property_type = "Casa"
    await session_store.save(session)
    await use_case.execute(phone, "olá", bypass_hours=True)
    assert "em qual bairro" in gateway.sent_texts[-1]["text"].lower()


@pytest.mark.asyncio
async def test_preferences_handler_no_results(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999999996"

    session = await session_store.get_or_create(phone)
    session.client_name = "Francisco"
    session.intent = "Locação"
    session.property_type = "Casa"
    session.neighborhood = "Derby"
    session.max_value = 500.0  # Nenhuma casa no Derby por R$ 500
    session.step = ConversationStep.PREFERENCES
    session._confirmed_search = True  # type: ignore[attr-defined]  # pula etapa de confirmação
    await session_store.save(session)

    await use_case.execute(phone, "buscar", bypass_hours=True)
    session = await session_store.get_or_create(phone)
    assert session.step == ConversationStep.SHOWING
    assert "quer que eu te avise" in gateway.sent_texts[-1]["text"].lower()


@pytest.mark.asyncio
async def test_preferences_handler_error(test_setup: Any) -> None:
    use_case, property_repo, gateway, session_store = test_setup
    phone = "5588999999995"

    # Força um erro na busca
    async def raise_error(*args: Any, **kwargs: Any) -> Any:
        raise Exception("Erro simulado do scraper")

    property_repo.find_by_preferences = raise_error

    session = await session_store.get_or_create(phone)
    session.client_name = "Francisco"
    session.intent = "Locação"
    session.property_type = "Casa"
    session.neighborhood = "Centro"
    session.step = ConversationStep.PREFERENCES
    session._confirmed_search = True  # type: ignore[attr-defined]  # pula etapa de confirmação
    await session_store.save(session)

    await use_case.execute(phone, "buscar", bypass_hours=True)
    assert "tive um problema ao pesquisar" in gateway.sent_texts[-1]["text"].lower()


@pytest.mark.asyncio
async def test_showing_handler_more_no_results(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999999994"

    session = await session_store.get_or_create(phone)
    session.step = ConversationStep.SHOWING
    session.results = [{"id": "1", "property_type": "Casa", "neighborhood": "Centro"}]
    session.result_offset = 0
    await session_store.save(session)

    # Solicita mais resultados, mas offset + page_size >= resultados
    await use_case.execute(phone, "mais", bypass_hours=True)
    assert "não encontrei mais imóveis" in gateway.sent_texts[-1]["text"].lower()


@pytest.mark.asyncio
async def test_showing_handler_invalid_selection(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999999993"

    session = await session_store.get_or_create(phone)
    session.step = ConversationStep.SHOWING
    session.results = [{"id": "101", "property_type": "Casa", "neighborhood": "Centro"}]
    session.result_offset = 0
    await session_store.save(session)

    # Escolha inválida (fora do range)
    await use_case.execute(phone, "5", bypass_hours=True)
    assert "não entendi. por favor, digite o número" in gateway.sent_texts[-1]["text"].lower()

    # Escolha inválida (não numérica/não comando)
    await use_case.execute(phone, "qualquer", bypass_hours=True)
    assert "não entendi. por favor, digite o número" in gateway.sent_texts[-2]["text"].lower()


@pytest.mark.asyncio
async def test_showing_handler_not_found_id(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999999992"

    session = await session_store.get_or_create(phone)
    session.step = ConversationStep.SHOWING
    # ID não existe no repositório fictício
    session.results = [{"id": "999", "property_type": "Casa", "neighborhood": "Centro"}]
    session.result_offset = 0
    await session_store.save(session)

    await use_case.execute(phone, "1", bypass_hours=True)
    assert "não consegui carregar os detalhes" in gateway.sent_texts[-1]["text"].lower()


@pytest.mark.asyncio
async def test_detail_handler_contact(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999999991"

    session = await session_store.get_or_create(phone)
    session.step = ConversationStep.DETAIL
    session.selected_property_id = "101"
    await session_store.save(session)

    await use_case.execute(phone, "quero agendar", bypass_hours=True)
    assert "agendar" in gateway.sent_texts[-1]["text"].lower() or "visita" in gateway.sent_texts[-1]["text"].lower()


@pytest.mark.asyncio
async def test_showing_handler_alertar(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999990001"

    session = await session_store.get_or_create(phone)
    session.client_name = "Maria"
    session.intent = "Locação"
    session.property_type = "Casa"
    session.neighborhood = "Centro"
    session.max_value = 1200.0
    session.step = ConversationStep.SHOWING
    await session_store.save(session)

    await use_case.execute(phone, "alertar", bypass_hours=True)

    # Verifica se enviou mensagem de sucesso
    assert "assinatura de alertas ativada" in gateway.sent_texts[-1]["text"].lower()

    # Verifica se salvou a assinatura no store
    sub = await use_case._subscription_store.get(phone)
    assert sub is not None
    assert sub.phone == phone
    assert sub.property_type == "Casa"
    assert sub.neighborhood == "Centro"
    assert sub.max_value == 1200.0


@pytest.mark.asyncio
async def test_showing_handler_desativar_alerta(test_setup: Any) -> None:
    use_case, _, gateway, session_store = test_setup
    phone = "5588999990002"

    session = await session_store.get_or_create(phone)
    session.step = ConversationStep.SHOWING
    await session_store.save(session)

    # Cria uma assinatura ativa direto no store
    from src.domain.entities.subscription import Subscription

    sub = Subscription(
        phone=phone,
        intent="Locação",
        property_type="Casa",
        neighborhood="Centro",
    )
    await use_case._subscription_store.save(sub)

    await use_case.execute(phone, "desativar alerta", bypass_hours=True)

    # Verifica se deletou do store
    deleted_sub = await use_case._subscription_store.get(phone)
    assert deleted_sub is None
    assert "cancelados com sucesso" in gateway.sent_texts[-1]["text"].lower()
