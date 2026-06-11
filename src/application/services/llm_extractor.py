import json
from typing import Any, Optional
from openai import AsyncOpenAI

from src.application.services.i_preference_extractor import IPreferenceExtractor
from src.application.services.regex_extractor import RegexPreferenceExtractor
from src.shared.circuit_breaker import CircuitBreaker
from src.shared.config import settings
from src.shared.logger import logger


class LLMPreferenceExtractor(IPreferenceExtractor):
    """Extração de preferências via LLM (OpenAI ou DeepSeek) com fallback para Regex."""

    def __init__(
        self,
        fallback_extractor: Optional[IPreferenceExtractor] = None,
        client: Optional[AsyncOpenAI] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.fallback = fallback_extractor or RegexPreferenceExtractor()
        self._client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=3, recovery_timeout=60.0
        )

    def _get_client(self) -> Optional[AsyncOpenAI]:
        if self._client is not None:
            return self._client

        provider = settings.llm_provider
        api_key = ""
        base_url = None

        if provider == "openai":
            api_key = settings.openai_api_key
        elif provider == "deepseek":
            api_key = settings.deepseek_api_key
            base_url = "https://api.deepseek.com"
        else:
            return None

        if not api_key:
            logger.warning(
                "Provedor de LLM configurado mas a chave de API correspondente está vazia.",
                provider=provider,
            )
            return None

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return self._client

    async def extract(self, text: str, history: list[str]) -> dict[str, Any]:
        """Extrai as preferências usando o LLM selecionado, ou cai para Regex em caso de falha/inexistência do LLM."""
        client = self._get_client()
        if not client:
            logger.info("Nenhum cliente LLM configurado. Usando extrator de fallback (Regex).")
            return await self.fallback.extract(text, history)

        provider = settings.llm_provider
        model = "gpt-4o-mini" if provider == "openai" else "deepseek-chat"

        # Formata o histórico de mensagens recentes (últimas 6)
        recent_history = history[-6:] if history else []
        history_str = "\n".join(recent_history)

        system_prompt = (
            "Você é o motor de processamento de linguagem natural do ExataBot, um robô de atendimento imobiliário em Sobral/CE.\n"
            "Sua tarefa é ler a mensagem do cliente e o histórico de mensagens recentes e extrair as preferências de busca do cliente.\n\n"
            "Retorne APENAS um objeto JSON válido contendo exatamente as seguintes chaves:\n"
            "{\n"
            '  "finalidade": "Locação"|"Venda"|null,\n'
            '  "tipo": "casa"|"apartamento"|"kitnet"|null,\n'
            '  "bairro": string|null,\n'
            '  "cidade": string|null,\n'
            '  "valor_max": number|null,\n'
            '  "quartos_min": number|null,\n'
            '  "pet_friendly": boolean|null,\n'
            '  "garagem": boolean|null,\n'
            '  "mobiliado": boolean|null,\n'
            '  "nome_cliente": string|null\n'
            "}\n\n"
            "Regras importantes:\n"
            "- Se o cliente disser seu próprio nome (ex: 'Me chamo Francisco', 'Oi, sou a Ana'), extraia para 'nome_cliente'.\n"
            "- Identifique bairros conhecidos de Sobral/CE (ex: Centro, Derby, Pedrinhas, Junco, Renato Parente, etc.). Se encontrar algum, coloque em 'bairro'.\n"
            "- Para 'tipo', padronize: se for kitnet/quitinete, retorne 'kitnet'. Se for casa, 'casa'. Se for apartamento/apto, 'apartamento'.\n"
            "- Se o cliente falar sobre aluguel, alugar, locar, retorne 'Locação' em 'finalidade'. Se falar sobre compra, comprar, venda, retorne 'Venda'.\n"
            "- 'valor_max' deve ser um número representando o limite de preço (ex: 'até R$ 1200' -> 1200.0, 'até 1.5 mil' -> 1500.0).\n"
            "- Não invente informações. Se uma chave não estiver presente na mensagem ou histórico, retorne null."
        )

        user_content = (
            f"Histórico de conversas recente:\n{history_str}\n\nNova mensagem do cliente:\n{text}"
        )

        try:
            logger.info("Realizando chamada para LLM", provider=provider, model=model)

            async def _make_api_call() -> Any:
                assert client is not None
                return await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    timeout=10.0,
                )

            response = await self.circuit_breaker.call(_make_api_call)
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Resposta vazia do LLM")

            data = json.loads(content)
            logger.info("Dados extraídos com sucesso pelo LLM", extraction_result=data)

            extracted: dict[str, Any] = {}
            if data.get("nome_cliente"):
                extracted["client_name"] = data["nome_cliente"]
            if data.get("finalidade"):
                extracted["intent"] = data["finalidade"]
            if data.get("tipo"):
                tipo_normalizado = data["tipo"].lower()
                if "casa" in tipo_normalizado:
                    extracted["property_type"] = "Casa"
                elif "apartamento" in tipo_normalizado:
                    extracted["property_type"] = "Apartamento"
                elif "kitnet" in tipo_normalizado or "quitinete" in tipo_normalizado:
                    extracted["property_type"] = "Quitinete"
                else:
                    extracted["property_type"] = data["tipo"].title()
            if data.get("bairro"):
                extracted["neighborhood"] = data["bairro"].title()
            if data.get("valor_max") is not None:
                try:
                    extracted["max_value"] = float(data["valor_max"])
                except (ValueError, TypeError):
                    pass

            return extracted

        except Exception as e:
            logger.error(
                "Falha ao extrair preferências com LLM. Utilizando fallback para Regex.",
                error=str(e),
            )
            return await self.fallback.extract(text, history)
