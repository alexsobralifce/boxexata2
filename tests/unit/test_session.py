from src.domain.entities.session import ConversationStep, Session


def test_session_initial_state() -> None:
    session = Session(phone="5588999990000")
    assert session.phone == "5588999990000"
    assert session.step == ConversationStep.START
    assert session.client_name is None
    assert session.intent is None
    assert session.property_type is None
    assert session.neighborhood is None
    assert session.max_value is None
    assert session.results == []
    assert session.result_offset == 0
    assert session.message_count == 0


def test_session_update_preferences() -> None:
    session = Session(phone="5588999990000")
    session.update_preferences(
        intent="Locação",
        property_type="casa",
        neighborhood="Centro",
        max_value=1200.0,
        client_name="Francisco",
    )
    assert session.intent == "Locação"
    assert session.property_type == "casa"
    assert session.neighborhood == "Centro"
    assert session.max_value == 1200.0
    assert session.client_name == "Francisco"


def test_session_transitions() -> None:
    session = Session(phone="5588999990000")
    session.transition_to(ConversationStep.PREFERENCES)
    assert session.step == ConversationStep.PREFERENCES


def test_session_increment_messages() -> None:
    session = Session(phone="5588999990000")
    session.increment_messages()
    assert session.message_count == 1
    session.increment_messages()
    assert session.message_count == 2


def test_session_reset() -> None:
    session = Session(phone="5588999990000")
    session.update_preferences(intent="Locação", property_type="casa")
    session.transition_to(ConversationStep.SHOWING)
    session.reset_search()
    assert session.step == ConversationStep.START
    assert session.intent is None
    assert session.property_type is None
    assert session.results == []
