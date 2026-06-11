# ExataBot — Claude Code Instructions
> Skills de Design Patterns, Clean Code e Clean Architecture para o projeto de WhatsApp Bot imobiliário

---

## 🧠 Contexto do Projeto

Você está desenvolvendo o **ExataBot**, um chatbot humanizado para WhatsApp integrado ao site https://www.exataservicos.net. A atendente virtual se chama **Ana** e responde perguntas de clientes sobre imóveis para locação e venda em Sobral/CE.

**Stack atual:**
- Python 3.12 + FastAPI + httpx + BeautifulSoup4
- Evolution API (WhatsApp Gateway)
- Deploy: Docker Compose + Railway

**Problema a resolver:** O `main.py` atual é um arquivo monolítico com ~600 linhas misturando scraping, lógica de negócio, envio de mensagens e configuração. Precisamos refatorar aplicando boas práticas profissionais.

---

## 🏗️ Arquitetura Alvo — Clean Architecture

Aplique rigorosamente esta estrutura de camadas. **Nunca deixe uma camada interna depender de uma camada externa.**

```
src/
├── domain/                  # Núcleo — ZERO dependências externas
│   ├── entities/            # Objetos com identidade (Session, PropertyListing)
│   ├── value_objects/       # Objetos imutáveis (Money, PhoneNumber)
│   └── repositories/        # Interfaces (abstrações, sem implementação)
│
├── application/             # Casos de uso — orquestra o domínio
│   ├── use_cases/           # Um arquivo por caso de uso
│   └── services/            # Serviços de aplicação (NLP, formatação)
│
├── infrastructure/          # Implementações concretas
│   ├── scraper/             # BeautifulSoup — implementa IPropertyRepository
│   ├── whatsapp/            # Evolution API — implementa IMessageGateway
│   └── cache/               # Cache em memória / Redis
│
├── presentation/            # Camada de entrada
│   └── webhook.py           # FastAPI routes + controllers
│
└── shared/                  # Utilitários transversais (logging, config)
    ├── config.py
    └── logger.py
```

**Regra de dependência:** `presentation → application → domain ← infrastructure`

---

## 📐 Design Patterns a Aplicar

### 1. Repository Pattern
**Onde:** `src/domain/repositories/` + `src/infrastructure/scraper/`
**Por quê:** Desacopla a lógica de busca de imóveis da implementação concreta (scraping hoje, API amanhã).

```python
# src/domain/repositories/property_repository.py
from abc import ABC, abstractmethod
from src.domain.entities.property_listing import PropertyListing
from src.domain.entities.session import Session

class IPropertyRepository(ABC):
    """Contrato de busca de imóveis — independente de implementação."""

    @abstractmethod
    async def find_by_preferences(self, session: Session) -> list[PropertyListing]:
        """Retorna imóveis filtrados pelas preferências da sessão."""
        ...

    @abstractmethod
    async def find_by_id(self, property_id: str) -> PropertyListing | None:
        """Retorna detalhes completos de um imóvel pelo ID interno."""
        ...
```

```python
# src/infrastructure/scraper/exata_property_repository.py
class ExataPropertyRepository(IPropertyRepository):
    """Implementação concreta via scraping do site exataservicos.net."""

    async def find_by_preferences(self, session: Session) -> list[PropertyListing]:
        # BeautifulSoup aqui — detalhes de implementação isolados
        ...
```

---

### 2. State Pattern
**Onde:** `src/domain/entities/session.py` + `src/application/use_cases/`
**Por quê:** Cada etapa da conversa (início, preferências, mostrando resultados) tem comportamento diferente para a mesma mensagem.

```python
# src/domain/entities/session.py
from enum import Enum, auto

class ConversationStep(Enum):
    START       = auto()
    INTENT      = auto()      # locação ou venda?
    PREFERENCES = auto()      # tipo, bairro, valor
    SEARCHING   = auto()
    SHOWING     = auto()
    DETAIL      = auto()

# src/application/use_cases/handle_message.py
# O HandleMessageUseCase despacha para o handler correto baseado no step:

STEP_HANDLERS: dict[ConversationStep, type[StepHandler]] = {
    ConversationStep.START:       StartHandler,
    ConversationStep.INTENT:      IntentHandler,
    ConversationStep.PREFERENCES: PreferencesHandler,
    ConversationStep.SHOWING:     ShowingHandler,
    ConversationStep.DETAIL:      DetailHandler,
}
```

