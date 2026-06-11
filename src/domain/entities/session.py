from enum import Enum, auto
from typing import Any, Optional


class ConversationStep(Enum):
    START = auto()
    INTENT = auto()  # Locação ou Venda?
    PREFERENCES = auto()  # Tipo, Bairro, Valor
    SEARCHING = auto()
    SHOWING = auto()
    DETAIL = auto()


class Session:
    """Entidade que representa a sessão de conversa de um cliente."""

    def __init__(
        self,
        phone: str,
        step: ConversationStep = ConversationStep.START,
        client_name: Optional[str] = None,
        intent: Optional[str] = None,  # "Locação" | "Venda"
        property_type: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_value: Optional[float] = None,
        results: Optional[list[dict[str, Any]]] = None,
        result_offset: int = 0,
        message_count: int = 0,
        selected_property_id: Optional[str] = None,
        history: Optional[list[str]] = None,
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

    def update_preferences(
        self,
        intent: Optional[str] = None,
        property_type: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_value: Optional[float] = None,
        client_name: Optional[str] = None,
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
        self.step = ConversationStep.START
