from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.shared.config import settings


class DetailHandler(BaseHandler):
    """Handler para a etapa DETAIL (detalhes do imóvel e agendamento)."""

    def __init__(self, message_gateway: IMessageGateway) -> None:
        self.message_gateway = message_gateway

    async def handle(self, session: Session, text: str) -> bool:
        clean_text = text.lower().strip()

        # Comando "reiniciar"
        if clean_text in ("reiniciar", "reinicia", "começar", "comecar", "inicio", "início"):
            session.reset_search()
            session.transition_to(ConversationStep.INTENT)
            await self.message_gateway.send_text(
                session.phone,
                "Certo, vamos começar de novo! Você busca um imóvel para **Locação** ou **Venda**?"
            )
            return False

        # Comando "voltar"
        if clean_text in ("voltar", "volta", "lista", "resultados"):
            session.transition_to(ConversationStep.SHOWING)

            page_size = settings.results_page_size
            offset = session.result_offset
            slice_results = session.results[offset : offset + page_size]

            response_lines = [
                "Encontrei esses imóveis que encaixam nas suas preferências:\n"
            ]
            for idx, item in enumerate(slice_results):
                num = offset + idx + 1
                price = item.get("value", 0.0)
                price_fmt = f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                response_lines.append(
                    f"*{num}. {item.get('property_type')} no {item.get('neighborhood')}*\n"
                    f"Valor: {price_fmt}\n"
                    f"Ref: {item.get('ref')} | Endereço: {item.get('address')}\n"
                    f"Link: {item.get('url')}\n"
                )

            response_lines.append(
                "Digite o número do imóvel para ver mais detalhes (ex: 1, 2, 3), 'mais' para ver outros, ou 'reiniciar' para começar de novo."
            )

            await self.message_gateway.send_text(session.phone, "\n".join(response_lines))
            return False

        # Qualquer outra mensagem envia os dados de contato / agendamento
        await self.message_gateway.send_text(
            session.phone,
            "Para agendar uma visita ou falar com um corretor, clique no link abaixo:\n"
            f"https://wa.me/558836113000\n"
            "Ou ligue para o telefone fixo: (88) 3611-3000.\n\n"
            "Digite 'voltar' para retornar à lista de imóveis ou 'reiniciar' para fazer uma nova busca."
        )
        return False
