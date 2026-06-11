from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway


class StartHandler(BaseHandler):
    """Handler para a etapa START da conversa."""

    def __init__(self, message_gateway: IMessageGateway) -> None:
        self.message_gateway = message_gateway

    def _get_broker_info(self) -> tuple[str, str]:
        from src.shared.context import get_current_broker
        from src.shared.config import settings
        broker = get_current_broker()
        if broker:
            return broker.bot_name, broker.broker_name
        return settings.bot_name, "Exata Serviços Imobiliários de Sobral/CE"

    async def handle(self, session: Session, text: str) -> bool:
        bot_name, broker_name = self._get_broker_info()

        # Se o nome do cliente já foi extraído
        if session.client_name:
            session.transition_to(ConversationStep.INTENT)
            await self.message_gateway.send_text(
                session.phone,
                f"Prazer, {session.client_name}! Eu sou a {bot_name}, atendente virtual da {broker_name}.",
            )
            await self.message_gateway.send_text(
                session.phone, "Você está buscando um imóvel para **Locação** ou **Venda**?"
            )
            return False

        # Verifica se o texto é uma saudação simples
        clean_text = text.lower().strip()
        if clean_text in (
            "oi",
            "olá",
            "ola",
            "bom dia",
            "boa tarde",
            "boa noite",
            "start",
            "começar",
        ):
            await self.message_gateway.send_text(
                session.phone,
                f"Olá! Eu sou a {bot_name}, atendente virtual da {broker_name}. Antes de começarmos, qual o seu nome?",
            )
            return False

        # Caso contrário, assume que o texto é o nome do cliente
        session.client_name = text.strip().title()
        session.transition_to(ConversationStep.INTENT)
        await self.message_gateway.send_text(session.phone, f"Prazer, {session.client_name}!")
        await self.message_gateway.send_text(
            session.phone, "Você está buscando um imóvel para **Locação** ou **Venda**?"
        )
        return False
