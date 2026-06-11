import pytest
from src.domain.entities.session import Session, ConversationStep
from src.infrastructure.scraper.exata_property_repository import ExataPropertyRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_scraper_find_by_preferences_all() -> None:
    """Verifica que o scraper real consegue recuperar imóveis do site Exata Serviços."""
    repository = ExataPropertyRepository()

    # Cria uma sessão vazia (sem filtros específicos) para trazer tudo da página inicial do scraper
    session = Session(phone="5588999999999", step=ConversationStep.PREFERENCES)

    listings = await repository.find_by_preferences(session)

    # Verifica que retornou imóveis (o site tem imóveis ativos na página principal)
    assert len(listings) > 0

    # Valida a estrutura dos itens retornados
    for listing in listings:
        assert listing.id != ""
        # Algumas propriedades no site têm o campo "Código" vazio na listagem geral,
        # portanto não podemos exigir listing.ref != ""
        assert listing.address != ""
        assert listing.neighborhood != ""
        assert listing.value.amount >= 0
        assert listing.url.startswith("https://www.exataservicos.net")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_scraper_find_by_preferences_with_filters() -> None:
    """Verifica que o scraper filtra corretamente por bairro e tipo usando dados reais."""
    repository = ExataPropertyRepository()

    # Filtra por Apartamento no Centro
    session = Session(
        phone="5588999999999",
        step=ConversationStep.PREFERENCES,
        property_type="Apartamento",
        neighborhood="Centro",
    )

    listings = await repository.find_by_preferences(session)

    # Todos os imóveis retornados devem respeitar o filtro
    for listing in listings:
        assert "centro" in listing.neighborhood.lower()
        assert "apartamento" in listing.property_type.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_scraper_find_by_id_and_details() -> None:
    """Busca detalhes de um imóvel real e valida o preenchimento de campos avançados."""
    repository = ExataPropertyRepository()

    # Busca a lista primeiro para obter um ID real válido
    session = Session(phone="5588999999999", step=ConversationStep.PREFERENCES)
    listings = await repository.find_by_preferences(session)
    assert len(listings) > 0

    # Pega o primeiro imóvel e faz a busca detalhada pelo ID dele
    target_listing = listings[0]
    detail = await repository.find_by_id(target_listing.id)

    assert detail is not None
    assert detail.id == target_listing.id
    # O código de referência no detalhe pode estar mais completo que na listagem (que pode vir vazia)
    if target_listing.ref:
        assert detail.ref == target_listing.ref
    else:
        assert detail.ref is not None  # Deve ser preenchido (ou vazio, mas não None)
    assert detail.address != ""
    assert detail.neighborhood != ""
    assert detail.value.amount == target_listing.value.amount
    # Detalhes devem preencher fotos e features se disponíveis no HTML
    assert len(detail.photos) >= 1
    # A primeira foto deve ser válida
    assert detail.photos[0].startswith("https://www.exataservicos.net")