---

### 3. Strategy Pattern
**Onde:** `src/application/services/preference_extractor.py`
**Por quê:** A extração de preferências pode usar regex (gratuito) ou LLM (pago). Trocar sem mudar o restante do código.

```python
# src/application/services/preference_extractor.py
from abc import ABC, abstractmethod

class IPreferenceExtractor(ABC):
    @abstractmethod
    async def extract(self, text: str, history: list[str]) -> dict:
        """Extrai preferências de uma mensagem em linguagem natural."""
        ...

class RegexPreferenceExtractor(IPreferenceExtractor):
    """Extração via regex — gratuito, zero latência."""
    async def extract(self, text: str, history: list[str]) -> dict:
        ...

class LLMPreferenceExtractor(IPreferenceExtractor):
    """Extração via DeepSeek/GPT-4o-mini — mais preciso."""
    async def extract(self, text: str, history: list[str]) -> dict:
        ...
```

---

### 4. Gateway Pattern
**Onde:** `src/domain/repositories/message_gateway.py` + `src/infrastructure/whatsapp/`
**Por quê:** Isola o código de negócio da Evolution API. Se mudar para Z-API ou Meta Cloud API, só troca a implementação.

```python
# src/domain/repositories/message_gateway.py
from abc import ABC, abstractmethod

class IMessageGateway(ABC):
    @abstractmethod
    async def send_text(self, phone: str, text: str, typing_delay: float = 1.2) -> None: ...

    @abstractmethod
    async def send_image(self, phone: str, image_url: str, caption: str = "") -> None: ...

    @abstractmethod
    async def send_typing(self, phone: str, duration_ms: int = 1500) -> None: ...
```

---

### 5. Factory Pattern
**Onde:** `src/shared/container.py`
**Por quê:** Centraliza a criação e injeção de dependências. Facilita testes (troca implementações reais por mocks).

```python
# src/shared/container.py
from src.infrastructure.scraper.exata_property_repository import ExataPropertyRepository
from src.infrastructure.whatsapp.evolution_gateway import EvolutionMessageGateway
from src.infrastructure.cache.memory_cache import MemoryCache
from src.application.use_cases.handle_message import HandleMessageUseCase
from src.shared.config import Settings

def create_container(settings: Settings) -> dict:
    """
    Dependency Injection Container — Factory que monta o grafo de dependências.
    Em testes, substitua as implementações por fakes/mocks.
    """
    cache = MemoryCache(ttl_minutes=30)

    property_repo = ExataPropertyRepository(
        base_url=settings.site_base_url,
        cache=cache,
    )

    message_gateway = EvolutionMessageGateway(
        api_url=settings.evolution_api_url,
        api_key=settings.evolution_api_key,
        instance=settings.evolution_instance,
    )

    use_case = HandleMessageUseCase(
        property_repo=property_repo,
        message_gateway=message_gateway,
        extractor=RegexPreferenceExtractor(),
    )

    return {"handle_message": use_case}
```

---

### 6. Value Objects
**Onde:** `src/domain/value_objects/`
**Por quê:** Encapsulam lógica de validação e formatação. Evitam "Primitive Obsession".

```python
# src/domain/value_objects/money.py
from dataclasses import dataclass

@dataclass(frozen=True)     # imutável por design
class Money:
    amount: float

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Valor não pode ser negativo.")

    def is_within(self, max_value: "Money") -> bool:
        return self.amount <= max_value.amount

    def formatted(self) -> str:
        return f"R$ {self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Uso:
rent = Money(1500.0)
print(rent.formatted())   # "R$ 1.500,00"
print(rent.is_within(Money(2000.0)))  # True


# src/domain/value_objects/phone_number.py
@dataclass(frozen=True)
class PhoneNumber:
    raw: str

    def __post_init__(self):
        normalized = re.sub(r"\D", "", self.raw)
        if len(normalized) < 10:
            raise ValueError(f"Número inválido: {self.raw}")
        object.__setattr__(self, "_normalized", normalized)

    @property
    def normalized(self) -> str:
        return self._normalized

    def whatsapp_jid(self) -> str:
        return f"{self.normalized}@s.whatsapp.net"
```

---

## 🧹 Clean Code — Regras Obrigatórias

