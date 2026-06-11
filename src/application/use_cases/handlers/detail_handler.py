from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.application.services.property_presenter import send_property_cards
from src.application.services import humanizer
from src.shared.config import settings


class DetailHandler(BaseHandler):
    """Handler para a etapa DETAIL (detalhes do imóvel e agendamento)."""

    def __init__(
        self,
        message_gateway: IMessageGateway,
        property_repo: IPropertyRepository,
    ) -> None:
        self.message_gateway = message_gateway
        self.property_repo = property_repo

    async def handle(self, session: Session, text: str) -> bool:
        clean_text = text.lower().strip()

        # Comando "reiniciar"
        if clean_text in ("reiniciar", "reinicia", "começar", "comecar", "inicio", "início"):
            session.reset_search()
            session.transition_to(ConversationStep.INTENT)
            await self.message_gateway.send_text(
                session.phone,
                "Certo, vamos começar de novo! Você busca um imóvel para **Locação** ou **Venda**?",
            )
            return False

        # Comando "voltar"
        if clean_text in ("voltar", "volta", "lista", "resultados"):
            session.transition_to(ConversationStep.SHOWING)

            page_size = settings.results_page_size
            offset = session.result_offset
            slice_results = session.results[offset : offset + page_size]

            await self.message_gateway.send_text(
                session.phone,
                "Aqui estão as opções novamente! 🏡✨👇"
            )

            await send_property_cards(
                phone=session.phone,
                slice_results=slice_results,
                start_num=offset + 1,
                property_repo=self.property_repo,
                message_gateway=self.message_gateway,
            )

            next_num_example = offset + 1
            footer_msg = (
                f"💡 *Dicas de navegação:*\n"
                f"- Digite o número do imóvel (ex: *{next_num_example}*) para ver opções de agendamento de visita ou mais fotos. 📸\n"
                f"- Digite *mais* para ver outras opções do seu perfil. 🔄\n"
                f"- Digite *alertar* para receber alertas deste perfil. 🔔\n"
                f"- Digite *reiniciar* para começar uma nova busca. 🔄"
            )
            await self.message_gateway.send_text(session.phone, footer_msg)
            return False

        # Qualquer outra mensagem envia os dados de contato / agendamento
        ref = ""
        if session.selected_property_id:
            try:
                listing = await self.property_repo.find_by_id(session.selected_property_id)
                if listing:
                    ref = listing.ref
            except Exception:
                pass

        booking_msg = humanizer.get_booking_phrase(ref)
        footer = humanizer.get_solicitude_footer()
        full_msg = f"{booking_msg}\n\n{footer}"
        await self.message_gateway.send_text(session.phone, full_msg)
        return False

