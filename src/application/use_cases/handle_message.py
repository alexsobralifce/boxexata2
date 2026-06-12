import asyncio
from typing import Optional
from src.domain.entities.session import ConversationStep
from src.domain.repositories.i_session_store import ISessionStore
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.application.services.i_preference_extractor import IPreferenceExtractor
from src.domain.repositories.i_subscription_store import ISubscriptionStore
from src.domain.repositories.i_message_log_repository import IMessageLogRepository
from src.domain.entities.message_log import MessageLog
from src.application.use_cases.handlers.start_handler import StartHandler
from src.application.use_cases.handlers.intent_handler import IntentHandler
from src.application.use_cases.handlers.preferences_handler import PreferencesHandler
from src.application.use_cases.handlers.confirm_criteria_handler import ConfirmCriteriaHandler
from src.application.use_cases.handlers.showing_handler import ShowingHandler
from src.application.use_cases.handlers.detail_handler import DetailHandler
from src.application.use_cases.handlers.farewell_handler import FarewellHandler
from src.shared.logger import logger


class HandleMessageUseCase:
    """Orquestrador principal do fluxo de mensagens do ExataBot."""

    def __init__(
        self,
        session_store: ISessionStore,
        property_repo: IPropertyRepository,
        message_gateway: IMessageGateway,
        extractor: IPreferenceExtractor,
        subscription_store: ISubscriptionStore,
        log_repo: Optional[IMessageLogRepository] = None,
    ) -> None:
        self._session_store = session_store
        self._property_repo = property_repo
        self._message_gateway = message_gateway
        self._extractor = extractor
        self._subscription_store = subscription_store
        self._log_repo = log_repo

        self._handlers = {
            ConversationStep.START: StartHandler(message_gateway),
            ConversationStep.INTENT: IntentHandler(message_gateway),
            ConversationStep.PREFERENCES: PreferencesHandler(
                property_repo, message_gateway, extractor
            ),
            ConversationStep.CONFIRM_CRITERIA: ConfirmCriteriaHandler(message_gateway),
            ConversationStep.SHOWING: ShowingHandler(
                property_repo, message_gateway, subscription_store
            ),
            ConversationStep.DETAIL: DetailHandler(message_gateway, property_repo),
            ConversationStep.FAREWELL: FarewellHandler(message_gateway),
        }

    def _is_within_business_hours(self) -> bool:
        # Bot responde 24/7 (qualquer hora)
        return True

    async def execute(self, phone: str, text: str, bypass_hours: bool = False) -> None:
        """Processa uma mensagem recebida de um remetente, gerenciando a máquina de estados e enviando respostas."""
        logger.info("Executando caso de uso de tratamento de mensagem", phone=phone, text=text)

        # 1. Verifica horário de atendimento
        if not bypass_hours and not self._is_within_business_hours():
            logger.info("Fora do horário de atendimento. Enviando mensagem padrão.", phone=phone)
            await self._message_gateway.send_text(
                phone,
                "Olá! No momento estamos fora do nosso horário de atendimento (Segunda a Sexta, das 08h às 18h). "
                "Deixe sua mensagem e responderemos assim que retornarmos!",
            )
            return

        # 2. Busca ou cria a sessão do cliente
        session = await self._session_store.get_or_create(phone)
        session.increment_messages()

        # Adiciona a mensagem recebida ao histórico
        session.history.append(f"Cliente: {text}")
        session.history = session.history[-20:]

        # 2b. Loga a mensagem de entrada (se o repositório estiver ativo)
        if self._log_repo:
            step_str = session.step.name if hasattr(session.step, "name") else str(session.step)
            incoming_log = MessageLog(
                phone=phone,
                direction="in",
                text=text,
                step=step_str,
                intent=session.intent,
            )
            asyncio.create_task(self._log_repo.save(incoming_log))

        # 3. Executa a extração de preferências caso a conversa não esteja nas etapas de paginação/detalhe
        if session.step not in (ConversationStep.SHOWING, ConversationStep.DETAIL):
            extracted = await self._extractor.extract(
                text, [line for line in session.history if "Cliente:" in line]
            )
            session.update_preferences(**extracted)

        # 4. Loop da máquina de estados
        max_transitions = 5
        transition_count = 0

        while transition_count < max_transitions:
            transition_count += 1
            current_step = session.step

            handler = self._handlers.get(current_step)
            if not handler:
                logger.error("Nenhum handler registrado para o estado", step=current_step)
                break

            logger.info(
                "Processando estado da conversa",
                phone=phone,
                step=current_step,
                transition_count=transition_count,
            )

            should_continue = await handler.handle(session, text)

            # Se o estado não mudou ou se o handler determinou que não devemos prosseguir de imediato, interrompe
            if session.step == current_step or not should_continue:
                break

        # 5. Salva o estado atualizado da sessão
        await self._session_store.save(session)
        logger.info("Sessão salva com sucesso", phone=phone, step=session.step)
