import pytest
from src.application.services.regex_extractor import RegexPreferenceExtractor


@pytest.mark.asyncio
async def test_extract_name() -> None:
    extractor = RegexPreferenceExtractor()

    res = await extractor.extract("Olá, me chamo Francisco", [])
    assert res.get("client_name") == "Francisco"

    res = await extractor.extract("oi, sou o Carlos", [])
    assert res.get("client_name") == "Carlos"

    res = await extractor.extract("Oi, Maria", [])
    assert res.get("client_name") == "Maria"


@pytest.mark.asyncio
async def test_extract_intent() -> None:
    extractor = RegexPreferenceExtractor()

    res = await extractor.extract("quero alugar uma casa", [])
    assert res.get("intent") == "Locação"

    res = await extractor.extract("comprar um apartamento", [])
    assert res.get("intent") == "Venda"


@pytest.mark.asyncio
async def test_extract_property_type() -> None:
    extractor = RegexPreferenceExtractor()

    res = await extractor.extract("quero ver kitnets", [])
    assert res.get("property_type") == "Quitinete"

    res = await extractor.extract("apto mobiliado", [])
    assert res.get("property_type") == "Apartamento"

    res = await extractor.extract("casa ampla", [])
    assert res.get("property_type") == "Casa"


@pytest.mark.asyncio
async def test_extract_neighborhood() -> None:
    extractor = RegexPreferenceExtractor()

    res = await extractor.extract("imovel no centro de sobral", [])
    assert res.get("neighborhood") == "Centro"

    res = await extractor.extract("quero no renato parente", [])
    assert res.get("neighborhood") == "Renato Parente"


@pytest.mark.asyncio
async def test_extract_max_value() -> None:
    extractor = RegexPreferenceExtractor()

    res = await extractor.extract("aluguel ate 1500 reais", [])
    assert res.get("max_value") == 1500.0

    res = await extractor.extract("valor maximo de R$ 2.500,00", [])
    assert res.get("max_value") == 2500.0

    res = await extractor.extract("ate 1.5 mil", [])
    assert res.get("max_value") == 1500.0
