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
            '  "prazo_mudanca": "urgente"|"1 mes"|"3 meses"|"sem pressa"|null,\n'
            '  "nome_cliente": string|null,\n'
            '  "ponto_referencia": string|null\n'
            "}\n\n"
            "Regras importantes:\n"
            "- Se o cliente disser seu próprio nome (ex: 'Me chamo Francisco', 'Oi, sou a Ana'), extraia para 'nome_cliente'.\n"
            "- Identifique bairros conhecidos de Sobral/CE (ex: Centro, Derby, Pedrinhas, Junco, Renato Parente, etc.). Se encontrar algum, coloque em 'bairro'.\n"
            "- Se o cliente colocar um ponto de referência onde ele quer o imóvel ao invés de um bairro (ou em conjunto com o bairro) (ex: 'perto da UFC', 'próximo ao Shopping Sobral', 'perto da Santa Casa', 'próximo à catedral', etc.), identifique esse ponto de referência e coloque em 'ponto_referencia'. Remova preposições como 'perto de', 'próximo a', retendo apenas a entidade (ex: 'UFC', 'Shopping Sobral', 'Santa Casa').\n"
            "- Para 'tipo', padronize: se for kitnet/quitinete, retorne 'kitnet'. Se for casa, 'casa'. Se for apartamento/apto, 'apartamento'.\n"
            "- Se o cliente falar sobre aluguel, alugar, locar, retorne 'Locação' em 'finalidade'. Se falar sobre compra, comprar, venda, retorne 'Venda'.\n"
            "- 'valor_max' deve ser um número representando o limite de preço (ex: 'até R$ 1200' -> 1200.0, 'até 1.5 mil' -> 1500.0).\n"
            "- 'quartos_min' deve ser o número mínimo de quartos desejado (ex: '2 quartos' -> 2, 'pelo menos 3 quartos' -> 3).\n"
            "- 'prazo_mudanca': se o cliente mencionar urgência ('preciso já', 'para logo', 'semana que vem', 'urgente') retorne 'urgente'. Se falar em 1 mês retorne '1 mes'. Se falar em 2-3 meses retorne '3 meses'. Se sem pressa retorne 'sem pressa'.\n"
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
            if data.get("ponto_referencia"):
                extracted["reference_point"] = data["ponto_referencia"]
            if data.get("valor_max") is not None:
                try:
                    extracted["max_value"] = float(data["valor_max"])
                except (ValueError, TypeError):
                    pass
            # --- Campos avançados de qualificação (agora mapeados para a sessão) ---
            if data.get("quartos_min") is not None:
                try:
                    extracted["bedrooms_min"] = int(data["quartos_min"])
                except (ValueError, TypeError):
                    pass
            if data.get("garagem") is not None:
                extracted["parking"] = bool(data["garagem"])
            if data.get("pet_friendly") is not None:
                extracted["pet_friendly"] = bool(data["pet_friendly"])
            if data.get("mobiliado") is not None:
                extracted["furnished"] = bool(data["mobiliado"])
            if data.get("prazo_mudanca"):
                extracted["move_deadline"] = data["prazo_mudanca"]

            return extracted

        except Exception as e:
            logger.error(
                "Falha ao extrair preferências com LLM. Utilizando fallback para Regex.",
                error=str(e),
            )
            return await self.fallback.extract(text, history)

    async def rank_properties_by_proximity(
        self, reference_point: str, properties: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Rankea uma lista de imóveis pela proximidade a um ponto de referência usando o LLM."""
        client = self._get_client()
        if not client or not properties:
            return properties

        provider = settings.llm_provider
        model = "gpt-4o-mini" if provider == "openai" else "deepseek-chat"

        simplified_props = []
        for p in properties:
            simplified_props.append(
                {
                    "id": p.get("id"),
                    "address": p.get("address"),
                    "neighborhood": p.get("neighborhood"),
                }
            )

        system_prompt = (
            "Você é um especialista em geografia, arruamento e localização da cidade de Sobral, Ceará.\n"
            "Sua tarefa é:\n"
            f"1. Identificar o endereço/localização exata do ponto de referência '{reference_point}' em Sobral/CE.\n"
            "2. Para cada imóvel da lista fornecida, determinar a distância aproximada ou facilidade de acesso até o ponto de referência (ex: 'Aprox. 400m', 'Aprox. 1.2km', 'Na mesma rua', etc.) com base no endereço e bairro do imóvel.\n"
            "3. Ordenar os imóveis do mais próximo para o mais distante do ponto de referência.\n\n"
            "Retorne APENAS um objeto JSON válido contendo exatamente a seguinte chave:\n"
            "{\n"
            '  "ranked_properties": [\n'
            "    {\n"
            '      "id": "ID_DO_IMOVEL",\n'
            "      \"proximity_description\": \"Breve descrição amigável da proximidade com emoji (ex: '🚶 Aprox. 5 min a pé / 400m da UFC', '🚗 Aprox. 3 min de carro / 1.2km da UFC')\"\n"
            "    },\n"
            "    ...\n"
            "  ]\n"
            "}\n\n"
            "Use apenas os IDs fornecidos. Não adicione novos imóveis. Se um imóvel estiver absurdamente longe ou for impossível de estimar, coloque uma descrição adequada mas ordene-o por último."
        )

        user_content = (
            f"Lista de imóveis para rankear:\n{json.dumps(simplified_props, ensure_ascii=False)}"
        )

        try:
            logger.info(
                "Realizando chamada para LLM para rankeamento de proximidade",
                provider=provider,
                model=model,
                reference_point=reference_point,
            )

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
                    timeout=12.0,
                )

            response = await self.circuit_breaker.call(_make_api_call)
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Resposta de rankeamento vazia do LLM")

            data = json.loads(content)
            ranked_list = data.get("ranked_properties", [])

            ordered_properties = []
            for item in ranked_list:
                pid = item.get("id")
                prop = next((p for p in properties if p.get("id") == pid), None)
                if prop:
                    prop_copy = dict(prop)
                    prop_copy["proximity"] = item.get("proximity_description")
                    ordered_properties.append(prop_copy)

            # Garante que imóveis não retornados pelo LLM não sejam perdidos
            for p in properties:
                if p.get("id") not in [op.get("id") for op in ordered_properties]:
                    prop_copy = dict(p)
                    prop_copy["proximity"] = None
                    ordered_properties.append(prop_copy)

            logger.info(
                "Rankeamento de proximidade concluído com sucesso", total=len(ordered_properties)
            )
            return ordered_properties

        except Exception as e:
            logger.error(
                "Falha ao rankear imóveis por proximidade com LLM. Retornando lista original.",
                error=str(e),
            )
            return [{**p, "proximity": None} for p in properties]
