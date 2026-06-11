import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PhoneNumber:
    raw: str
    _normalized: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized = re.sub(r"\D", "", self.raw)
        if len(normalized) < 10:
            raise ValueError(f"Número de telefone inválido: {self.raw}")
        # Atribui ao atributo de leitura privada usando object.__setattr__ devido ao frozen=True
        object.__setattr__(self, "_normalized", normalized)

    @property
    def normalized(self) -> str:
        return self._normalized

    def whatsapp_jid(self) -> str:
        return f"{self.normalized}@s.whatsapp.net"
