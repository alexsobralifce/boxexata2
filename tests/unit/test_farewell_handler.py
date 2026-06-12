import pytest
from src.application.use_cases.handlers.farewell_handler import FarewellHandler
from src.domain.entities.session import Session, ConversationStep
from tests.fakes.spy_message_gateway import SpyMessageGateway


@pytest.mark.asyncio
async def test_farewell_handler_continue() -> None:
    gateway = SpyMessageGateway()
    handler = FarewellHandler(gateway)
    session = Session(phone="5588999999999", client_name="Alexandre")
    session.transition_to(ConversationStep.FAREWELL)

    # 1/sim should transition to INTENT
    result = await handler.handle(session, "1")

    assert result is False
    assert session.step == ConversationStep.INTENT
    assert len(gateway.sent_texts) == 1
    assert "locação" in gateway.sent_texts[0]["text"].lower()


@pytest.mark.asyncio
async def test_farewell_handler_end() -> None:
    gateway = SpyMessageGateway()
    handler = FarewellHandler(gateway)
    session = Session(phone="5588999999999", client_name="Alexandre")
    session.transition_to(ConversationStep.FAREWELL)

    # 2/nao should transition/reset to START
    result = await handler.handle(session, "não")

    assert result is False
    assert session.step == ConversationStep.START
    assert len(gateway.sent_texts) == 1


@pytest.mark.asyncio
async def test_farewell_handler_invalid() -> None:
    gateway = SpyMessageGateway()
    handler = FarewellHandler(gateway)
    session = Session(phone="5588999999999", client_name="Alexandre")
    session.transition_to(ConversationStep.FAREWELL)

    # invalid option should keep step and show message
    result = await handler.handle(session, "something else")

    assert result is False
    assert session.step == ConversationStep.FAREWELL
    assert len(gateway.sent_texts) == 1