### Nomenclatura
```python
# ❌ RUIM — abreviações, nomes sem significado
async def proc_msg(n, t):
    s = get_s(n)
    if s.e == "m":
        res = await sc(s.b, s.v)

# ✅ BOM — nomes revelam intenção
async def process_incoming_message(phone: str, text: str) -> None:
    session = await session_repository.get_or_create(phone)
    if session.step == ConversationStep.SHOWING:
        results = await property_repository.find_by_preferences(session)
```

### Funções com responsabilidade única (SRP)
```python
# ❌ RUIM — função faz tudo
async def processar_mensagem(numero, texto):
    # extrai preferências
    # busca imóveis
    # monta resposta
    # envia via WhatsApp
    # atualiza sessão

# ✅ BOM — cada função faz UMA coisa
class HandleMessageUseCase:
    async def execute(self, phone: str, text: str) -> None:
        session = await self._session_repo.get_or_create(phone)
        preferences = await self._extractor.extract(text)
        session.update_preferences(**preferences)
        handler = self._get_handler(session.step)
        await handler.handle(session, text)
        await self._session_repo.save(session)
```

### Evitar comentários óbvios — código autoexplicativo
```python
# ❌ RUIM
# Incrementa o contador de mensagens
s.contagem_msgs += 1

# ✅ BOM — o nome já explica
session.message_count += 1
```

### Magic numbers → constantes nomeadas
```python
# ❌ RUIM
if 8 <= now.hour < 18 and now.weekday() in [0, 1, 2, 3, 4]:
    ...

# ✅ BOM
BUSINESS_HOURS_START = 8
BUSINESS_HOURS_END = 18
BUSINESS_WEEKDAYS = range(0, 5)  # segunda a sexta

def is_within_business_hours() -> bool:
    now = datetime.now()
    return (
        now.weekday() in BUSINESS_WEEKDAYS
        and BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END
    )
```

### Evitar else desnecessário (Early Return)
```python
# ❌ RUIM
def get_greeting(hour: int) -> str:
    if hour < 12:
        return "Bom dia"
    else:
        if hour < 18:
            return "Boa tarde"
        else:
            return "Boa noite"

# ✅ BOM
def get_greeting(hour: int) -> str:
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"
```

### Tratamento de exceções específico
```python
# ❌ RUIM
try:
    result = await client.get(url)
except:
    return []

# ✅ BOM
try:
    result = await client.get(url, timeout=15.0)
    result.raise_for_status()
except httpx.TimeoutException:
    logger.warning(f"Timeout ao buscar {url}")
    return []
except httpx.HTTPStatusError as e:
    logger.error(f"HTTP {e.response.status_code} ao buscar {url}")
    return []
except httpx.RequestError as e:
    logger.error(f"Erro de rede ao buscar {url}: {e}")
    return []
```

---

## 🔒 SOLID Principles — Aplicação Prática

### S — Single Responsibility
Cada classe e função tem **uma única razão para mudar**.

```
ExataPropertyRepository   → só busca imóveis (muda se o site mudar)
EvolutionMessageGateway   → só envia mensagens (muda se a API mudar)
RegexPreferenceExtractor  → só extrai preferências (muda se a lógica mudar)
SessionRepository         → só persiste sessões (muda se o storage mudar)
HandleMessageUseCase      → só orquestra o fluxo (muda se o negócio mudar)
```

### O — Open/Closed
Aberto para extensão, fechado para modificação.

```python
# Adicionar novo canal (Telegram, Instagram) SEM modificar código existente:
class ITelegramGateway(IMessageGateway):
    async def send_text(self, phone: str, text: str, typing_delay: float = 1.2) -> None:
        # implementação Telegram
        ...

# O HandleMessageUseCase funciona com qualquer IMessageGateway
# sem precisar de nenhuma modificação
```

### L — Liskov Substitution
Qualquer implementação concreta deve substituir sua interface sem quebrar o sistema.

```python
# Estas duas são intercambiáveis em qualquer lugar que use IPropertyRepository:
repo_real  = ExataPropertyRepository(base_url="https://www.exataservicos.net")
repo_fake  = FakePropertyRepository(fixtures=[...])  # usado em testes

use_case = HandleMessageUseCase(property_repo=repo_real)  # produção
use_case = HandleMessageUseCase(property_repo=repo_fake)  # testes
```

