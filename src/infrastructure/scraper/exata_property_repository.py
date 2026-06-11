import asyncio
import time
from typing import Any, Optional, cast
from bs4 import BeautifulSoup
import httpx

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
    """Implementação concreta de scraping para recuperar imóveis do site Exata Serviços."""

    def __init__(
        self,
        cache: Optional[MemoryCache] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self.cache = cache or MemoryCache(default_ttl_seconds=settings.cache_ttl_minutes * 60)
        self.rate_limiter = rate_limiter or RateLimiter(min_delay_seconds=1.0)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        self.timeout = 15.0

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
            # Padrão brasileiro: 1.250,50 -> 1250.50
            clean = val_str.replace(".", "").replace(",", ".")
        elif "," in val_str:
            # e.g., 800,00 -> 800.00
            clean = val_str.replace(",", ".")
        elif "." in val_str:
            # e.g., 750.00 ou 1500.00 ou 1.500
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

    async def _fetch_html(self, url: str) -> str:
        """Faz a requisição HTTP respeitando rate limiting e retorna o HTML."""
        await self.rate_limiter.wait()
        logger.info("Realizando request HTTP para o site Exata", url=url)
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            # O site usa codificação ISO-8859-1 (Latin1) frequentemente
            content_type = response.headers.get("content-type", "").lower()
            if "utf-8" not in content_type:
                response.encoding = "iso-8859-1"
            return response.text

    async def _scrape_all_basic_listings(self) -> dict[str, dict[str, Any]]:
        """Busca a listagem completa em imovel.php e constrói dicionário por ID."""
        cache_key = "all_basic_listings"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, dict[str, Any]], cached)

        url = f"{settings.site_base_url}/imovel.php"
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
            if cover_image and not cover_image.startswith("http"):
                cover_image = f"{settings.site_base_url}/{cover_image}"

            # Parsing text-based key-values inside the mold box
            text_parts = div.get_text("|", strip=True).split("|")
            parts = [p.strip() for p in text_parts if p.strip()]

            kv_map = {}
            i = 0
            while i < len(parts):
                part = parts[i]
                part_clean = part.rstrip(":").lower()
                # Verifica se a parte é uma palavra-chave de metadados
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
                    # Apenas associa se o próximo item não for outra chave
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
                "url": f"{settings.site_base_url}/{href}",
            }

        self.cache.set(cache_key, listings)
        return listings

    async def find_by_preferences(self, session: Session) -> list[PropertyListing]:
        """Busca imóveis no site com base nas preferências coletadas."""
        logger.info(
            "Iniciando busca de imóveis por preferências",
            intent=session.intent,
            property_type=session.property_type,
            neighborhood=session.neighborhood,
            max_value=session.max_value,
        )

        # 1. Carrega todos os anúncios básicos para ter preço e dados gerais
        all_basics = await self._scrape_all_basic_listings()

        tipo_codigo = self._map_property_type_to_code(session.property_type)
        filtered_ids: Optional[set[str]] = None

        # 2. Se o tipo do imóvel for especificado e mapeável, filtra pelos IDs desse tipo
        if tipo_codigo is not None:
            cache_key = f"listings_type_{tipo_codigo}"
            cached_ids = self.cache.get(cache_key)

            if cached_ids is not None:
                filtered_ids = cached_ids
            else:
                url = f"{settings.site_base_url}/resultado_imovel.php?codigo={tipo_codigo}"
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
                                pid = (
                                    href.split("codigo=")[-1]
                                    if "codigo=" in href
                                    else ""
                                )
                                if pid:
                                    current_ids.add(pid)
                    self.cache.set(cache_key, current_ids)
                    filtered_ids = current_ids
                except Exception as e:
                    logger.error("Erro ao buscar filtragem por tipo de imóvel", code=tipo_codigo, error=str(e))
                    filtered_ids = None

        # 3. Monta a lista final combinando as duas fontes de dados
        results: list[PropertyListing] = []
        for pid, basic in all_basics.items():
            # Se filtramos por tipo, ignorar se não pertencer aos IDs filtrados
            if filtered_ids is not None and pid not in filtered_ids:
                continue

            # Determina o tipo descritivo
            prop_type = (
                self._map_code_to_property_type(tipo_codigo)
                if tipo_codigo is not None
                else "Imóvel"
            )

            # Filtros adicionais no repositório (além do matches_preferences do domínio)
            # Filtro de finalidade (Locação ou Venda)
            if session.intent:
                clean_intent = session.intent.strip().lower()
                # O intent do anúncio pode ser "Locação" ou "Venda"
                if clean_intent not in basic["intent"].lower():
                    continue

            # Pula anúncios incompletos (sem preço ou sem endereço)
            if basic["price"] <= 0 or not basic["address"].strip():
                continue

            # Constrói entidade básica
            listing = PropertyListing(
                property_id=pid,
                ref=basic["ref"],
                property_type=prop_type,
                address=basic["address"],
                neighborhood=basic["neighborhood"],
                value=Money(basic["price"]),
                url=basic["url"],
                photos=[basic["cover_image"]] if basic["cover_image"] else [],
            )

            # Aplica validação de preferências do domínio (bairro, tipo_imovel, max_value)
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
        """Busca informações detalhadas de um imóvel pelo seu ID, com suporte a cache."""
        cache_key = f"property_detail_{property_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("Recuperando imóvel detalhado do cache", id=property_id)
            return cast(Optional[PropertyListing], cached)

        # Busca informações básicas primeiro para manter consistência (valor, tipo, cover photo)
        all_basics = await self._scrape_all_basic_listings()
        basic = all_basics.get(property_id)

        url = f"{settings.site_base_url}/detalhe_imovel.php?codigo={property_id}"
        try:
            html = await self._fetch_html(url)
        except Exception as e:
            logger.error("Erro ao carregar detalhes do imóvel", id=property_id, error=str(e))
            return None

        soup = BeautifulSoup(html, "html.parser")

        ref = ""
        address = ""
        number = ""
        neighborhood = ""
        complement = ""
        fees_str = ""
        price_str = ""
        features: list[str] = []

        # Extração das tabelas de detalhes
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
        for ul in soup.find_all("ul"):
            lis = ul.find_all("li")
            if lis:
                features = [li.get_text(strip=True) for li in lis]
                break

        # Fotos (fancybox links)
        photos: list[str] = []
        for a in soup.find_all("a", class_="fancybox"):
            href_val = a.get("href")
            if href_val and not isinstance(href_val, list):
                href = href_val
                if not href.startswith("http"):
                    href = f"{settings.site_base_url}/{href}"
                if href not in photos:
                    photos.append(href)

        # Fallbacks caso o HTML detalhado falte ou seja parseado incorretamente
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
            if not photos and basic["cover_image"]:
                photos.append(basic["cover_image"])
        else:
            price_val = self._parse_price(price_str)

        # Monta endereço completo
        full_address = address
        if number:
            full_address += f", {number}"
        if complement:
            full_address += f" - {complement}"

        fees_val = self._parse_price(fees_str)

        listing = PropertyListing(
            property_id=property_id,
            ref=ref,
            property_type=basic["property_type"] if basic and "property_type" in basic else "Imóvel",
            address=full_address,
            neighborhood=neighborhood,
            value=Money(price_val),
            url=url,
            fees=Money(fees_val) if fees_val > 0 else None,
            features=features,
            photos=photos,
        )

        self.cache.set(cache_key, listing)
        return listing
