from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.shared.logger import logger


class PreferencesHandler(BaseHandler):
    """Handler para a etapa PREFERENCES da conversa."""

    def __init__(
        self, property_repo: IPropertyRepository, message_gateway: IMessageGateway
    ) -> None:
        self.property_repo = property_repo
        self.message_gateway = message_gateway

    async def handle(self, session: Session, text: str) -> bool:
        # Se falta preencher o tipo
        if not session.property_type:
            await self.message_gateway.send_text(
                session.phone,
                "Qual tipo de imóvel você procura? (Ex: casa, apartamento, quitinete, etc.)",
            )
            return False

        # Se falta preencher o bairro
        if not session.neighborhood:
            await self.message_gateway.send_text(
                session.phone,
                f"Entendi! E em qual bairro de Sobral você busca {session.property_type.lower()}? (Ex: Centro, Derby, Junco, Renato Parente, etc.)",
            )
            return False

        # Se temos as preferências mínimas (tipo e bairro), realiza a busca
        logger.info(
            "Preferências completas. Iniciando busca no repositório de imóveis.",
            phone=session.phone,
            intent=session.intent,
            property_type=session.property_type,
            neighborhood=session.neighborhood,
            max_value=session.max_value,
        )

        try:
            await self.message_gateway.send_typing(session.phone, duration_ms=2000)
            results = await self.property_repo.find_by_preferences(session)
        except Exception as e:
            logger.error("Erro ao buscar imóveis no repositório", error=str(e))
            await self.message_gateway.send_text(
                session.phone,
                "Desculpe, tive um problema ao pesquisar no site da Exata Serviços no momento. Por favor, tente novamente em alguns instantes.",
            )
            return False

        if not results:
            intent_label = "alugar" if session.intent == "Locação" else "comprar"
            valor_label = (
                f" com valor até R$ {session.max_value:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
                if session.max_value
                else ""
            )
            msg = (
                f"Não encontrei nenhuma opção de {session.property_type.lower()} para {intent_label} "
                f"no bairro {session.neighborhood}{valor_label} no momento.\n\n"
                "Quer que eu te avise assim que novos imóveis com esse perfil surgirem no site? Digite **alertar** para ativar.\n"
                "Se preferir fazer uma nova busca com outros critérios, digite **começar**."
            )
            session.results = []
            session.result_offset = 0
            session.transition_to(ConversationStep.SHOWING)
            await self.message_gateway.send_text(session.phone, msg)
            return False

        # Armazena os resultados serializados na sessão
        session.results = [r.to_dict() for r in results]
        session.result_offset = 0
        session.transition_to(ConversationStep.SHOWING)

        # Exibe os primeiros 3 imóveis
        page_size = 3
        slice_results = results[:page_size]

        response_lines = ["Encontrei esses imóveis que encaixam nas suas preferências:\n"]
        for idx, item in enumerate(slice_results):
            num = idx + 1
            price_fmt = item.value.formatted()
            response_lines.append(
                f"*{num}. {item.property_type} no {item.neighborhood}*\n"
                f"Valor: {price_fmt}\n"
                f"Ref: {item.ref} | Endereço: {item.address}\n"
                f"Link: {item.url}\n"
            )

        response_lines.append(
            "Digite o número do imóvel para ver mais detalhes (ex: 1, 2, 3), 'mais' para ver outros, 'alertar' para receber avisos de novas opções, ou 'reiniciar' para começar de novo."
        )

        await self.message_gateway.send_text(session.phone, "\n".join(response_lines))
        return False
