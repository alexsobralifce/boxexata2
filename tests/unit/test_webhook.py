import pytest
from unittest.mock import AsyncMock
from src.presentation.webhook import _process_webhook_message
from src.shared.config import settings
from src.shared.container import get_container
from src.domain.entities.broker_profile import BrokerProfile


@pytest.mark.asyncio
async def test_process_webhook_message_no_database_allows_all() -> None:
    # Arrange
    original_db_url = settings.database_url
    settings.database_url = ""

    container = get_container()

    # Mock broker repo to return None
    mock_broker_repo = AsyncMock()
    mock_broker_repo.get_by_instance.return_value = None

    # Mock use case
    mock_use_case = AsyncMock()

    # Save original container dependencies
    orig_broker_repo = container.get("broker_repo")
    orig_use_case = container.get("handle_message")

    container["broker_repo"] = mock_broker_repo
    container["handle_message"] = mock_use_case

    try:
        # Act
        await _process_webhook_message("non_existent_instance", "5588999999999", "Oi")

        # Assert
        mock_broker_repo.get_by_instance.assert_called_once_with("non_existent_instance")
        mock_use_case.execute.assert_called_once_with("5588999999999", "Oi")
    finally:
        # Restore
        settings.database_url = original_db_url
        if orig_broker_repo:
            container["broker_repo"] = orig_broker_repo
        if orig_use_case:
            container["handle_message"] = orig_use_case


@pytest.mark.asyncio
async def test_process_webhook_message_with_database_blocks_unregistered() -> None:
    # Arrange
    original_db_url = settings.database_url
    settings.database_url = "postgresql+asyncpg://mock:mock@localhost:5432/db"

    container = get_container()

    # Mock broker repo to return None (unregistered)
    mock_broker_repo = AsyncMock()
    mock_broker_repo.get_by_instance.return_value = None

    # Mock use case
    mock_use_case = AsyncMock()

    # Save original container dependencies
    orig_broker_repo = container.get("broker_repo")
    orig_use_case = container.get("handle_message")

    container["broker_repo"] = mock_broker_repo
    container["handle_message"] = mock_use_case

    try:
        # Act
        await _process_webhook_message("deleted_instance", "5588999999999", "Oi")

        # Assert
        mock_broker_repo.get_by_instance.assert_called_once_with("deleted_instance")
        mock_use_case.execute.assert_not_called()
    finally:
        # Restore
        settings.database_url = original_db_url
        if orig_broker_repo:
            container["broker_repo"] = orig_broker_repo
        if orig_use_case:
            container["handle_message"] = orig_use_case


@pytest.mark.asyncio
async def test_process_webhook_message_with_database_blocks_inactive() -> None:
    # Arrange
    original_db_url = settings.database_url
    settings.database_url = "postgresql+asyncpg://mock:mock@localhost:5432/db"

    container = get_container()

    # Mock broker repo to return inactive broker profile
    inactive_broker = BrokerProfile(
        instance_id="inactive_instance",
        broker_name="Broker Test",
        phone_number="5588992215701",
        site_base_url="https://test.com",
        bot_name="Ana",
        is_active=False,
    )
    mock_broker_repo = AsyncMock()
    mock_broker_repo.get_by_instance.return_value = inactive_broker

    # Mock use case
    mock_use_case = AsyncMock()

    # Save original container dependencies
    orig_broker_repo = container.get("broker_repo")
    orig_use_case = container.get("handle_message")

    container["broker_repo"] = mock_broker_repo
    container["handle_message"] = mock_use_case

    try:
        # Act
        await _process_webhook_message("inactive_instance", "5588999999999", "Oi")

        # Assert
        mock_broker_repo.get_by_instance.assert_called_once_with("inactive_instance")
        mock_use_case.execute.assert_not_called()
    finally:
        # Restore
        settings.database_url = original_db_url
        if orig_broker_repo:
            container["broker_repo"] = orig_broker_repo
        if orig_use_case:
            container["handle_message"] = orig_use_case


@pytest.mark.asyncio
async def test_process_webhook_message_with_database_allows_active() -> None:
    # Arrange
    original_db_url = settings.database_url
    settings.database_url = "postgresql+asyncpg://mock:mock@localhost:5432/db"

    container = get_container()

    # Mock broker repo to return active broker profile
    active_broker = BrokerProfile(
        instance_id="active_instance",
        broker_name="Broker Test",
        phone_number="5588992215701",
        site_base_url="https://test.com",
        bot_name="Ana",
        is_active=True,
    )
    mock_broker_repo = AsyncMock()
    mock_broker_repo.get_by_instance.return_value = active_broker

    # Mock use case
    mock_use_case = AsyncMock()

    # Save original container dependencies
    orig_broker_repo = container.get("broker_repo")
    orig_use_case = container.get("handle_message")

    container["broker_repo"] = mock_broker_repo
    container["handle_message"] = mock_use_case

    try:
        # Act
        await _process_webhook_message("active_instance", "5588999999999", "Oi")

        # Assert
        mock_broker_repo.get_by_instance.assert_called_once_with("active_instance")
        mock_use_case.execute.assert_called_once_with("5588999999999", "Oi")
    finally:
        # Restore
        settings.database_url = original_db_url
        if orig_broker_repo:
            container["broker_repo"] = orig_broker_repo
        if orig_use_case:
            container["handle_message"] = orig_use_case
