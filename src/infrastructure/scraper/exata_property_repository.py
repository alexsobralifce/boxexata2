import asyncio
import time
from typing import Any, Optional, cast
from bs4 import BeautifulSoup
import httpx
import re
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlmodel import select, col
from src.infrastructure.persistence.models import Properties

from src.domain.entities.property_listing import PropertyListing
from src.domain.entities.session import Session
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.domain.value_objects.money import Money
from src.infrastructure.cache.memory_cache import MemoryCache
from src.shared.config import settings
from src.shared.logger import logger


class RateLimiter:
    """Garante um intervalo mínimo de tempo entre requisições ao mesmo domínio."""

    def __init__(self, min_delay_seconds: float = 1.0) -> None:
        self.min_delay = min_delay_seconds
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                await asyncio.sleep(sleep_time)
            self.last_request_time = time.time()


class ExataPropertyRepository(IPropertyRepository):
    """Implementação de scraping para recuperar imóveis com persistência em banco de dados."""

    def __init__(
        self,
        cache: Optional[Any] = None,
        rate_limiter: Optional[RateLimiter] = None,
        engine: Optional[AsyncEngine] = None,
    ) -> None:
        self.cache = cache or MemoryCache(default_ttl_seconds=settings.cache_ttl_minutes * 60)
        self.rate_limiter = rate_limiter or RateLimiter(min_delay_seconds=1.0)
        self.engine = engine
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        self.timeout = 15.0

    @property
    def site_base_url(self) -> str:
        """Retorna a URL base do site de scraping de forma dinâmica do contexto ativo."""
        from src.shared.context import get_current_broker

        broker = get_current_broker()
        if broker and broker.site_base_url:
            return broker.site_base_url
        return settings.site_base_url

    def _map_property_type_to_code(self, property_type: Optional[str]) -> Optional[int]:
        """Mapeia a string descritiva do tipo de imóvel para o código interno do site."""
        if not property_type:
            return None
        pt = property_type.lower().strip()
        if "casa" in pt:
            return 4
        elif "apto" in pt or "apartamento" in pt:
            return 5
        elif "kitnet" in pt or "quitinete" in pt or "kitinete" in pt:
            return 6
        elif "sitio" in pt or "sítio" in pt:
            return 7
        elif "ponto" in pt:
            return 1
        elif "sala" in pt:
            return 2
        elif "galpao" in pt or "galpão" in pt:
            return 3
        elif "terreno" in pt:
            return 8
        elif "lote" in pt:
            return 10
        return None

    def _map_code_to_property_type(self, code: int) -> str:
        """Mapeia o código interno do site de volta para a descrição textual."""
        mapping = {
            1: "Ponto comercial",
            2: "Salas",
            3: "Galpão",
            4: "Casa",
            5: "Apartamento",
            6: "Quitinete",
            7: "Sítio",
            8: "Terreno murado",
            9: "Terreno não murado",
            10: "Lote",
        }
        return mapping.get(code, "Imóvel")

    def _parse_price(self, val_str: str) -> float:
        """Limpa e converte a string de valor para float de forma robusta."""
        val_str = val_str.replace("R$", "").replace(" ", "").strip()
        if not val_str:
            return 0.0

        if "." in val_str and "," in val_str:
            clean = val_str.replace(".", "").replace(",", ".")
        elif "," in val_str:
            clean = val_str.replace(",", ".")
        elif "." in val_str:
            parts = val_str.split(".")
            if len(parts[-1]) == 2:
                clean = val_str
            else:
                clean = val_str.replace(".", "")
        else:
            clean = val_str

        try:
            return float(clean)
        except ValueError:
            logger.warn("Falha ao converter valor do imóvel para float", raw_value=val_str)
            return 0.0

    @staticmethod
    def _absolutize_url(base_url: str, maybe_relative: str) -> str:
        """Concatena base + path tratando casos problemáticos de URL.

        - Retorna string vazia se o caminho for vazio.
        - Preserva URLs já absolutas (``http://``, ``https://`` ou ``//cdn...``).
        - Normaliza barras duplicadas ao juntar base e path.
        """
        if not maybe_relative:
            return ""
        candidate = maybe_relative.strip()
        if not candidate:
            return ""
        if (
            candidate.startswith("http://")
            or candidate.startswith("https://")
            or candidate.startswith("//")
        ):
            return candidate
        base = (base_url or "").rstrip("/")
        path = candidate.lstrip("/")
        if not base:
            return f"/{path}"
        return f"{base}/{path}"

    async def _fetch_html(self, url: str) -> str:
        """Faz a requisição HTTP respeitando rate limiting e retorna o HTML."""
        await self.rate_limiter.wait()
        logger.info("Realizando request HTTP para o site Exata", url=url)
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Tenta decodificar como UTF-8; se houver erro, decodifica como ISO-8859-1
            try:
                content = response.content.decode("utf-8")
            except UnicodeDecodeError:
                content = response.content.decode("iso-8859-1")
            return content

    async def _scrape_all_basic_listings(self) -> dict[str, dict[str, Any]]:
        """Busca a listagem completa em imovel.php e constrói dicionário por ID."""
        cache_key = "all_basic_listings"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, dict[str, Any]], cached)

        url = f"{self.site_base_url}/imovel.php"
        try:
            html = await self._fetch_html(url)
        except Exception as e:
            logger.error("Erro ao carregar listagem geral do site Exata", error=str(e))
            return {}

        soup = BeautifulSoup(html, "html.parser")
        listings: dict[str, dict[str, Any]] = {}

        for div in soup.find_all("div", id="mold"):
            a_tag = div.find("a")
            if not a_tag:
                continue
            href_val = a_tag.get("href")
            if not href_val or isinstance(href_val, list):
                continue
            href = href_val
            property_id = href.split("codigo=")[-1] if "codigo=" in href else ""
            if not property_id:
                continue

            img_tag = div.find("img")
            src_val = img_tag.get("src") if img_tag else None
            cover_image = src_val if src_val and not isinstance(src_val, list) else ""
            cover_image = self._absolutize_url(self.site_base_url, cover_image)

            text_parts = div.get_text("|", strip=True).split("|")
            parts = [p.strip() for p in text_parts if p.strip()]

            kv_map = {}
            i = 0
            while i < len(parts):
                part = parts[i]
                part_clean = part.rstrip(":").lower()
                if part.endswith(":") or part_clean in (
                    "tipo",
                    "finalidade",
                    "codigo",
                    "código",
                    "ref",
                    "ref.",
                    "endereço",
                    "endereco",
                    "bairro",
                    "valor",
                ):
                    key = part_clean
                    if i + 1 < len(parts) and not (
                        parts[i + 1].endswith(":")
                        or parts[i + 1].rstrip(":").lower()
                        in (
                            "tipo",
                            "finalidade",
                            "codigo",
                            "código",
                            "ref",
                            "ref.",
                            "endereço",
                            "endereco",
                            "bairro",
                            "valor",
                        )
                    ):
                        kv_map[key] = parts[i + 1]
                        i += 2
                    else:
                        kv_map[key] = ""
                        i += 1
                elif ":" in part:
                    k, v = part.split(":", 1)
                    kv_map[k.strip().lower()] = v.strip()
                    i += 1
                else:
                    i += 1

            intent = kv_map.get("tipo") or kv_map.get("finalidade") or ""
            ref = (
                kv_map.get("código")
                or kv_map.get("codigo")
                or kv_map.get("ref")
                or kv_map.get("ref.")
                or ""
            )
            address = kv_map.get("endereço") or kv_map.get("endereco") or ""
            neighborhood = kv_map.get("bairro") or ""
            price_val = self._parse_price(kv_map.get("valor", "0.0"))

            listings[property_id] = {
                "id": property_id,
                "ref": ref,
                "intent": intent,
                "address": address,
                "neighborhood": neighborhood,
                "price": price_val,
                "cover_image": cover_image,
                "url": self._absolutize_url(self.site_base_url, href),
            }

        await self.cache.set(cache_key, listings)
        return listings

    # --- Database operations ---

    async def save(self, property: PropertyListing) -> None:
        """Persiste ou atualiza o imóvel no banco de dados."""
        if not self.engine:
            return
        model = Properties.from_entity(property)
        async with AsyncSession(self.engine) as session:
            existing = await session.get(Properties, property.id)
            if existing:
                existing.ref = model.ref
                existing.property_type = model.property_type
                existing.address = model.address
                existing.neighborhood = model.neighborhood
                existing.value = model.value
                existing.url = model.url
                existing.fees = model.fees
                existing.bedrooms = model.bedrooms
                existing.bathrooms = model.bathrooms
                existing.parking_spaces = model.parking_spaces
                existing.description = model.description
                existing.photos = model.photos
                existing.intent = model.intent
                existing.is_available = model.is_available
                session.add(existing)
            else:
                session.add(model)
            await session.commit()

    async def delete(self, property_id: str) -> None:
        """Remove um imóvel do banco de dados."""
        if not self.engine:
            return
        async with AsyncSession(self.engine) as session:
            existing = await session.get(Properties, property_id)
            if existing:
                await session.delete(existing)
                await session.commit()

    async def list_stored_properties(
        self,
        property_type: Optional[str] = None,
        bedrooms: Optional[int] = None,
        bathrooms: Optional[int] = None,
        parking_spaces: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        neighborhood: Optional[str] = None,
        intent: Optional[str] = None,
        ref: Optional[str] = None,
        is_available: Optional[bool] = None,
    ) -> list[PropertyListing]:
        """Lista imóveis no banco de dados aplicando os filtros fornecidos."""
        if not self.engine:
            return []

        async with AsyncSession(self.engine) as session:
            statement = select(Properties)
            if property_type:
                statement = statement.where(
                    col(Properties.property_type).ilike(f"%{property_type}%")
                )
            if bedrooms is not None:
                statement = statement.where(col(Properties.bedrooms) >= bedrooms)
            if bathrooms is not None:
                statement = statement.where(col(Properties.bathrooms) >= bathrooms)
            if parking_spaces is not None:
                statement = statement.where(col(Properties.parking_spaces) >= parking_spaces)
            if min_price is not None:
                statement = statement.where(col(Properties.value) >= min_price)
            if max_price is not None:
                statement = statement.where(col(Properties.value) <= max_price)
            if neighborhood:
                statement = statement.where(col(Properties.neighborhood).ilike(f"%{neighborhood}%"))
            if intent:
                statement = statement.where(col(Properties.intent).ilike(f"%{intent}%"))
            if ref:
                statement = statement.where(col(Properties.ref).ilike(f"%{ref}%"))
            if is_available is not None:
                statement = statement.where(col(Properties.is_available) == is_available)

            statement = statement.order_by(col(Properties.created_at).desc())
            result = await session.execute(statement)
            models = result.scalars().all()
            return [m.to_entity() for m in models]

    # --- Main Interface Implementations ---

    async def find_by_preferences(self, session: Session) -> list[PropertyListing]:
        """Busca imóveis com base nas preferências, integrando dados do site com o banco."""
        logger.info(
            "Iniciando busca de imóveis por preferências",
            intent=session.intent,
            property_type=session.property_type,
            neighborhood=session.neighborhood,
            max_value=session.max_value,
        )

        all_basics = await self._scrape_all_basic_listings()
        tipo_codigo = self._map_property_type_to_code(session.property_type)
        filtered_ids: Optional[set[str]] = None

        if tipo_codigo is not None:
            cache_key = f"listings_type_{tipo_codigo}"
            cached_ids = await self.cache.get(cache_key)

            if cached_ids is not None:
                filtered_ids = cached_ids
            else:
                url = f"{self.site_base_url}/resultado_imovel.php?codigo={tipo_codigo}"
                try:
                    html = await self._fetch_html(url)
                    soup = BeautifulSoup(html, "html.parser")
                    current_ids = set()
                    for div in soup.find_all("div", id="mold"):
                        a_tag = div.find("a")
                        if a_tag:
                            href_val = a_tag.get("href")
                            if href_val and not isinstance(href_val, list):
                                href = href_val
                                pid = href.split("codigo=")[-1] if "codigo=" in href else ""
                                if pid:
                                    current_ids.add(pid)
                    await self.cache.set(cache_key, current_ids)
                    filtered_ids = current_ids
                except Exception as e:
                    logger.error(
                        "Erro ao buscar filtragem por tipo de imóvel",
                        code=tipo_codigo,
                        error=str(e),
                    )
                    filtered_ids = None

        results: list[PropertyListing] = []
        for pid, basic in all_basics.items():
            if filtered_ids is not None and pid not in filtered_ids:
                continue

            prop_type = (
                self._map_code_to_property_type(tipo_codigo)
                if tipo_codigo is not None
                else "Imóvel"
            )

            if session.intent:
                clean_intent = session.intent.strip().lower()
                if clean_intent not in basic["intent"].lower():
                    continue

            if basic["price"] <= 0 or not basic["address"].strip():
                continue

            detailed = await self.find_by_id(pid)
            if detailed:
                listing = detailed
            else:
                listing = PropertyListing(
                    property_id=pid,
                    ref=basic["ref"],
                    property_type=prop_type,
                    address=basic["address"],
                    neighborhood=basic["neighborhood"],
                    value=Money(basic["price"]),
                    url=basic["url"],
                    photos=[basic["cover_image"]] if basic["cover_image"] else [],
                    intent=basic["intent"],
                )

            if listing.matches_preferences(
                intent=session.intent,
                property_type=session.property_type,
                neighborhood=session.neighborhood,
                max_value=session.max_value,
            ):
                results.append(listing)

        logger.info("Busca por preferências concluída", total_resultados=len(results))
        return results

    async def find_by_id(self, property_id: str) -> Optional[PropertyListing]:
        """Busca informações detalhadas de um imóvel pelo seu ID, checando banco primeiro."""
        cache_key = f"property_detail_{property_id}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            logger.info("Recuperando imóvel detalhado do cache", id=property_id)
            return cast(Optional[PropertyListing], cached)

        if self.engine:
            async with AsyncSession(self.engine) as db_session:
                model = await db_session.get(Properties, property_id)
                if model and model.description:
                    # Se a descrição contiver o menu do site por erro anterior, vamos re-scrapar para corrigir
                    desc_lower = model.description.lower()
                    has_menu = "residencialcasa" in desc_lower or (
                        "residencial" in desc_lower
                        and "quitinete" in desc_lower
                        and "apartamento" in desc_lower
                    )
                    if not has_menu:
                        logger.info(
                            "Recuperando imóvel detalhado do banco de dados", id=property_id
                        )
                        entity = model.to_entity()
                        await self.cache.set(cache_key, entity)
                        return entity
                    else:
                        logger.info(
                            "Imóvel no BD possui menu na descrição, forçando re-scrape para correção",
                            id=property_id,
                        )

        all_basics = await self._scrape_all_basic_listings()
        basic = all_basics.get(property_id)

        url = f"{self.site_base_url}/detalhe_imovel.php?codigo={property_id}"
        try:
            html = await self._fetch_html(url)
        except Exception as e:
            logger.error("Erro ao carregar detalhes do imóvel", id=property_id, error=str(e))
            return None

        listing = await self._parse_detail_html(property_id, html, basic)
        if listing:
            await self.save(listing)
            await self.cache.set(cache_key, listing)
            return listing

        return None

    # --- Scraper Helpers ---

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<[^>]*>", "", text)
        replacements = {
            "&nbsp;": " ",
            "&oacute;": "ó",
            "&ccdil;": "ç",
            "&ccedil;": "ç",
            "&atilde;": "ã",
            "&eacute;": "é",
            "&iacute;": "í",
            "&uacute;": "ú",
            "&acirc;": "â",
            "&otilde;": "õ",
            "&Acirc;": "Â",
            "&Ocirc;": "Ô",
            "&ocirc;": "ô",
        }
        for entity, val in replacements.items():
            text = text.replace(entity, val)
        return text.strip().rstrip(";").rstrip(".")

    def _extract_description_lines(self, html: str) -> list[str]:
        lines = []
        li_matches = re.findall(r"<li[^>]*>([\s\S]*?)<\/li>", html, re.IGNORECASE)
        for match in li_matches:
            txt = self._clean_text(match)
            if txt and txt not in lines:
                lines.append(txt)

        div_matches = re.findall(r"<div[^>]*>([\s\S]*?)<\/div>", html, re.IGNORECASE)
        for match in div_matches:
            txt = self._clean_text(match)
            if (
                txt
                and "fancybox" not in txt
                and "agendar.php" not in txt
                and not txt.startswith("<")
            ):
                if txt not in lines:
                    lines.append(txt)

        if not lines:
            br_lines = re.split(r"<br\s*\/?>", html, flags=re.IGNORECASE)
            for line in br_lines:
                txt = self._clean_text(line)
                if txt and txt not in lines:
                    lines.append(txt)

        return [line for line in lines if line]

    def _parse_features_from_text(self, description: str) -> dict[str, Optional[int]]:
        bedrooms = None
        bathrooms = None
        parking_spaces = None

        lines = [line.strip() for line in description.split("\n") if line.strip()]
        suite_count = 0
        social_bath_count = 0

        for line in lines:
            clean_line = line.lower()

            bed_match = re.search(r"(\d+)\s*(?:quarto|dormitorio)", clean_line)
            if bed_match and bedrooms is None:
                bedrooms = int(bed_match.group(1))

            suite_bed_match = re.search(r"(\d+)\s*(?:suíte|suite)", clean_line)
            if suite_bed_match:
                num_suites = int(suite_bed_match.group(1))
                suite_count += num_suites
                if bedrooms is None:
                    bedrooms = num_suites
            elif "suíte" in clean_line or "suite" in clean_line:
                suite_count += 1
                if bedrooms is None:
                    bedrooms = 1

            bath_match = re.search(r"(\d+)\s*(?:banheiro|wc|sanitario)", clean_line)
            if bath_match:
                social_bath_count += int(bath_match.group(1))
            elif "banheiro" in clean_line or "wc" in clean_line or "sanitario" in clean_line:
                social_bath_count += 1

            park_match = re.search(
                r"(?:garagem\s*p\/\s*|vagas?\s*p\/\s*|vagas?\s*de\s*garagem\s*p\/\s*|garagem\s*para\s*)(\d+)",
                clean_line,
            ) or re.search(
                r"(\d+)\s*(?:vagas?\s*de\s*garagem|vagas?\s*na\s*garagem|garagens?)", clean_line
            )
            if park_match and parking_spaces is None:
                parking_spaces = int(park_match.group(1))
            elif "garagem" in clean_line or "vaga de garagem" in clean_line:
                if parking_spaces is None:
                    parking_spaces = 1

        if suite_count > 0 or social_bath_count > 0:
            bathrooms = max(social_bath_count, suite_count)
            has_explicit_suite = any(
                "suíte" in line.lower() or "suite" in line.lower() for line in lines
            )
            has_explicit_social = any(
                ("banheiro" in line.lower() or "wc" in line.lower() or "sanitario" in line.lower())
                and not ("suíte" in line.lower() or "suite" in line.lower())
                for line in lines
            )
            if has_explicit_suite and has_explicit_social:
                bathrooms = suite_count + social_bath_count

        return {"bedrooms": bedrooms, "bathrooms": bathrooms, "parking_spaces": parking_spaces}

    async def _use_llm_to_format_description(
        self, description_raw: str
    ) -> Optional[dict[str, Any]]:
        provider = settings.llm_provider
        api_key = (
            settings.openai_api_key
            if provider == "openai"
            else (settings.deepseek_api_key if provider == "deepseek" else "")
        )
        if not api_key or provider == "regex":
            return None

        base_url = "https://api.deepseek.com" if provider == "deepseek" else None
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            model = "gpt-4o-mini" if provider == "openai" else "deepseek-chat"

            prompt = (
                "Dado o HTML de descrição de um imóvel, extraia os itens da descrição e organize-os em uma lista de tópicos limpa (um por linha, sem marcadores HTML ou markdown). Além disso, extraia a quantidade de quartos (bedrooms), banheiros (bathrooms) e vagas de garagem (parking spaces).\n\n"
                f"HTML de descrição:\n{description_raw}\n\n"
                "Retorne estritamente um JSON no seguinte formato:\n"
                "{\n"
                '  "descriptionFormatted": "Garagem p/ 04 carros\\n02 Salas de estar\\n...",\n'
                '  "bedrooms": 3,\n'
                '  "bathrooms": 2,\n'
                '  "parkingSpaces": 1\n'
                "}"
            )

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                timeout=10.0,
            )
            content = response.choices[0].message.content
            if content:
                import json

                data = json.loads(content)
                return {
                    "description": data.get("descriptionFormatted", ""),
                    "bedrooms": data.get("bedrooms"),
                    "bathrooms": data.get("bathrooms"),
                    "parking_spaces": data.get("parkingSpaces"),
                }
        except Exception as e:
            logger.error("Error formatting description with LLM", error=str(e))
        return None

    async def _parse_detail_html(
        self, property_id: str, html: str, basic: Optional[dict[str, Any]] = None
    ) -> Optional[PropertyListing]:
        soup = BeautifulSoup(html, "html.parser")
        ref = ""
        address = ""
        number = ""
        neighborhood = ""
        complement = ""
        fees_str = ""
        price_str = ""

        for strong in soup.find_all("strong"):
            label = strong.get_text(strip=True).lower()
            if not strong.parent:
                continue
            parent_text = strong.parent.get_text(strip=True)
            val = ""
            if ":" in parent_text:
                val = parent_text.split(":", 1)[1].strip()

            if "código" in label or "codigo" in label:
                ref = val
            elif "endereço" in label or "endereco" in label:
                address = val
            elif "número" in label or "numero" in label:
                number = val
            elif "bairro" in label:
                neighborhood = val
            elif "complemento" in label:
                complement = val
            elif "taxas" in label:
                fees_str = val
            elif "valor" in label:
                price_str = val

        # Descrição/Características
        desc_td = None
        details_table = None
        for strong in soup.find_all("strong"):
            lbl = strong.get_text(strip=True).lower()
            if "código" in lbl or "codigo" in lbl:
                details_table = strong.find_parent("table")
                break

        if details_table:
            for strong in details_table.find_all("strong"):
                lbl = strong.get_text(strip=True).lower()
                if "descrição" in lbl or "descricao" in lbl:
                    parent_tr = strong.find_parent("tr")
                    if parent_tr:
                        next_tr = parent_tr.find_next_sibling("tr")
                        if next_tr:
                            desc_td = next_tr.find("td")
                            break

        if not desc_td:
            # Se não achou dentro da tabela de detalhes, busca na página inteira
            for strong in soup.find_all("strong"):
                lbl = strong.get_text(strip=True).lower()
                if "descrição" in lbl or "descricao" in lbl:
                    parent_tr = strong.find_parent("tr")
                    if parent_tr:
                        next_tr = parent_tr.find_next_sibling("tr")
                        if next_tr:
                            desc_td = next_tr.find("td")
                            break

        description_raw = desc_td.decode_contents() if desc_td else ""
        if not description_raw:
            # Fallback a procurar ul, mas evitando o menu principal
            target_ul = None
            if details_table:
                target_ul = details_table.find("ul")

            if not target_ul:
                for ul in soup.find_all("ul"):
                    ul_text = ul.get_text().lower()
                    # Menus têm muitos tipos de imóveis juntos
                    menu_keywords = [
                        "residencial",
                        "comercial",
                        "quitinete",
                        "ponto comercial",
                        "salas",
                    ]
                    matches = sum(1 for kw in menu_keywords if kw in ul_text)
                    if matches >= 3:
                        continue
                    target_ul = ul
                    break

            if target_ul:
                description_raw = target_ul.decode_contents()

        description_formatted = ""
        bedrooms = None
        bathrooms = None
        parking_spaces = None

        ai_result = await self._use_llm_to_format_description(description_raw)
        if ai_result:
            description_formatted = ai_result["description"]
            bedrooms = ai_result["bedrooms"]
            bathrooms = ai_result["bathrooms"]
            parking_spaces = ai_result["parking_spaces"]
        else:
            lines = self._extract_description_lines(description_raw)
            description_formatted = "\n".join(lines)
            feats = self._parse_features_from_text(description_formatted)
            bedrooms = feats["bedrooms"]
            bathrooms = feats["bathrooms"]
            parking_spaces = feats["parking_spaces"]

        # Photos
        photos: list[str] = []
        for a in soup.find_all("a", class_="fancybox"):
            href_val = a.get("href")
            if href_val and not isinstance(href_val, list):
                href = self._absolutize_url(self.site_base_url, href_val)
                if href and href not in photos:
                    photos.append(href)

        # Fallbacks basic info
        if basic:
            if not ref:
                ref = basic["ref"]
            if not address:
                address = basic["address"]
            if not neighborhood:
                neighborhood = basic["neighborhood"]
            if not price_str:
                price_val = basic["price"]
            else:
                price_val = self._parse_price(price_str)
            if not photos and basic.get("cover_image"):
                photos.append(basic["cover_image"])
            intent_val = basic.get("intent", "Locação")
            prop_type = basic.get("property_type", "Imóvel")
        else:
            price_val = self._parse_price(price_str)
            intent_val = "Locação"
            prop_type = "Imóvel"
            # Tentar adivinhar tipo a partir do complemento ou descrição
            comp_lower = complement.lower()
            desc_lower = description_formatted.lower()
            if "casa" in comp_lower or "casa" in desc_lower:
                prop_type = "Casa"
            elif "apto" in comp_lower or "apartamento" in comp_lower or "apartamento" in desc_lower:
                prop_type = "Apartamento"
            elif "sala" in comp_lower or "ponto" in comp_lower or "comercial" in desc_lower:
                prop_type = "Ponto comercial"
            elif "galpão" in comp_lower or "galpao" in desc_lower:
                prop_type = "Galpão"
            elif "quitinete" in comp_lower or "kitnet" in comp_lower or "quitinete" in desc_lower:
                prop_type = "Quitinete"

        full_address = address
        if number:
            full_address += f", {number}"
        if complement:
            full_address += f" - {complement}"

        fees_val = self._parse_price(fees_str)

        return PropertyListing(
            property_id=property_id,
            ref=ref,
            property_type=prop_type,
            address=full_address,
            neighborhood=neighborhood,
            value=Money(price_val),
            url=f"{self.site_base_url}/detalhe_imovel.php?codigo={property_id}",
            fees=Money(fees_val) if fees_val > 0 else None,
            features=description_formatted.split("\n") if description_formatted else [],
            photos=photos,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            parking_spaces=parking_spaces,
            description=description_formatted,
            intent=intent_val,
        )

    # --- Live Scraper Search by Ref code ---

    async def check_id_for_ref(self, id_val: int, target_ref: str) -> Optional[str]:
        url = f"{self.site_base_url}/detalhe_imovel.php?codigo={id_val}"
        try:
            await self.rate_limiter.wait()
            async with httpx.AsyncClient(headers=self.headers, timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    html = response.text
                    if target_ref.upper() in html.upper():
                        ref_match = (
                            re.search(
                                r"C&oacute;digo:<\/strong>\s*(?:<[^>]*>)*\s*([a-zA-Z0-9]+)",
                                html,
                                re.IGNORECASE,
                            )
                            or re.search(
                                r"C&oacute;digo:<\/strong>\s*([a-zA-Z0-9]+)", html, re.IGNORECASE
                            )
                            or re.search(r"C&oacute;digo:\s*([a-zA-Z0-9]+)", html, re.IGNORECASE)
                        )
                        if ref_match and ref_match.group(1).upper() == target_ref.upper():
                            return html
        except Exception:
            pass
        return None

    async def locate_property_html(self, target_ref: str) -> Optional[tuple[str, str]]:
        # 1. Search in basic listings
        all_basics = await self._scrape_all_basic_listings()
        for pid, basic in all_basics.items():
            if basic.get("ref", "").upper() == target_ref.upper():
                url = f"{self.site_base_url}/detalhe_imovel.php?codigo={pid}"
                await self.rate_limiter.wait()
                async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        return pid, resp.text

        # 2. Concurrently scan range of IDs
        logger.info(
            "Reference not found in active basic list. Scanning IDs concurrently...", ref=target_ref
        )
        min_id = 500
        max_id = 950
        chunk_size = 30

        for start in range(max_id, min_id - 1, -chunk_size):
            end = max(min_id, start - chunk_size + 1)
            tasks = [
                self.check_id_for_ref(id_val, target_ref) for id_val in range(start, end - 1, -1)
            ]
            results = await asyncio.gather(*tasks)
            for i, html in enumerate(results):
                if html:
                    scraped_id = str(start - i)
                    return scraped_id, html
        return None

    async def scrape_by_ref(self, target_ref: str) -> Optional[PropertyListing]:
        """Realiza o scrape completo de um imóvel por código de referência."""
        result = await self.locate_property_html(target_ref)
        if not result:
            return None
        property_id, html = result

        # Encontra se existia dados básicos
        all_basics = await self._scrape_all_basic_listings()
        basic = all_basics.get(property_id)

        listing = await self._parse_detail_html(property_id, html, basic)
        if listing:
            # Força a referência a ser exatamente o target_ref se veio diferente
            if not listing.ref:
                listing.ref = target_ref
            await self.save(listing)
            # Limpa cache
            cache_key = f"property_detail_{property_id}"
            await self.cache.delete(cache_key)
            return listing
        return None
