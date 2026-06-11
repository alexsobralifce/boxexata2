import pytest
from src.domain.entities.message_log import MessageLog
from src.infrastructure.persistence.null_log_repository import NullMessageLogRepository


@pytest.mark.asyncio
async def test_null_log_repository() -> None:
    # Arrange
    repo = NullMessageLogRepository()
    log = MessageLog(
        phone="5511999999999",
        direction="in",
        text="teste",
        step="START",
    )

    # Act & Assert
    try:
        await repo.save(log)
    except Exception as e:
        pytest.fail(f"NullMessageLogRepository.save lançou exceção inesperada: {e}")

    logs = await repo.list_by_phone("5511999999999")
    assert logs == []