### I — Interface Segregation
Interfaces pequenas e específicas, não uma grande interface geral.

```python
# ❌ RUIM — interface gorda
class IRepository(ABC):
    async def find_all(self): ...
    async def find_by_id(self): ...
    async def save(self): ...
    async def delete(self): ...
    async def count(self): ...
    async def bulk_insert(self): ...

# ✅ BOM — interfaces específicas para cada necessidade
class IPropertyReader(ABC):
    async def find_by_preferences(self, session: Session) -> list[PropertyListing]: ...
    async def find_by_id(self, id: str) -> PropertyListing | None: ...

class ISessionStore(ABC):
    async def get_or_create(self, phone: str) -> Session: ...
    async def save(self, session: Session) -> None: ...
```

### D — Dependency Inversion
Dependa de abstrações, não de implementações concretas.

```python
# ❌ RUIM — dependência direta da implementação
class HandleMessageUseCase:
    def __init__(self):
        self.repo = ExataPropertyRepository()      # concreto
        self.gateway = EvolutionMessageGateway()  # concreto

# ✅ BOM — depende das interfaces (abstrações)
class HandleMessageUseCase:
    def __init__(
        self,
        property_repo: IPropertyRepository,    # interface
        message_gateway: IMessageGateway,      # interface
        extractor: IPreferenceExtractor,       # interface
    ):
        self._property_repo = property_repo
        self._message_gateway = message_gateway
        self._extractor = extractor
```

---

## 🧪 Testes com Design Patterns

### Fake Objects (melhor que Mock para repositórios)
```python
# tests/fakes/fake_property_repository.py
class FakePropertyRepository(IPropertyRepository):
    """Fake in-memory — sem httpx, sem rede, determinístico."""

    def __init__(self, fixtures: list[PropertyListing]):
        self._data = fixtures

    async def find_by_preferences(self, session: Session) -> list[PropertyListing]:
        return [
            p for p in self._data
            if p.matches_preferences(
                listing_type=session.listing_type,
                neighborhood=session.neighborhood,
                max_rent=session.max_rent,
            )
        ]

    async def find_by_id(self, property_id: str) -> PropertyListing | None:
        return next((p for p in self._data if p.id == property_id), None)
```

### Spy para o Gateway de mensagens
```python
# tests/fakes/spy_message_gateway.py
class SpyMessageGateway(IMessageGateway):
    """Registra chamadas sem enviar nada — útil para assertions."""

    def __init__(self):
        self.sent_texts: list[tuple[str, str]] = []
        self.sent_images: list[tuple[str, str]] = []

    async def send_text(self, phone: str, text: str, typing_delay: float = 0) -> None:
        self.sent_texts.append((phone, text))

    async def send_image(self, phone: str, image_url: str, caption: str = "") -> None:
        self.sent_images.append((phone, image_url))

    async def send_typing(self, phone: str, duration_ms: int = 0) -> None:
        pass  # sem efeito em testes

    def last_text_sent_to(self, phone: str) -> str | None:
        msgs = [text for p, text in self.sent_texts if p == phone]
        return msgs[-1] if msgs else None
```

### Teste de caso de uso completo
```python
# tests/unit/test_handle_message.py
import pytest
from src.application.use_cases.handle_message import HandleMessageUseCase
from src.domain.value_objects.money import Money
from tests.fakes.fake_property_repository import FakePropertyRepository
from tests.fakes.spy_message_gateway import SpyMessageGateway
from tests.fixtures.property_fixtures import make_property

@pytest.fixture
def use_case():
    repo = FakePropertyRepository(fixtures=[
        make_property(id="1", neighborhood="Centro", monthly_rent=Money(1200.0)),
        make_property(id="2", neighborhood="Aldeota", monthly_rent=Money(1800.0)),
    ])
    gateway = SpyMessageGateway()
    return HandleMessageUseCase(property_repo=repo, message_gateway=gateway), gateway

@pytest.mark.asyncio
async def test_greeting_on_first_message(use_case):
    handler, gateway = use_case
    await handler.execute(phone="5588999990000", text="oi")
    last = gateway.last_text_sent_to("5588999990000")
    assert "Ana" in last
    assert "Exata Serviços" in last

@pytest.mark.asyncio
async def test_search_filters_by_neighborhood(use_case):
    handler, gateway = use_case
    await handler.execute("5588999990000", "oi")
    await handler.execute("5588999990000", "locação")
    await handler.execute("5588999990000", "casa no centro")
    last = gateway.last_text_sent_to("5588999990000")
    assert "Centro" in last
    assert "Aldeota" not in last
```

