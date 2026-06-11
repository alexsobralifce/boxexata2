import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.services.llm_extractor import LLMPreferenceExtractor


@pytest.mark.asyncio
async def test_llm_extractor_success() -> None:
    # Cria o mock da resposta da API
    mock_response = MagicMock()
    mock_choices = MagicMock()
    mock_choices.message.content = (
        '{"nome_cliente": "Francisco", "finalidade": "Locação", "tipo": "casa", '
        '"bairro": "Centro", "valor_max": 1200}'
    )
    mock_response.choices = [mock_choices]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    extractor = LLMPreferenceExtractor(client=mock_client)
    res = await extractor.extract(
        "oi, me chamo Francisco e quero alugar uma casa no Centro por 1200 reais", []
    )

    assert res.get("client_name") == "Francisco"
    assert res.get("intent") == "Locação"
    assert res.get("property_type") == "Casa"
    assert res.get("neighborhood") == "Centro"
    assert res.get("max_value") == 1200.0


@pytest.mark.asyncio
async def test_llm_extractor_fallback_on_api_error() -> None:
    # Mock do cliente que falha (simulando timeout ou erro de rede)
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

    # Mock do extrator fallback (Regex)
    mock_fallback = AsyncMock()
    mock_fallback.extract.return_value = {"intent": "Locação", "neighborhood": "Centro"}

    extractor = LLMPreferenceExtractor(fallback_extractor=mock_fallback, client=mock_client)
    res = await extractor.extract("quero alugar no centro", [])

    # Deve chamar o fallback quando a chamada da LLM falhar
    mock_fallback.extract.assert_called_once_with("quero alugar no centro", [])
    assert res == {"intent": "Locação", "neighborhood": "Centro"}


@pytest.mark.asyncio
async def test_llm_extractor_trips_circuit_breaker() -> None:
    # Mock do cliente que sempre falha
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Connection Error"))

    # Mock do extrator fallback (Regex)
    mock_fallback = AsyncMock()
    mock_fallback.extract.return_value = {"fallback": True}

    # Circuit Breaker com limite de 2 falhas consecutivas
    extractor = LLMPreferenceExtractor(
        fallback_extractor=mock_fallback,
        client=mock_client,
    )
    # Ajusta o circuit breaker para ter threshold 2
    extractor.circuit_breaker.failure_threshold = 2

    # Primeira chamada: Falha e usa fallback
    res1 = await extractor.extract("msg1", [])
    assert res1 == {"fallback": True}
    assert extractor.circuit_breaker.state == "CLOSED"
    assert extractor.circuit_breaker.failure_count == 1

    # Segunda chamada: Falha e abre o circuito (trips)
    res2 = await extractor.extract("msg2", [])
    assert res2 == {"fallback": True}
    assert extractor.circuit_breaker.state == "OPEN"
    assert extractor.circuit_breaker.failure_count == 2

    # Reseta o mock de chamada do cliente da API
    mock_client.chat.completions.create.reset_mock()

    # Terceira chamada: Como o circuito está aberto, o LLMPreferenceExtractor
    # captura o CircuitBreakerOpenException e cai imediatamente no fallback
    # sem sequer tentar chamar o client.chat.completions.create
    res3 = await extractor.extract("msg3", [])
    assert res3 == {"fallback": True}
    mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_llm_extractor_reference_point() -> None:
    mock_response = MagicMock()
    mock_choices = MagicMock()
    mock_choices.message.content = (
        '{"nome_cliente": null, "finalidade": "Locação", "tipo": "casa", '
        '"bairro": null, "valor_max": null, "ponto_referencia": "UFC"}'
    )
    mock_response.choices = [mock_choices]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    extractor = LLMPreferenceExtractor(client=mock_client)
    res = await extractor.extract(
        "quero alugar uma casa perto da UFC", []
    )

    assert res.get("reference_point") == "UFC"
    assert res.get("intent") == "Locação"
    assert res.get("property_type") == "Casa"


@pytest.mark.asyncio
async def test_llm_proximity_ranking() -> None:
    mock_response = MagicMock()
    mock_choices = MagicMock()
    mock_choices.message.content = (
        '{"ranked_properties": ['
        '  {"id": "103", "proximity_description": "🚶 Aprox. 3 min a pé da UFC"},'
        '  {"id": "101", "proximity_description": "🚗 Aprox. 5 min de carro da UFC"}'
        ']}'
    )
    mock_response.choices = [mock_choices]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    extractor = LLMPreferenceExtractor(client=mock_client)
    properties = [
        {"id": "101", "ref": "REF101", "address": "Rua A", "neighborhood": "Centro"},
        {"id": "103", "ref": "REF103", "address": "Rua C", "neighborhood": "Junco"}
    ]
    res = await extractor.rank_properties_by_proximity("UFC", properties)

    assert len(res) == 2
    assert res[0]["id"] == "103"
    assert res[0]["proximity"] == "🚶 Aprox. 3 min a pé da UFC"
    assert res[1]["id"] == "101"
    assert res[1]["proximity"] == "🚗 Aprox. 5 min de carro da UFC"
