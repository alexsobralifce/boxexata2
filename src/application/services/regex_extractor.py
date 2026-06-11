import re
from typing import Any, Optional
from src.application.services.i_preference_extractor import IPreferenceExtractor


SOBRAL_NEIGHBORHOODS = [
    "centro",
    "derby",
    "pedrinhas",
    "junco",
    "campo dos velhos",
    "cohab i",
    "cohab ii",
    "cohab iii",
    "cohab",
    "domingos olímpio",
    "domingos olimpio",
    "renato parente",
    "cidade gerardo cristino",
    "sinhá sabóia",
    "sinha saboia",
    "betânia",
    "betania",
    "alto do cristo",
    "recanto",
    "terrenos novos",
]


class RegexPreferenceExtractor(IPreferenceExtractor):
    """Extração de preferências a partir de expressões regulares."""

    async def extract(self, text: str, history: list[str]) -> dict[str, Any]:
        """Extrai as preferências contidas no texto."""
        nome = self.extrair_nome(text)
        valor_max = self.extrair_valor_max(text)
        bairro = self.extrair_bairro(text)
        tipo = self.extrair_tipo(text)
        intent = self.extrair_intent(text)

        result: dict[str, Any] = {}
        if nome:
            result["client_name"] = nome
        if valor_max is not None:
            result["max_value"] = valor_max
        if bairro:
            result["neighborhood"] = bairro.title()
        if tipo:
            result["property_type"] = tipo
        if intent:
            result["intent"] = intent

        return result

    def extrair_nome(self, text: str) -> Optional[str]:
        """Detecta padrões como 'me chamo X', 'meu nome é X', 'sou o X', 'sou a X'."""
        patterns = [
            r"(?:me chamo|meu nome é|sou o|sou a)\s+([A-Za-zÀ-ÖØ-öø-ÿ]+)",
            r"(?:oi|olá|ola|bom dia|boa tarde|boa noite),\s+([A-Za-zÀ-ÖØ-öø-ÿ]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def extrair_valor_max(self, text: str) -> Optional[float]:
        """Extrai o valor máximo da busca (R$ 1.500, 1500, 1.5 mil, etc.)."""
        # Trata formato "X mil"
        mil_match = re.search(r"(\d+(?:[.,]\d+)?)\s*mil", text, re.IGNORECASE)
        if mil_match:
            val = float(mil_match.group(1).replace(",", "."))
            return val * 1000.0

        # Encontra todos os números na string
        pattern = r"\b\d+(?:[.,]\d+)*\b"
        matches = re.finditer(pattern, text)
        candidates = []
        for m in matches:
            val_str = m.group(0)
            clean = val_str.replace(".", "").replace(",", ".")
            try:
                val = float(clean)
                # Filtra anos comuns e números fora do range plausível de imóvel
                if 100 < val < 1000000 and val not in (2024, 2025, 2026):
                    candidates.append(val)
            except ValueError:
                continue
        if candidates:
            return candidates[0]
        return None

    def extrair_bairro(self, text: str) -> Optional[str]:
        """Busca correspondência com a lista de bairros conhecidos de Sobral/CE."""
        text_lower = text.lower()
        for neighborhood in SOBRAL_NEIGHBORHOODS:
            if neighborhood in text_lower:
                return neighborhood
        return None

    def extrair_tipo(self, text: str) -> Optional[str]:
        """Busca correspondência com tipos de imóveis."""
        text_lower = text.lower()
        if "apartamento" in text_lower or "apto" in text_lower or "apartamentos" in text_lower:
            return "Apartamento"
        if "quitinete" in text_lower or "kitnet" in text_lower or "kitinete" in text_lower:
            return "Quitinete"
        if "casa" in text_lower or "casas" in text_lower:
            return "Casa"
        if "galpão" in text_lower or "galpao" in text_lower:
            return "Galpão"
        if "ponto" in text_lower or "ponto comercial" in text_lower:
            return "Ponto comercial"
        if "sala" in text_lower or "salas" in text_lower:
            return "Salas"
        if "sítio" in text_lower or "sitio" in text_lower:
            return "Sítio"
        if "terreno" in text_lower:
            return "Terreno murado"
        if "lote" in text_lower:
            return "Lote"
        return None

    def extrair_intent(self, text: str) -> Optional[str]:
        """Identifica a finalidade (Locação ou Venda)."""
        text_lower = text.lower()
        if (
            "alugar" in text_lower
            or "aluguel" in text_lower
            or "locação" in text_lower
            or "locacao" in text_lower
        ):
            return "Locação"
        if "comprar" in text_lower or "venda" in text_lower or "vender" in text_lower:
            return "Venda"
        return None
