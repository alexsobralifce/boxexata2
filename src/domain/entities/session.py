from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Optional


class ConversationStep(Enum):
    START = auto()
    INTENT = auto()           # Locação, Venda, Anunciar, FAQ, Corretor
    PREFERENCES = auto()      # Tipo, Bairro, Valor, Quartos...
    CONFIRM_CRITERIA = auto() # Confirmação dos critérios antes de buscar
    SEARCHING = auto()
    SHOWING = auto()
    DETAIL = auto()
    FAQ = auto()              # Dúvidas financeiras/documentais
    OWNER_ONBOARDING = auto() # Proprietário que quer anunciar imóvel
    HANDOFF = auto()          # Transferência para corretor humano
    FAREWELL = auto()         # Encerramento após alerta — "posso ajudar em mais algo?"


class Session:
    """Entidade que representa a sessão de conversa de um cliente."""

    def __init__(
        self,
        phone: str,
        step: ConversationStep = ConversationStep.START,
        client_name: Optional[str] = None,
        intent: Optional[str] = None,      # "Locação" | "Venda"
        property_type: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_value: Optional[float] = None,
        results: Optional[list[dict[str, Any]]] = None,
        result_offset: int = 0,
        message_count: int = 0,
        selected_property_id: Optional[str] = None,
        history: Optional[list[str]] = None,
        reference_point: Optional[str] = None,
        # --- Campos de qualificação avançada (Fase 1+) ---
        bedrooms_min: Optional[int] = None,
        parking: Optional[bool] = None,
        pet_friendly: Optional[bool] = None,
        furnished: Optional[bool] = None,
        move_deadline: Optional[str] = None,   # "urgente" | "1 mês" | "3 meses" | "sem pressa"
        persona: Optional[str] = None,         # "buyer" | "renter" | "owner" | "faq" | "visitor"
        lead_score: int = 0,
        handoff_reason: Optional[str] = None,
        # --- Campos de follow-up por silêncio (Fase 4) ---
        last_activity_at: Optional[datetime] = None,
        followup_count: int = 0,
        # --- Campos do proprietário (Fase 2) ---
        owner_property_type: Optional[str] = None,
        owner_neighborhood: Optional[str] = None,
        owner_value: Optional[str] = None,
        owner_availability: Optional[str] = None,
        owner_step: int = 0,  # 0=tipo, 1=endereço, 2=valor, 3=disponibilidade
    ) -> None:
        self.phone = phone
        self.step = step
        self.client_name = client_name
        self.intent = intent
        self.property_type = property_type
        self.neighborhood = neighborhood
        self.max_value = max_value
        self.results = results if results is not None else []
        self.result_offset = result_offset
        self.message_count = message_count
        self.selected_property_id = selected_property_id
        self.history = history if history is not None else []
        self.reference_point = reference_point
        # Qualificação avançada
        self.bedrooms_min = bedrooms_min
        self.parking = parking
        self.pet_friendly = pet_friendly
        self.furnished = furnished
        self.move_deadline = move_deadline
        self.persona = persona
        self.lead_score = lead_score
        self.handoff_reason = handoff_reason
        # Follow-up por silêncio
        self.last_activity_at = last_activity_at or datetime.now(timezone.utc)
        self.followup_count = followup_count
        # Dados do proprietário
        self.owner_property_type = owner_property_type
        self.owner_neighborhood = owner_neighborhood
        self.owner_value = owner_value
        self.owner_availability = owner_availability
        self.owner_step = owner_step

    def update_preferences(
        self,
        intent: Optional[str] = None,
        property_type: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_value: Optional[float] = None,
        client_name: Optional[str] = None,
        reference_point: Optional[str] = None,
        bedrooms_min: Optional[int] = None,
        parking: Optional[bool] = None,
        pet_friendly: Optional[bool] = None,
        furnished: Optional[bool] = None,
        move_deadline: Optional[str] = None,
    ) -> None:
        """Atualiza os campos de preferências coletados do cliente."""
        if intent is not None:
            self.intent = intent
        if property_type is not None:
            self.property_type = property_type
        if neighborhood is not None:
            self.neighborhood = neighborhood
        if max_value is not None:
            self.max_value = max_value
        if client_name is not None:
            self.client_name = client_name
        if reference_point is not None:
            self.reference_point = reference_point
        if bedrooms_min is not None:
            self.bedrooms_min = bedrooms_min
        if parking is not None:
            self.parking = parking
        if pet_friendly is not None:
            self.pet_friendly = pet_friendly
        if furnished is not None:
            self.furnished = furnished
        if move_deadline is not None:
            self.move_deadline = move_deadline
        # Atualiza timestamp de atividade sempre que preferências são atualizadas
        self.last_activity_at = datetime.now(timezone.utc)

    def transition_to(self, step: ConversationStep) -> None:
        """Altera a etapa atual do fluxo da conversa."""
        self.step = step

    def increment_messages(self) -> None:
        """Registra a contagem de interações."""
        self.message_count += 1

    def reset_search(self) -> None:
        """Reinicia os parâmetros de busca para novas consultas."""
        self.intent = None
        self.property_type = None
        self.neighborhood = None
        self.max_value = None
        self.results = []
        self.result_offset = 0
        self.selected_property_id = None
        self.history = []
        self.reference_point = None
        self.bedrooms_min = None
        self.parking = None
        self.pet_friendly = None
        self.furnished = None
        self.move_deadline = None
        self.persona = None
        self.lead_score = 0
        self.handoff_reason = None
        self.step = ConversationStep.START
