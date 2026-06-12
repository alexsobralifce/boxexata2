from src.application.use_cases.handlers.base_handler import BaseHandler
from src.domain.entities.session import Session, ConversationStep
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.shared.logger import logger


def _fmt_value(value: float) -> str:
    """Formata valor monetário em real brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _build_criteria_summary(session: Session) -> str:
    """Monta o resumo textual dos critérios de busca confirmados pelo cliente."""
    lines = ["✅ *Confirmando sua busca:*\n"]

    intent_label = session.intent or "Não informado"
    lines.append(f"- *Finalidade*: {intent_label}")

    tipo_label = session.property_type or "Não informado"
    lines.append(f"- *Tipo de imóvel*: {tipo_label}")

    if session.neighborhood:
        lines.append(f"- *Bairro*: {session.neighborhood}")
    elif session.reference_point:
        lines.append(f"- *Próximo a*: {session.reference_point}")
    else:
        lines.append("- *Localização*: Não informada")

    if session.max_value:
        lines.append(f"- *Valor máximo*: {_fmt_value(session.max_value)}")

    if session.bedrooms_min:
        lines.append(f"- *Quartos mínimos*: {session.bedrooms_min}")

    extras = []
    if session.parking:
        extras.append("Garagem")
    if session.pet_friendly:
        extras.append("Pet friendly")
    if session.furnished:
        extras.append("Mobiliado")
    if extras:
        lines.append(f"- *Extras*: {', '.join(extras)}")

    if session.move_deadline:
        deadline_map = {
            "urgente": "⚡ Urgente",
            "1 mes": "Até 1 mês",
            "3 meses": "Até 3 meses",
            "sem pressa": "Sem pressa",
        }
        lines.append(f"- *Prazo para mudança*: {deadline_map.get(session.move_deadline, session.move_deadline)}")

    lines.append("\nEstá correto? Responda *sim* para buscar ou *não* para corrigir os critérios.")
    return "\n".join(lines)


class ConfirmCriteriaHandler(BaseHandler):
    """Handler para a etapa CONFIRM_CRITERIA — exibe resumo e aguarda confirmação antes de buscar."""

    def __init__(self, message_gateway: IMessageGateway) -> None:
        self.message_gateway = message_gateway

    async def handle(self, session: Session, text: str) -> bool:
        clean_text = text.lower().strip()

        # Primeira vez nessa etapa: exibe resumo e aguarda resposta
        if not session.confirm_shown:
            session.confirm_shown = True
            summary = _build_criteria_summary(session)
            await self.message_gateway.send_text(session.phone, summary)
            return False

        # Cliente confirmou → avança para busca
        if clean_text in ("sim", "s", "isso", "correto", "certo", "ok", "pode", "pode buscar", "pode pesquisar", "confirmar", "confirmo"):
            logger.info("Cliente confirmou critérios de busca", phone=session.phone)
            session.confirmed_search = True
            session.transition_to(ConversationStep.PREFERENCES)
            return True  # Dispara a transição para PreferencesHandler buscar

        # Cliente quer corrigir → volta para coleta de preferências
        if clean_text in ("não", "nao", "n", "errado", "corrigir", "mudar", "alterar", "voltar"):
            session.transition_to(ConversationStep.PREFERENCES)
            await self.message_gateway.send_text(
                session.phone,
                "Tudo bem! Vamos ajustar. O que você gostaria de mudar? Pode me dizer o tipo, bairro, valor ou qualquer outra preferência. 😊",
            )
            # Reseta o flag de exibição para quando retornar
            session.confirm_shown = False
            return False

        # Resposta não reconhecida
        await self.message_gateway.send_text(
            session.phone,
            "Por favor, responda *sim* para confirmar a busca ou *não* para corrigir os critérios. 😊",
        )
        return False
