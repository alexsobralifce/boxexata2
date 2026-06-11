import re
from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.domain.repositories.i_subscription_store import ISubscriptionStore
from src.shared.config import settings
from src.shared.logger import logger
from src.application.services.property_presenter import send_property_cards
from src.application.services import humanizer


class ShowingHandler(BaseHandler):
    """Handler para a etapa SHOWING (exibição de resultados e seleção)."""

    def __init__(
        self,
        property_repo: IPropertyRepository,
        message_gateway: IMessageGateway,
        subscription_store: ISubscriptionStore,
    ) -> None:
        self.property_repo = property_repo
        self.message_gateway = message_gateway
        self.subscription_store = subscription_store

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

        # Comando "alertar" / "alerta" / "ativar alerta" / "receber alertas"
        if clean_text in (
            "alertar",
            "alerta",
            "alertas",
            "receber alerta",
            "receber alertas",
            "ativar alerta",
            "ativar alertas",
        ):
            if not session.intent or not session.property_type or not session.neighborhood:
                await self.message_gateway.send_text(
                    session.phone,
                    "Você precisa definir um tipo de imóvel e bairro antes de assinar alertas. Digite 'reiniciar' para fazer uma busca completa.",
                )
                return False

            from src.domain.entities.subscription import Subscription

            subscription = Subscription(
                phone=session.phone,
                intent=session.intent,
                property_type=session.property_type,
                neighborhood=session.neighborhood,
                max_value=session.max_value,
            )
            await self.subscription_store.save(subscription)

            alert_msg = humanizer.get_alert_activated_phrase(
                session.client_name, session.property_type, session.neighborhood, session.intent, session.max_value
            )
            await self.message_gateway.send_text(session.phone, alert_msg)
            return False

        # Comando "desativar alerta" / "cancelar alerta" / "remover alerta"
        if clean_text in (
            "desativar alerta",
            "desativar alertas",
            "cancelar alerta",
            "cancelar alertas",
            "remover alerta",
            "remover alertas",
        ):
            await self.subscription_store.delete(session.phone)
            cancel_msg = humanizer.get_alert_cancelled_phrase()
            await self.message_gateway.send_text(session.phone, cancel_msg)
            return False

        # Se houver 0 resultados na busca, os únicos comandos permitidos além de alertar/desativar são reiniciar
        if len(session.results) == 0:
            await self.message_gateway.send_text(
                session.phone,
                "Não há imóveis disponíveis com este perfil para mostrar agora. 😔 Mas você pode digitar **alertar** para assinar alertas desse perfil, ou **reiniciar** para tentar com outros critérios!",
            )
            return False

        # Comando "mais" ou "outro"
        if clean_text in ("mais", "outro", "outros", "mais resultados", "proxima", "próxima"):
            page_size = settings.results_page_size
            next_offset = session.result_offset + page_size

            if next_offset < len(session.results):
                session.result_offset = next_offset
                slice_results = session.results[next_offset : next_offset + page_size]

                await self.message_gateway.send_text(
                    session.phone,
                    "Aqui estão mais algumas opções! 🏡✨👇"
                )

                await send_property_cards(
                    phone=session.phone,
                    slice_results=slice_results,
                    start_num=next_offset + 1,
                    property_repo=self.property_repo,
                    message_gateway=self.message_gateway,
                )

                next_num_example = next_offset + 1
                footer_msg = (
                    f"💡 *Dicas de navegação:*\n"
                    f"- Digite o número do imóvel (ex: *{next_num_example}*) para ver opções de agendamento de visita ou mais fotos. 📸\n"
                    f"- Digite *mais* para ver outras opções do seu perfil. 🔄\n"
                    f"- Digite *alertar* para receber alertas deste perfil. 🔔\n"
                    f"- Digite *reiniciar* para começar uma nova busca. 🔄"
                )
                await self.message_gateway.send_text(session.phone, footer_msg)
            else:
                no_more_msg = humanizer.get_no_more_results_phrase()
                await self.message_gateway.send_text(session.phone, no_more_msg)
            return False

        # Tenta interpretar como seleção numérica de imóvel
        num_match = re.match(r"^(\d+)\.?$", clean_text)
        if num_match:
            try:
                idx = int(num_match.group(1))
                if 1 <= idx <= len(session.results):
                    selected_item = session.results[idx - 1]
                    property_id = selected_item["id"]

                    await self.message_gateway.send_typing(session.phone, duration_ms=1500)
                    listing = await self.property_repo.find_by_id(property_id)

                    if not listing:
                        await self.message_gateway.send_text(
                            session.phone,
                            "Desculpe, não consegui carregar os detalhes desse imóvel no momento. 😅 Digite 'voltar' para tentar novamente.",
                        )
                        return False

                    session.selected_property_id = property_id
                    session.transition_to(ConversationStep.DETAIL)

                    limit = settings.max_photos_per_property
                    photos_to_send = listing.photos[:limit] if listing.photos else []
                    for photo in photos_to_send:
                        if photo:
                            try:
                                await self.message_gateway.send_image(
                                    session.phone, photo, f"Foto do imóvel Ref {listing.ref}"
                                )
                            except Exception as e:
                                logger.warning(
                                    "Falha ao enviar imagem do imóvel", url=photo, error=str(e)
                                )

                    detail_lines = [
                        f"🏡 *Detalhes do Imóvel — Ref: {listing.ref}*",
                        f"Tipo: {listing.property_type}",
                        f"Endereço: {listing.address}",
                        f"Bairro: {listing.neighborhood}",
                        f"Valor: {listing.value.formatted()}",
                    ]
                    if listing.fees:
                        detail_lines.append(f"Taxas (Condomínio/IPTU): {listing.fees.formatted()}")

                    if listing.features:
                        detail_lines.append("\n*Características:*")
                        for feat in listing.features:
                            detail_lines.append(f"- {feat}")

                    detail_lines.append(f"\nLink no site: {listing.url}")
                    
                    booking_part = (
                        "\nCom certeza posso te ajudar com isso! 😊 Clique no link abaixo para falar direto com um de nossos corretores no WhatsApp. Eles vão adorar te atender!\n\n"
                        f"https://wa.me/558836113000?text=Olá,%20gostaria%20de%20agendar%20uma%20visita%20para%20o%20imóvel%20Ref%20{listing.ref}\n\n"
                        "Digite 'voltar' para ver a lista de imóveis novamente, ou 'reiniciar' para fazer uma nova busca."
                    )
                    detail_lines.append(booking_part)

                    await self.message_gateway.send_text(session.phone, "\n".join(detail_lines))
                    return False
            except (ValueError, IndexError):
                pass

        unknown_msg = humanizer.get_unknown_command_phrase()
        await self.message_gateway.send_text(session.phone, unknown_msg)
        return False

