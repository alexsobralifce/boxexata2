from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    amount: float

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Valor não pode ser negativo.")

    def is_within(self, max_value: "Money") -> bool:
        return self.amount <= max_value.amount

    def formatted(self) -> str:
        # Formata para padrão brasileiro: R$ 1.500,00
        # Usando substituição simples para evitar problemas de locale do sistema
        formatted_val = f"R$ {self.amount:,.2f}"
        return formatted_val.replace(",", "X").replace(".", ",").replace("X", ".")
