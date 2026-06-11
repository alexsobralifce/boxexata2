import re
from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.shared.config import settings
from src.shared.logger import logger


class ShowingHandler(BaseHandler):
    """Handler para a etapa SHOWING (exibição de resultados e seleção)."""

    def __init__(self, property_repo: IPropertyRepository, message_gateway: IMessageGateway) -> None:
        self.property_repo = property_repo
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

        # Comando "mais" ou "outro"
        if clean_text in ("mais", "outro", "outros", "mais resultados", "proxima", "próxima"):
            page_size = settings.results_page_size
            next_offset = session.result_offset + page_size

            if next_offset < len(session.results):
                session.result_offset = next_offset
                slice_results = session.results[next_offset : next_offset + page_size]

                response_lines = [
                    "Aqui estão mais algumas opções:\n"
                ]
                for idx, item in enumerate(slice_results):
                    num = next_offset + idx + 1
                    price = item.get("value", 0.0)
                    price_fmt = f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    response_lines.append(
                        f"*{num}. {item.get('property_type')} no {item.get('neighborhood')}*\n"
                        f"Valor: {price_fmt}\n"
                        f"Ref: {item.get('ref')} | Endereço: {item.get('address')}\n"
                        f"Link: {item.get('url')}\n"
                    )

                next_num_example = next_offset + 1
                response_lines.append(
                    f"Digite o número do imóvel para ver mais detalhes (ex: {next_num_example}), 'mais' para ver outros, ou 'reiniciar' para começar de novo."
                )
                await self.message_gateway.send_text(session.phone, "\n".join(response_lines))
            else:
                await self.message_gateway.send_text(
                    session.phone,
                    "Não encontrei mais imóveis com essas preferências no site. Digite 'reiniciar' para fazer uma nova busca."
                )
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
                            "Desculpe, não consegui carregar os detalhes desse imóvel no momento. Digite 'voltar' para tentar novamente."
                        )
                        return False

                    session.selected_property_id = property_id
                    session.transition_to(ConversationStep.DETAIL)

                    limit = settings.max_photos_per_property
                    photos_to_send = listing.photos[:limit] if listing.photos else []
                    for photo in photos_to_send:
                        if photo:
                            try:
                                await self.message_gateway.send_image(session.phone, photo, f"Foto do imóvel Ref {listing.ref}")
                            except Exception as e:
                                logger.warning("Falha ao enviar imagem do imóvel", url=photo, error=str(e))

                    detail_lines = [
                        f"🏡 *Detalhes do Imóvel — Ref: {listing.ref}*",
                        f"Tipo: {listing.property_type}",
                        f"Endereço: {listing.address}",
                        f"Bairro: {listing.neighborhood}",
                        f"Valor: {listing.value.formatted()}"
                    ]
                    if listing.fees:
                        detail_lines.append(f"Taxas (Condomínio/IPTU): {listing.fees.formatted()}")

                    if listing.features:
                        detail_lines.append("\n*Características:*")
                        for feat in listing.features:
                            detail_lines.append(f"- {feat}")

                    detail_lines.append(f"\nLink no site: {listing.url}")
                    detail_lines.append(
                        "\nSe quiser agendar uma visita para este imóvel, clique no link abaixo para falar com um de nossos corretores:\n"
                        f"https://wa.me/558836113000?text=Olá,%20gostaria%20de%20agendar%20uma%20visita%20para%20o%20imóvel%20Ref%20{listing.ref}"
                        "\n\nDigite 'voltar' para ver a lista de imóveis novamente, ou 'reiniciar' para fazer uma nova busca."
                    )

                    await self.message_gateway.send_text(session.phone, "\n".join(detail_lines))
                    return False
            except (ValueError, IndexError):
                pass

        await self.message_gateway.send_text(
            session.phone,
            "Não entendi. Por favor, digite o número do imóvel desejado (ex: 1, 2, 3), 'mais' para ver mais opções, ou 'reiniciar' para começar uma nova busca."
        )
        return False
