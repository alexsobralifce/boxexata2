from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.application.services import humanizer
from src.shared.logger import logger


class FarewellHandler(BaseHandler):
    """Handler para o estado FAREWELL.

    Ativado após a criação de um alerta. Pergunta ao cliente se deseja
    continuar o atendimento ou encerrar:
      - 1 / sim → reinicia o atendimento (vai para INTENT)
      - 2 / não → agradece e encerra (reset para START)
    """

    def __init__(self, message_gateway: IMessageGateway) -> None:
        self.message_gateway = message_gateway

    async def handle(self, session: Session, text: str) -> bool:
        clean_text = text.lower().strip()

        # Opção 1: cliente quer continuar → reinicia o atendimento
        if clean_text in ("1", "sim", "s", "1 sim", "quero continuar", "continuar", "continue"):
            logger.info("Cliente optou por continuar o atendimento após alerta", phone=session.phone)
            session.reset_search()
            session.transition_to(ConversationStep.INTENT)

            name = session.client_name
            greeting = humanizer.get_greeting()
            nome_str = f", {name}" if name else ""
            restart_msg = (
                f"{greeting}{nome_str}! 😊 Com prazer, vamos continuar.\n\n"
                "Você busca um imóvel para *Locação* ou *Venda*?"
            )
            await self.message_gateway.send_text(session.phone, restart_msg)
            return False

        # Opção 2: cliente quer encerrar → despedida calorosa + reset para START
        if clean_text in ("2", "não", "nao", "n", "2 não", "2 nao", "encerrar", "tchau", "até logo", "ate logo", "obrigado", "obrigada"):
            logger.info("Cliente optou por encerrar o atendimento após alerta", phone=session.phone)
            goodbye_msg = humanizer.get_farewell_goodbye_phrase(session.client_name)
            await self.message_gateway.send_text(session.phone, goodbye_msg)

            # Reseta a sessão para START → próxima mensagem recomeça naturalmente
            session.reset_search()
            return False

        # Opção inválida → pede gentilmente que escolha 1 ou 2
        logger.info("Resposta inválida no estado FAREWELL", phone=session.phone, text=text)
        invalid_msg = humanizer.get_farewell_invalid_option_phrase()
        await self.message_gateway.send_text(session.phone, invalid_msg)
        return False
