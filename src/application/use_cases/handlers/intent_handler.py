from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway


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
            return True
        elif "comp" in clean_text or "vend" in clean_text:
            session.intent = "Venda"
            session.transition_to(ConversationStep.PREFERENCES)
            return True

        nome = session.client_name or "cliente"
        await self.message_gateway.send_text(
            session.phone,
            f"Por favor, {nome}, digite **Locação** se você deseja alugar ou **Venda** se deseja comprar um imóvel.",
        )
        return False
