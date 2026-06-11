from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_subscription_store import ISubscriptionStore
from src.shared.logger import logger


class NotifyNewListingsUseCase:
    """Caso de uso para checer e notificar usuários sobre novos imóveis correspondentes às suas assinaturas."""

    def __init__(
        self,
        property_repo: IPropertyRepository,
        message_gateway: IMessageGateway,
        subscription_store: ISubscriptionStore,
    ) -> None:
        self.property_repo = property_repo
        self.message_gateway = message_gateway
        self.subscription_store = subscription_store

    async def execute(self) -> None:
        """Executa a rotina periódica de busca e envio de alertas."""
        logger.info("Iniciando verificação periódica de novos imóveis para alertas")
        subscriptions = await self.subscription_store.list_all()
        if not subscriptions:
            logger.info("Nenhuma assinatura de alerta ativa encontrada")
            return

        logger.info(f"Processando {len(subscriptions)} assinaturas de alerta")

        for sub in subscriptions:
            try:
                # Cria uma sessão fake temporária para realizar a query no repositório
                query_session = Session(
                    phone=sub.phone,
                    step=ConversationStep.PREFERENCES,
                    intent=sub.intent,
                    property_type=sub.property_type,
                    neighborhood=sub.neighborhood,
                    max_value=sub.max_value,
                )

                # Busca imóveis correspondentes
                listings = await self.property_repo.find_by_preferences(query_session)

                # Filtra apenas os imóveis que dão match com a assinatura
                matched_listings = [listing for listing in listings if sub.matches(listing)]

                new_listings = []
                for listing in matched_listings:
                    already_notified = await self.subscription_store.is_notified(
                        sub.phone, listing.id
                    )
                    if not already_notified:
                        new_listings.append(listing)

                if new_listings:
                    logger.info(
                        "Encontrados novos imóveis para o assinante",
                        phone=sub.phone,
                        count=len(new_listings),
                        criteria={"type": sub.property_type, "neigh": sub.neighborhood},
                    )

                    for listing in new_listings:
                        # Envia foto se disponível
                        if listing.photos:
                            try:
                                await self.message_gateway.send_image(
                                    sub.phone,
                                    listing.photos[0],
                                    f"Nova opção de {listing.property_type.lower()} no bairro {listing.neighborhood}!",
                                )
                            except Exception as e:
                                logger.warning(
                                    "Falha ao enviar foto do alerta",
                                    phone=sub.phone,
                                    url=listing.photos[0],
                                    error=str(e),
                                )

                        price_fmt = listing.value.formatted()
                        alert_msg = (
                            f"🔔 *Alerta de Novo Imóvel!*\n\n"
                            f"Acaba de surgir uma nova opção que combina com suas preferências:\n\n"
                            f"🏡 *{listing.property_type} no {listing.neighborhood}*\n"
                            f"Valor: {price_fmt}\n"
                            f"Endereço: {listing.address}\n"
                            f"Ref: {listing.ref}\n"
                            f"Link: {listing.url}\n\n"
                            f"Quer agendar uma visita? Clique no link abaixo para falar com nossos corretores:\n"
                            f"https://wa.me/558836113000?text=Olá,%20gostaria%20de%20saber%20mais%20sobre%20o%20imóvel%20Ref%20{listing.ref}"
                        )

                        await self.message_gateway.send_text(sub.phone, alert_msg)

                        # Marca como notificado
                        await self.subscription_store.mark_notified(sub.phone, listing.id)

            except Exception as e:
                logger.error(
                    "Erro ao processar assinatura de alertas",
                    phone=sub.phone,
                    error=str(e),
                )
