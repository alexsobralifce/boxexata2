import asyncio
import inspect
import time
from typing import Callable, Any


class CircuitBreakerOpenException(Exception):
    """Exceção lançada quando o Circuit Breaker está aberto e rejeita chamadas."""
    pass


class CircuitBreaker:
    """Implementação genérica e assíncrona do padrão Circuit Breaker."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED | OPEN | HALF-OPEN
        self.last_state_change = time.time()
        self._lock = asyncio.Lock()

    def _check_state(self) -> None:
        """Verifica se o circuito pode transitar de OPEN para HALF-OPEN com base no tempo de recuperação."""
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_timeout:
                self.state = "HALF-OPEN"
                self.last_state_change = time.time()

    def _on_success(self) -> None:
        """Reseta contadores em caso de sucesso."""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_state_change = time.time()

    def _on_failure(self) -> None:
        """Incrementa falhas e abre o circuito se ultrapassar o limite."""
        self.failure_count += 1
        if self.state in ("CLOSED", "HALF-OPEN") and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Executa a função monitorada pelo Circuit Breaker."""
        async with self._lock:
            self._check_state()
            if self.state == "OPEN":
                raise CircuitBreakerOpenException("Circuit Breaker is OPEN. Calls blocked.")

        try:
            # Verifica se a função é uma corrotina para await
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            async with self._lock:
                self._on_success()
            return result
        except Exception as e:
            async with self._lock:
                self._on_failure()
            raise e
