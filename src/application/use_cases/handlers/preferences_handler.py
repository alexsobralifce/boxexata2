from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.application.services.i_preference_extractor import IPreferenceExtractor
from src.application.services.property_presenter import send_property_cards
from src.shared.logger import logger


class PreferencesHandler(BaseHandler):
    """Handler para a etapa PREFERENCES da conversa."""

    def __init__(
        self,
        property_repo: IPropertyRepository,
        message_gateway: IMessageGateway,
        extractor: IPreferenceExtractor,
    ) -> None:
        self.property_repo = property_repo
        self.message_gateway = message_gateway
        self.extractor = extractor

    async def handle(self, session: Session, text: str) -> bool:
        # Se falta preencher o tipo
        if not session.property_type:
            await self.message_gateway.send_text(
                session.phone,
                "Qual tipo de imóvel você procura? 🏡 (Ex: casa, apartamento, quitinete, etc.)",
            )
            return False

        # Se falta preencher o bairro/localização
        if not session.neighborhood and not session.reference_point:
            await self.message_gateway.send_text(
                session.phone,
                f"Entendi! E em qual bairro ou ponto de referência em Sobral você busca {session.property_type.lower()}? 📍 (Ex: Centro, Derby, perto da UFC, próximo ao Shopping, etc.)",
            )
            return False

        # Se temos as preferências mínimas (tipo e local/bairro), realiza a busca
        logger.info(
            "Preferências completas. Iniciando busca no repositório de imóveis.",
            phone=session.phone,
            intent=session.intent,
            property_type=session.property_type,
            neighborhood=session.neighborhood,
            reference_point=session.reference_point,
            max_value=session.max_value,
        )

        try:
            await self.message_gateway.send_typing(session.phone, duration_ms=2000)
            results = await self.property_repo.find_by_preferences(session)
        except Exception as e:
            logger.error("Erro ao buscar imóveis no repositório", error=str(e))
            await self.message_gateway.send_text(
                session.phone,
                "Desculpe, tive um problema ao pesquisar no site da Exata Serviços no momento. 😔 Por favor, tente novamente em alguns instantes.",
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
            location_label = f"no bairro {session.neighborhood}" if session.neighborhood else f"próximo a {session.reference_point}"
            msg = (
                f"Não encontrei nenhuma opção de {session.property_type.lower()} para {intent_label} "
                f"{location_label}{valor_label} no momento. 😔\n\n"
                "Quer que eu te avise assim que novos imóveis com esse perfil surgirem no site? Digite **alertar** para ativar. 🔔\n"
                "Se preferir fazer uma nova busca com outros critérios, digite **começar**."
            )
            session.results = []
            session.result_offset = 0
            session.transition_to(ConversationStep.SHOWING)
            await self.message_gateway.send_text(session.phone, msg)
            return False

        # Armazena os resultados serializados na sessão
        results_dicts = [r.to_dict() for r in results]

        # Se o usuário especificou ponto de referência, rankeamos via LLM
        if session.reference_point and hasattr(self.extractor, "rank_properties_by_proximity"):
            results_dicts = await self.extractor.rank_properties_by_proximity(
                session.reference_point, results_dicts
            )

        session.results = results_dicts
        session.result_offset = 0
        session.transition_to(ConversationStep.SHOWING)

        # Exibe os primeiros 3 imóveis
        page_size = 3
        slice_results = results_dicts[:page_size]

        await self.message_gateway.send_text(
            session.phone,
            "Encontrei esses imóveis que encaixam nas suas preferências! 🏡✨👇"
        )

        # Envia os cartões (imagem + texto detalhado)
        await send_property_cards(
            phone=session.phone,
            slice_results=slice_results,
            start_num=1,
            property_repo=self.property_repo,
            message_gateway=self.message_gateway,
        )

        footer_msg = (
            "💡 *Dicas de navegação:*\n"
            "- Digite o número do imóvel (ex: *1*, *2*, *3*) para ver opções de agendamento de visita ou mais fotos. 📸\n"
            "- Digite *mais* para ver outras opções do seu perfil. 🔄\n"
            "- Digite *alertar* para receber avisos automáticos de novas opções deste perfil. 🔔\n"
            "- Digite *reiniciar* para começar uma nova busca do zero. 🔄"
        )
        await self.message_gateway.send_text(session.phone, footer_msg)
        return False
