from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.application.services import humanizer


class IntentHandler(BaseHandler):
    """Handler para a etapa INTENT da conversa."""

    def __init__(self, message_gateway: IMessageGateway) -> None:
        self.message_gateway = message_gateway

    async def handle(self, session: Session, text: str) -> bool:
        if session.intent:
            session.transition_to(ConversationStep.PREFERENCES)
            return True

        clean_text = text.lower().strip()
        if "alug" in clean_text or "loca" in clean_text:
            session.intent = "Locação"
            session.transition_to(ConversationStep.PREFERENCES)
            confirm_msg = humanizer.get_intent_recognized_phrase(session.client_name, "Locação")
            await self.message_gateway.send_text(session.phone, confirm_msg)
            return True
        elif "comp" in clean_text or "vend" in clean_text:
            session.intent = "Venda"
            session.transition_to(ConversationStep.PREFERENCES)
            confirm_msg = humanizer.get_intent_recognized_phrase(session.client_name, "Venda")
            await self.message_gateway.send_text(session.phone, confirm_msg)
            return True

        invalid_msg = humanizer.get_intent_invalid_phrase(session.client_name)
        await self.message_gateway.send_text(session.phone, invalid_msg)
        return False
