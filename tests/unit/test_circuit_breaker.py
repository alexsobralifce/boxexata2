import asyncio
import pytest
from src.shared.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException


@pytest.mark.asyncio
async def test_circuit_breaker_closed_state() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    async def success_fn() -> str:
        return "success"

    # Chamada bem-sucedida funciona normal e mantém estado CLOSED
    res = await breaker.call(success_fn)
    assert res == "success"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    async def fail_fn() -> None:
        raise ValueError("failing")

    # Primeira falha: incrementa falhas mas permanece CLOSED
    with pytest.raises(ValueError):
        await breaker.call(fail_fn)
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 1

    # Segunda falha: atinge limite de 2, circuito abre
    with pytest.raises(ValueError):
        await breaker.call(fail_fn)
    assert breaker.state == "OPEN"
    assert breaker.failure_count == 2

    # Chamada subsequente deve lançar CircuitBreakerOpenException imediatamente
    with pytest.raises(CircuitBreakerOpenException):
        await breaker.call(fail_fn)


@pytest.mark.asyncio
async def test_circuit_breaker_cooldown_and_half_open() -> None:
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

    async def fail_fn() -> None:
        raise ValueError("failing")

    # Tripa o circuito
    with pytest.raises(ValueError):
        await breaker.call(fail_fn)
    assert breaker.state == "OPEN"

    # Espera tempo de cooldown passar
    await asyncio.sleep(0.06)

    # Nova chamada deve transitar para HALF-OPEN e executar a função
    called: bool = False

    async def recovery_fn() -> str:
        nonlocal called
        called = True
        return "recovered"

    res = await breaker.call(recovery_fn)
    assert res == "recovered"
    assert called is True
    # Se a chamada HALF-OPEN for bem-sucedida, o estado volta para CLOSED
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_reopens() -> None:
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

    async def fail_fn() -> None:
        raise ValueError("failing")

    # Tripa o circuito
    with pytest.raises(ValueError):
        await breaker.call(fail_fn)
    assert breaker.state == "OPEN"

    # Espera cooldown
    await asyncio.sleep(0.06)

    # Executa função que falha no estado HALF-OPEN. Deve voltar a ficar OPEN
    with pytest.raises(ValueError):
        await breaker.call(fail_fn)

    assert breaker.state == "OPEN"
    # Chamadas subsequentes continuam bloqueadas
    with pytest.raises(CircuitBreakerOpenException):
        await breaker.call(fail_fn)