---

## 📦 Estrutura Final de Arquivos

```
src/
│
├── domain/                              # ← NUNCA importa de infrastructure
│   ├── entities/
│   │   ├── session.py                  # ConversationStep (State Pattern)
│   │   └── property_listing.py         # matches_preferences()
│   ├── value_objects/
│   │   ├── money.py                    # frozen dataclass
│   │   └── phone_number.py             # frozen dataclass
│   └── repositories/                   # interfaces (ABC)
│       ├── i_property_repository.py    # IPropertyRepository
│       ├── i_message_gateway.py        # IMessageGateway
│       └── i_session_store.py          # ISessionStore
│
├── application/
│   ├── use_cases/
│   │   └── handle_message.py           # orquestra o fluxo completo
│   └── services/
│       ├── i_preference_extractor.py   # interface (Strategy)
│       ├── regex_extractor.py          # implementação gratuita
│       └── llm_extractor.py            # implementação DeepSeek/GPT
│
├── infrastructure/
│   ├── scraper/
│   │   └── exata_property_repository.py   # httpx + BeautifulSoup
│   ├── whatsapp/
│   │   └── evolution_gateway.py           # Evolution API
│   └── cache/
│       └── memory_cache.py                # TTL in-memory
│
├── presentation/
│   └── webhook.py                     # FastAPI routes
│
└── shared/
    ├── config.py                      # Settings com pydantic-settings
    ├── logger.py                      # logger configurado
    └── container.py                   # DI Container (Factory Pattern)

tests/
├── unit/
│   ├── test_money.py
│   ├── test_session.py
│   └── test_handle_message.py
├── integration/
│   └── test_exata_scraper.py          # testa scraping real (lento, CI apenas)
└── fakes/
    ├── fake_property_repository.py
    └── spy_message_gateway.py
```

---

## ⚙️ Configuração com Pydantic Settings

```python
# src/shared/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Evolution API
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str
    evolution_instance: str = "exatabot"

    # Bot
    bot_name: str = "Ana"
    business_hours_start: int = 8
    business_hours_end: int = 18
    site_base_url: str = "https://www.exataservicos.net"
    cache_ttl_minutes: int = 30
    results_page_size: int = 3
    max_photos_per_property: int = 3

    # LLM (opcional)
    llm_provider: str = "regex"          # "regex" | "openai" | "deepseek"
    openai_api_key: str = ""
    deepseek_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Singleton
settings = Settings()
```

---

## 🚀 Checklist de Qualidade

Antes de cada commit, verifique:

- [ ] Nenhum arquivo tem mais de **200 linhas** (SRP)
- [ ] Nenhuma função tem mais de **20 linhas**
- [ ] Nenhuma função tem mais de **3 parâmetros** (agrupe em dataclass se necessário)
- [ ] Zero dependências de `infrastructure` no `domain`
- [ ] Toda interface tem pelo menos **1 fake** nos testes
- [ ] Nomes de variáveis, funções e classes em **inglês** (consistência)
- [ ] Strings de mensagens ao cliente **externalizadas** (não hard-coded nas classes)
- [ ] Cobertura de testes > **80%** nos use cases
- [ ] Nenhum `except Exception:` sem log + motivo
- [ ] Nenhum número mágico sem constante nomeada

---

## 🔁 Ordem de Refatoração Recomendada

Faça **um passo por sessão de trabalho**, commitando ao final de cada um:

1. Criar `value_objects/money.py` e `value_objects/phone_number.py` com testes
2. Criar `entities/property_listing.py` e `entities/session.py` com `ConversationStep`
3. Criar as 3 interfaces (repository, gateway, extractor)
4. Extrair `ExataPropertyRepository` do `main.py` → `infrastructure/scraper/`
5. Extrair `EvolutionMessageGateway` do `main.py` → `infrastructure/whatsapp/`
6. Criar `HandleMessageUseCase` com injeção de dependências
7. Criar fakes + testes unitários dos use cases
8. Refatorar `main.py` → `presentation/webhook.py` usando o container
9. Adicionar `LLMPreferenceExtractor` como Strategy alternativo
10. Configurar CI com pytest + coverage

