# ExataBot — Documentação Técnica do Sistema

> **Propósito deste documento:** Referência completa para LLMs e desenvolvedores que precisam entender a arquitetura, padrões, entidades e convenções do ExataBot antes de implementar novas funcionalidades.

---

## Índice

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura Geral (Clean Architecture)](#2-arquitetura-geral-clean-architecture)
3. [Estrutura de Diretórios](#3-estrutura-de-diretórios)
4. [Camada de Domínio](#4-camada-de-domínio)
   - [Entidades](#41-entidades)
   - [Value Objects](#42-value-objects)
   - [Interfaces de Repositório / Gateway](#43-interfaces-de-repositório--gateway)
5. [Camada de Aplicação](#5-camada-de-aplicação)
   - [Casos de Uso](#51-casos-de-uso)
   - [Máquina de Estados (Handlers)](#52-máquina-de-estados-handlers)
   - [Serviços de Aplicação](#53-serviços-de-aplicação)
6. [Camada de Infraestrutura](#6-camada-de-infraestrutura)
   - [Scraper](#61-scraper)
   - [Gateway WhatsApp (Evolution API)](#62-gateway-whatsapp-evolution-api)
   - [Persistência (Sessão, Subscrições, Logs, Corretores)](#63-persistência)
   - [Cache (Memória e Redis)](#64-cache)
7. [Camada de Apresentação](#7-camada-de-apresentação)
   - [Webhook Principal](#71-webhook-principal)
   - [Painel Admin (API REST)](#72-painel-admin-api-rest)
8. [Módulo Compartilhado (shared)](#8-módulo-compartilhado-shared)
   - [Container de Injeção de Dependências](#81-container-de-injeção-de-dependências)
   - [Configurações (Settings)](#82-configurações-settings)
   - [Contexto Multi-Tenant](#83-contexto-multi-tenant)
   - [Circuit Breaker](#84-circuit-breaker)
   - [Logger Estruturado](#85-logger-estruturado)
9. [Fluxo Completo de uma Mensagem](#9-fluxo-completo-de-uma-mensagem)
10. [Fluxo de Alertas Proativos](#10-fluxo-de-alertas-proativos)
11. [Multi-Tenancy (Suporte a Múltiplos Corretores)](#11-multi-tenancy-suporte-a-múltiplos-corretores)
12. [Infraestrutura Docker](#12-infraestrutura-docker)
13. [Variáveis de Ambiente](#13-variáveis-de-ambiente)
14. [Testes](#14-testes)
15. [Padrões de Design Adotados](#15-padrões-de-design-adotados)
16. [Convenções de Código](#16-convenções-de-código)
17. [Roadmap e Fases de Desenvolvimento](#17-roadmap-e-fases-de-desenvolvimento)
18. [Como Executar e Testar](#18-como-executar-e-testar)

---

## 1. Visão Geral do Sistema

**ExataBot** é um chatbot de WhatsApp voltado ao mercado imobiliário, desenvolvido para a empresa **Exata Serviços** de Sobral/CE. O bot atende clientes via WhatsApp, coleta suas preferências de imóvel (finalidade, tipo, bairro, valor), realiza scraping no site `exataservicos.net`, exibe os resultados e permite visualizar detalhes, ativar alertas de novos imóveis e agendar visitas.

### Tecnologias Principais

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ |
| Framework Web | FastAPI (async) |
| Servidor ASGI | Uvicorn |
| WhatsApp Gateway | Evolution API v2 |
| Scraping | httpx + BeautifulSoup4 |
| Cache | Redis (produção) / In-Memory (dev) |
| Sessões | Redis (produção) / In-Memory (dev) |
| Banco de Dados | PostgreSQL via SQLModel + asyncpg |
| Migrações | Alembic |
| Extração NLP | Regex (padrão) ou OpenAI/DeepSeek (opcional) |
| Autenticação Admin | JWT (PyJWT + passlib/bcrypt) |
| Agendador | APScheduler (AsyncIOScheduler) |
| Logs | structlog (estruturado) |
| Containerização | Docker + Docker Compose |

---

## 2. Arquitetura Geral (Clean Architecture)

O sistema segue os princípios de **Clean Architecture** com 4 camadas, onde as dependências sempre apontam para dentro (da Infra → App → Domain):

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION (FastAPI)                    │
│          webhook.py  |  admin_router.py  |  security.py     │
├─────────────────────────────────────────────────────────────┤
│                  APPLICATION (Use Cases)                     │
│   HandleMessageUseCase  |  NotifyNewListingsUseCase         │
│   Handlers (State Machine)  |  Services (Extractors)        │
├─────────────────────────────────────────────────────────────┤
│                     DOMAIN (Core)                            │
│   Entities  |  Value Objects  |  Repository Interfaces      │
├─────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE                             │
│   ExataPropertyRepository  |  EvolutionGateway             │
│   Redis/Memory Stores  |  SQLModel Persistence              │
└─────────────────────────────────────────────────────────────┘
                          ↑
                    SHARED (cross-cutting)
         Container DI  |  Config  |  Logger  |  CircuitBreaker
```

**Regra de ouro:** O Domínio não importa nada das outras camadas. A Infraestrutura implementa as interfaces do Domínio. A Aplicação orquestra e usa as interfaces. A Apresentação invoca os casos de uso.

---

## 3. Estrutura de Diretórios

```
botexata/
├── src/
│   ├── domain/
│   │   ├── entities/            # Entidades de negócio puras
│   │   │   ├── session.py       # Session + ConversationStep
│   │   │   ├── property_listing.py
│   │   │   ├── subscription.py
│   │   │   ├── broker_profile.py
│   │   │   └── message_log.py
│   │   ├── value_objects/
│   │   │   ├── money.py
│   │   │   └── phone_number.py
│   │   └── repositories/        # Interfaces (contratos)
│   │       ├── i_property_repository.py
│   │       ├── i_message_gateway.py
│   │       ├── i_session_store.py
│   │       ├── i_subscription_store.py
│   │       ├── i_message_log_repository.py
│   │       └── i_broker_profile_repository.py
│   │
│   ├── application/
│   │   ├── use_cases/
│   │   │   ├── handle_message.py         # Orquestrador principal
│   │   │   ├── notify_new_listings.py    # Alertas proativos
│   │   │   └── handlers/                 # State machine handlers
│   │   │       ├── base_handler.py
│   │   │       ├── start_handler.py
│   │   │       ├── intent_handler.py
│   │   │       ├── preferences_handler.py
│   │   │       ├── showing_handler.py
│   │   │       ├── detail_handler.py
│   │   │       └── farewell_handler.py
│   │   └── services/
│   │       ├── i_preference_extractor.py
│   │       ├── regex_extractor.py
│   │       ├── llm_extractor.py
│   │       ├── auth_service.py
│   │       └── message_log_middleware.py
│   │
│   ├── infrastructure/
│   │   ├── scraper/
│   │   │   └── exata_property_repository.py  # Scraping + RateLimiter
│   │   ├── whatsapp/
│   │   │   └── evolution_gateway.py
│   │   ├── persistence/
│   │   │   ├── models.py                     # SQLModel ORM models
│   │   │   ├── memory_session_store.py
│   │   │   ├── redis_session_store.py
│   │   │   ├── memory_subscription_store.py
│   │   │   ├── redis_subscription_store.py
│   │   │   ├── memory_broker_profile_repository.py
│   │   │   ├── sql_broker_profile_repository.py
│   │   │   ├── sql_log_repository.py
│   │   │   └── null_log_repository.py
│   │   └── cache/
│   │       ├── memory_cache.py
│   │       └── redis_cache.py
│   │
│   ├── presentation/
│   │   ├── webhook.py            # Endpoint /webhook (Evolution API)
│   │   ├── admin_router.py       # Rotas /api/admin/*
│   │   ├── security.py           # JWT validation dependency
│   │   └── static/               # Dashboard admin (HTML/JS/CSS)
│   │
│   └── shared/
│       ├── container.py          # Dependency Injection Factory
│       ├── config.py             # Settings (pydantic-settings)
│       ├── context.py            # Multi-tenant ContextVar
│       ├── circuit_breaker.py    # CircuitBreaker genérico
│       └── logger.py             # structlog configurado
│
├── tests/
│   ├── fakes/                    # Test doubles (SpyMessageGateway etc.)
│   ├── unit/                     # Testes unitários
│   └── integration/              # Testes de integração (requerem internet)
│
├── migrations/                   # Alembic migrations (PostgreSQL)
├── doc/                          # Documentação
├── scripts/                      # Scripts de setup e deploy
├── docker-compose.yml            # Produção
├── docker-compose.dev.yml        # Desenvolvimento local
├── Dockerfile
├── pyproject.toml
└── main.py                       # Entry point (importa e executa webhook.app)
```

---

## 4. Camada de Domínio

### 4.1 Entidades

#### `Session` — `src/domain/entities/session.py`

Representa a **sessão de conversa** de um cliente. É o objeto central da máquina de estados.

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `phone` | `str` | Número de telefone (identificador único) |
| `step` | `ConversationStep` | Estado atual da conversa |
| `client_name` | `Optional[str]` | Nome do cliente (extraído da conversa) |
| `intent` | `Optional[str]` | `"Locação"` ou `"Venda"` |
| `property_type` | `Optional[str]` | `"Casa"`, `"Apartamento"`, `"Quitinete"`, etc. |
| `neighborhood` | `Optional[str]` | Bairro desejado |
| `max_value` | `Optional[float]` | Valor máximo em R$ |
| `results` | `list[dict]` | Imóveis encontrados (serializado como dict) |
| `result_offset` | `int` | Paginação — offset atual dos resultados |
| `message_count` | `int` | Total de mensagens trocadas |
| `selected_property_id` | `Optional[str]` | ID do imóvel atualmente em detalhe |
| `history` | `list[str]` | Histórico de mensagens (últimas 20, formato `"Cliente: <texto>"`) |

**Enum `ConversationStep`:**

```
START → INTENT → PREFERENCES → SEARCHING → SHOWING → DETAIL → FAREWELL
```

| Step | Descrição |
|---|---|
| `START` | Início — bot dá boas-vindas |
| `INTENT` | Aguarda finalidade: Locação ou Venda |
| `PREFERENCES` | Coleta tipo, bairro, valor → realiza busca |
| `SEARCHING` | Estado intermediário (busca em progresso) |
| `SHOWING` | Exibe resultados, navega, ativa alertas |
| `DETAIL` | Exibe detalhes do imóvel selecionado |
| `FAREWELL` | Fluxo de encerramento após ativação de alerta (pergunta se quer continuar) |

**Métodos importantes:**
- `update_preferences(**kwargs)` — atualiza campos coletados sem sobrescrever com `None`
- `transition_to(step)` — muda o estado
- `reset_search()` — zera todos os campos e volta ao `START`
- `increment_messages()` — incrementa contador de mensagens

---

#### `PropertyListing` — `src/domain/entities/property_listing.py`

Representa um **anúncio de imóvel** scraped do site.

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `id` | `str` | ID interno do site (ex: `"123"`) |
| `ref` | `str` | Código de referência do anúncio |
| `property_type` | `str` | Tipo descritivo (`"Casa"`, `"Apartamento"`, etc.) |
| `address` | `str` | Endereço completo |
| `neighborhood` | `str` | Bairro |
| `value` | `Money` | Valor principal (aluguel ou venda) |
| `url` | `str` | Link para o anúncio no site |
| `fees` | `Optional[Money]` | Taxas (condomínio/IPTU), se houver |
| `features` | `list[str]` | Lista de características (quartos, vagas, etc.) |
| `photos` | `list[str]` | URLs das fotos |

**Métodos:**
- `matches_preferences(intent, property_type, neighborhood, max_value)` → `bool` — filtro de compatibilidade
- `to_dict()` → `dict` — serialização para JSON/cache

---

#### `Subscription` — `src/domain/entities/subscription.py`

Representa uma **assinatura de alerta** de um usuário (notificação proativa de novos imóveis).

**Atributos:** `phone`, `intent`, `property_type`, `neighborhood`, `max_value`, `created_at`

**Método:** `matches(listing: PropertyListing)` → `bool` — verifica se um imóvel novo corresponde ao perfil da assinatura

---

#### `BrokerProfile` — `src/domain/entities/broker_profile.py`

Representa o **perfil de um corretor/imobiliária** (tenant no modelo multi-tenant).

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `instance_id` | `str` | ID da instância do WhatsApp na Evolution API (PK) |
| `broker_name` | `str` | Nome do corretor ou imobiliária |
| `phone_number` | `str` | Número de telefone do corretor |
| `site_base_url` | `str` | URL base do site para scraping deste corretor |
| `bot_name` | `str` | Nome da atendente virtual (padrão: `"Ana"`) |
| `is_active` | `bool` | Se o perfil está ativo |
| `created_at` | `datetime` | Data de criação |

---

#### `MessageLog` — `src/domain/entities/message_log.py`

Registra cada mensagem trocada (entrada e saída).

**Atributos:** `id`, `phone`, `direction` (`"in"` ou `"out"`), `text`, `step`, `intent`, `created_at`

---

### 4.2 Value Objects

#### `Money` — `src/domain/value_objects/money.py`

Encapsula um valor monetário em R$.

- `amount: float`
- `formatted()` → `str` — ex: `"R$ 1.200,00"`

#### `PhoneNumber` — `src/domain/value_objects/phone_number.py`

Encapsula e valida um número de telefone brasileiro.

---

### 4.3 Interfaces de Repositório / Gateway

Todos definidos em `src/domain/repositories/`. São as **abstrações** que permitem trocar implementações sem alterar o domínio ou a aplicação.

| Interface | Responsabilidade |
|---|---|
| `IPropertyRepository` | `find_by_preferences(session)` e `find_by_id(id)` |
| `IMessageGateway` | `send_text()`, `send_image()`, `send_typing()` |
| `ISessionStore` | `get_or_create(phone)`, `save(session)` |
| `ISubscriptionStore` | `save()`, `delete()`, `list_all()`, `is_notified()`, `mark_notified()` |
| `IMessageLogRepository` | `save(log)`, `list_by_phone(phone, limit)` |
| `IBrokerProfileRepository` | `save()`, `get_by_instance()`, `list_all()`, `delete()` |

---

## 5. Camada de Aplicação

### 5.1 Casos de Uso

#### `HandleMessageUseCase` — `src/application/use_cases/handle_message.py`

**Orquestrador principal** do fluxo de mensagens. Recebe uma mensagem de um cliente e:

1. Verifica horário de atendimento (Seg-Sex, 08h-18h configurável)
2. Busca ou cria a sessão do cliente (`session_store.get_or_create(phone)`)
3. Incrementa contador e adiciona mensagem ao histórico (últimas 20)
4. Loga a mensagem de entrada (se `log_repo` ativo) via `asyncio.create_task`
5. Executa extração de preferências (regex ou LLM) — **exceto** nos estados `SHOWING` e `DETAIL`
6. Loop da máquina de estados (max 5 transições):
   - Obtém o handler do step atual
   - Executa `handler.handle(session, text)` → retorna `bool` (continuar ou não)
   - Se o step não mudou ou `should_continue == False`, sai do loop
7. Salva a sessão atualizada

**Dependências injetadas:** `session_store`, `property_repo`, `message_gateway`, `extractor`, `subscription_store`, `log_repo`

---

#### `NotifyNewListingsUseCase` — `src/application/use_cases/notify_new_listings.py`

**Caso de uso de alertas proativos.** Executado periodicamente pelo APScheduler:

1. Lista todas as assinaturas ativas
2. Para cada assinatura, busca imóveis que correspondem ao perfil
3. Filtra apenas os **não notificados** (`subscription_store.is_notified()`)
4. Envia foto (se disponível) + mensagem de alerta via WhatsApp
5. Marca como notificado (`subscription_store.mark_notified()`)

---

### 5.2 Máquina de Estados (Handlers)

Cada handler corresponde a um `ConversationStep` e implementa `BaseHandler` com o método:

```python
async def handle(self, session: Session, text: str) -> bool:
    # Retorna True para continuar o loop, False para parar
```

#### `StartHandler` — `start_handler.py`

- Envia boas-vindas (nome do bot, perguntas)
- Transiciona para `INTENT`
- Retorna `True` (para o loop prosseguir imediatamente)

#### `IntentHandler` — `intent_handler.py`

- Interpreta se o cliente quer `"Locação"` ou `"Venda"`
- Transiciona para `PREFERENCES` se detectou intenção, senão pede confirmação
- Se a intenção já estava na sessão (extraída pelo extrator), prossegue diretamente

#### `PreferencesHandler` — `preferences_handler.py`

- Verifica se as preferências mínimas foram coletadas (tipo e bairro)
- Se sim: realiza a busca via `property_repo.find_by_preferences(session)`
- Armazena os resultados em `session.results` (como lista de dicts via `to_dict()`)
- Exibe os primeiros `results_page_size` imóveis (padrão: 3)
- Transiciona para `SHOWING`

#### `ShowingHandler` — `showing_handler.py`

Handler mais complexo. Interpreta comandos na etapa de exibição:

| Comando | Ação |
|---|---|
| `"reiniciar"`, `"começar"`, etc. | Reseta sessão, volta para `INTENT` |
| `"alertar"`, `"receber alertas"`, etc. | Cria `Subscription` e ativa alertas |
| `"desativar alerta"`, `"cancelar alerta"`, etc. | Remove assinatura |
| `"mais"`, `"outro"`, `"proxima"`, etc. | Pagina resultados |
| Número (`"1"`, `"2"`, etc.) | Abre detalhes do imóvel (transiciona para `DETAIL`) |

#### `DetailHandler` — `detail_handler.py`

- Trata navegação dentro de um imóvel em detalhe
- `"voltar"` → retorna para `SHOWING`
- `"reiniciar"` → reseta tudo
- Qualquer outra coisa → lembra comandos disponíveis

#### `FarewellHandler` — `farewell_handler.py`

- Ativado após o cliente criar um alerta no estado `SHOWING`.
- Pergunta ao cliente se deseja continuar o atendimento ou encerrar (1-Sim, 2-Não).
- `"1"` ou `"sim"` → Reinicia a conversa (vai para `INTENT`).
- `"2"` ou `"não"` → Agradece, se despede e reseta a sessão (volta para `START`).

---

### 5.3 Serviços de Aplicação

#### `IPreferenceExtractor` + `RegexPreferenceExtractor` + `LLMPreferenceExtractor`

Interface e duas implementações da **extração de preferências** da mensagem do cliente.

**`RegexPreferenceExtractor`** — padrão offline:
- Detecta intenção por palavras-chave (aluguel → Locação, compra → Venda)
- Detecta tipo por palavras-chave (casa, apartamento, kitnet, etc.)
- Detecta bairros por lista curada de Sobral/CE
- Detecta valor máximo por regex (ex: `"até 1.200"`, `"1,5 mil"`)
- Detecta nome do cliente por padrões como `"Me chamo X"`, `"sou a X"`

**`LLMPreferenceExtractor`** — opcional (OpenAI ou DeepSeek):
- Usa prompt estruturado para extrair JSON com campos: `finalidade`, `tipo`, `bairro`, `cidade`, `valor_max`, `quartos_min`, `pet_friendly`, `garagem`, `mobiliado`, `nome_cliente`
- Protegido por `CircuitBreaker` (3 falhas → abre por 60s)
- **Fallback automático** para `RegexPreferenceExtractor` se LLM falhar ou não estiver configurado

**Retorno do extrator:** `dict[str, Any]` com chaves mapeadas para os atributos de `Session`:
- `intent`, `property_type`, `neighborhood`, `max_value`, `client_name`

---

#### `MessageLogMiddleware` — `src/application/services/message_log_middleware.py`

**Decorator** do `IMessageGateway` que intercepta chamadas de envio e registra logs de **saída** automaticamente no banco de dados. Usa o padrão Decorator sobre o `EvolutionGateway`.

---

#### `AuthService` — `src/application/services/auth_service.py`

Utilitários para autenticação do painel admin:
- `verify_password(plain, hashed)` — bcrypt verify
- `create_access_token(data)` — gera JWT com expiração configurável

---

## 6. Camada de Infraestrutura

### 6.1 Scraper

#### `ExataPropertyRepository` — `src/infrastructure/scraper/exata_property_repository.py`

Implementação de `IPropertyRepository` que realiza scraping do site **exataservicos.net**.

**Estratégia de scraping:**

1. **`_scrape_all_basic_listings()`**: Faz GET em `/imovel.php`, parseia todos os `<div id="mold">` e constrói um dict `{property_id: {ref, intent, address, neighborhood, price, cover_image, url}}`. Resultado cacheado por `cache_ttl_minutes` (padrão: 30 min).

2. **Filtro por tipo**: Se `property_type` for especificado, faz GET em `/resultado_imovel.php?codigo={tipo_codigo}` para obter IDs filtrados. Resultado cacheado por tipo.

3. **`find_by_preferences(session)`**: Combina os dados, aplica filtros (finalidade, preço > 0, endereço não vazio), constrói entidades `PropertyListing` e aplica `matches_preferences()` do domínio.

4. **`find_by_id(property_id)`**: Faz GET em `/detalhe_imovel.php?codigo={id}`, parseia `<strong>` para extrair todos os campos detalhados + fotos (links `class="fancybox"`). Resultado cacheado individualmente.

**Mapeamento de tipos (código ↔ nome):**

| Código | Nome |
|---|---|
| 1 | Ponto comercial |
| 2 | Salas |
| 3 | Galpão |
| 4 | Casa |
| 5 | Apartamento |
| 6 | Quitinete |
| 7 | Sítio |
| 8 | Terreno murado |
| 9 | Terreno não murado |
| 10 | Lote |

**Encoding:** O site usa `iso-8859-1`. O scraper detecta e converte automaticamente.

**`RateLimiter`**: Garante intervalo mínimo de 1 segundo entre requisições HTTP (asyncio Lock).

**Sincronização Standalone:** O script `scripts/sync_properties.py` permite executar a varredura do site localmente através da CLI para popular ou forçar a atualização do cache (ideal para agendadores externos).

**Multi-tenant:** A URL base é lida dinamicamente de `get_current_broker().site_base_url` (via `ContextVar`), com fallback para `settings.site_base_url`.

---

### 6.2 Gateway WhatsApp (Evolution API)

#### `EvolutionGateway` — `src/infrastructure/whatsapp/evolution_gateway.py`

Implementação de `IMessageGateway` que se comunica com a **Evolution API v2**.

**Endpoints utilizados:**

| Método | URL | Ação |
|---|---|---|
| `send_text` | `POST /message/sendText/{instance}` | Envia texto com delay simulado (1.2s padrão) |
| `send_image` | `POST /message/sendMedia/{instance}` | Envia imagem com legenda |
| `send_typing` | `POST /chat/sendPresence/{instance}` | Indica "digitando..." |

**Multi-tenant:** O `instance` é lido de `get_current_broker().instance_id` ou `settings.evolution_instance`.

**Timeout:** 10s para texto, 15s para mídia. Falhas são logadas mas não lançam exceção (resiliente).

---

### 6.3 Persistência

#### Session Store

| Implementação | Descrição |
|---|---|
| `MemorySessionStore` | Dict em memória, perde dados ao reiniciar. Para dev/testes. |
| `RedisSessionStore` | Persiste em Redis como JSON com TTL de 24h (86400s). Para produção. |

**Serialização da sessão:** JSON manual com campos primitivos. `ConversationStep` serializado como `.name`.

---

#### Subscription Store

| Implementação | Descrição |
|---|---|
| `MemorySubscriptionStore` | Dict em memória. Para dev/testes. |
| `RedisSubscriptionStore` | Persiste assinaturas e IDs notificados em Redis. TTL dos notificados: 7 dias (604800s). |

**Chaves Redis:**
- `subscription:{phone}` → dados da assinatura (JSON)
- `notified:{phone}:{listing_id}` → flag de notificação (TTL 7 dias)

---

#### Broker Profile Repository

| Implementação | Descrição |
|---|---|
| `MemoryBrokerProfileRepository` | Dict em memória. Para dev/testes. |
| `SqlBrokerProfileRepository` | PostgreSQL via SQLModel (tabela `brokerprofiles`). |

---

#### Message Log Repository

| Implementação | Descrição |
|---|---|
| `NullMessageLogRepository` | No-op (descarta logs). Padrão quando DB não configurado. |
| `SqlMessageLogRepository` | PostgreSQL via SQLModel (tabela `messagelogs`). |

---

#### Modelos ORM — `src/infrastructure/persistence/models.py`

Dois modelos SQLModel com conversão bidirecional para entidades de domínio:

```python
class MessageLogs(SQLModel, table=True):
    # Colunas: id, phone, direction, text, step, intent, created_at
    
class BrokerProfiles(SQLModel, table=True):
    # Colunas: instance_id (PK), broker_name, phone_number, site_base_url, bot_name, is_active, created_at
```

---

### 6.4 Cache

Interface implícita com métodos `get(key)`, `set(key, value, ttl_override=None)`, `delete(key)`.

| Implementação | Descrição |
|---|---|
| `MemoryCache` | Dict com TTL gerenciado por timestamp. Sem persistência. |
| `RedisCache` | Cache Redis com TTL nativo. Serialização via `pickle`. |

**TTL padrão:** Configurável via `cache_ttl_minutes` (padrão: 30 min).

**O que é cacheado:**
- `all_basic_listings` → listagem geral (30 min)
- `listings_type_{codigo}` → IDs filtrados por tipo (30 min)
- `property_detail_{id}` → detalhes de imóvel específico (30 min)

---

## 7. Camada de Apresentação

### 7.1 Webhook Principal

**Arquivo:** `src/presentation/webhook.py`
**Framework:** FastAPI

#### Ciclo de Vida (lifespan)

**Startup:**
1. Inicializa o container de DI via `get_container()`
2. Cria tabelas no PostgreSQL (se DB ativo)
3. Inicia o `AsyncIOScheduler` com o job `notify_new_listings.execute()` (intervalo: `notify_check_interval_minutes`, padrão: 15 min)

**Shutdown:**
1. Para o scheduler
2. Fecha o pool de conexões do DB

---

#### Endpoints

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| `GET` | `/health` | Status do bot e configurações | — |
| `GET` | `/test-scraping` | Debug do scraping com params `finalidade`, `bairro`, `tipo` | — |
| `POST` | `/test-mensagem` | Simula mensagem e captura respostas via `SpyMessageGateway` | — |
| `POST` | `/webhook` | Recebe eventos da Evolution API | `apikey` header |
| `GET/POST/DELETE` | `/api/admin/*` | Painel admin (logs, assinaturas, corretores) | JWT Bearer |
| `GET` | `/admin` | Dashboard estático (HTML/CSS/JS) | — |

---

#### Processamento do Webhook (`POST /webhook`)

1. Valida header `apikey` (se configurado)
2. Parseia JSON do body
3. Ignora eventos que não sejam `messages.upsert`
4. Ignora mensagens `fromMe` (enviadas pelo bot) e de grupos (`@g.us`)
5. Extrai `phone` e `text` (suporta `conversation`, `extendedTextMessage`, `buttonsResponseMessage`, `listResponseMessage`)
6. Lança `asyncio.create_task()` com o processamento isolado por contexto de corretor
7. Retorna `{"status": "processing"}` imediatamente (processamento assíncrono)

---

### 7.2 Painel Admin (API REST)

**Arquivo:** `src/presentation/admin_router.py`
**Prefixo:** `/api/admin`
**Autenticação:** JWT Bearer (via `get_current_admin` dependency)

| Endpoint | Descrição |
|---|---|
| `POST /login` | Login com usuário/senha → retorna JWT |
| `GET /logs?phone=&limit=` | Lista logs de mensagens (filtrado por phone ou todos) |
| `GET /subscriptions` | Lista assinaturas ativas |
| `DELETE /subscriptions/{phone}` | Cancela assinatura de um usuário |
| `GET /brokers` | Lista perfis de corretores |
| `POST /brokers` | Cria ou atualiza perfil de corretor |
| `DELETE /brokers/{instance_id}` | Exclui perfil de corretor |

---

## 8. Módulo Compartilhado (shared)

### 8.1 Container de Injeção de Dependências

**Arquivo:** `src/shared/container.py`

`create_container(settings)` é uma **factory function** que monta o grafo de dependências baseado nas configurações:

```python
{
    "redis_client": ...,
    "cache": MemoryCache | RedisCache,
    "property_repo": ExataPropertyRepository,
    "message_gateway": EvolutionGateway | MessageLogMiddleware(EvolutionGateway),
    "session_store": MemorySessionStore | RedisSessionStore,
    "subscription_store": MemorySubscriptionStore | RedisSubscriptionStore,
    "extractor": RegexPreferenceExtractor | LLMPreferenceExtractor,
    "handle_message": HandleMessageUseCase,
    "notify_new_listings": NotifyNewListingsUseCase,
    "log_repo": NullMessageLogRepository | SqlMessageLogRepository,
    "db_engine": None | AsyncEngine,
    "broker_repo": MemoryBrokerProfileRepository | SqlBrokerProfileRepository,
}
```

**Singleton global:** `get_container()` retorna o container já inicializado (lazy init na primeira chamada).

**Lógica de seleção:**
- `cache_type == "redis"` → `RedisCache`, senão `MemoryCache`
- `session_store_type == "redis"` → `RedisSessionStore`, senão `MemorySessionStore`
- `subscription_store_type == "redis"` → `RedisSubscriptionStore`, senão `MemorySubscriptionStore`
- `llm_provider in ("openai", "deepseek")` → `LLMPreferenceExtractor`, senão `RegexPreferenceExtractor`
- `message_log_enabled and database_url` → wraps gateway em `MessageLogMiddleware` + usa `SqlMessageLogRepository`
- `db_engine` existente → usa `SqlBrokerProfileRepository`, senão `MemoryBrokerProfileRepository`

---

### 8.2 Configurações (Settings)

**Arquivo:** `src/shared/config.py` — usa `pydantic-settings`

Lê variáveis de ambiente e dos arquivos `.env` e `.env.local`.

**Grupos de configuração:**

```
# Evolution API
EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE

# Bot
BOT_NAME, BUSINESS_HOURS_START, BUSINESS_HOURS_END, SITE_BASE_URL
CACHE_TTL_MINUTES, RESULTS_PAGE_SIZE, MAX_PHOTOS_PER_PROPERTY

# LLM (opcional)
LLM_PROVIDER (regex|openai|deepseek), OPENAI_API_KEY, DEEPSEEK_API_KEY

# Redis
REDIS_URL, SESSION_STORE_TYPE (memory|redis), CACHE_TYPE (memory|redis)

# Alertas
SUBSCRIPTION_STORE_TYPE (memory|redis), NOTIFY_CHECK_INTERVAL_MINUTES

# Banco de Dados
DATABASE_URL, MESSAGE_LOG_ENABLED

# Admin / JWT
ADMIN_USERNAME, ADMIN_PASSWORD_HASH (bcrypt), JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
```

---

### 8.3 Contexto Multi-Tenant

**Arquivo:** `src/shared/context.py`

Usa `contextvars.ContextVar` para isolar o perfil do corretor por tarefa assíncrona:

```python
current_broker: ContextVar[Optional[BrokerProfile]] = ContextVar("current_broker", default=None)

get_current_broker() -> Optional[BrokerProfile]
set_current_broker(profile) -> token  # Retorna token para reset
```

**Como funciona:**
- Ao receber um webhook, o `instance_id` da Evolution API é usado para carregar o `BrokerProfile` do banco
- `set_current_broker(profile)` é chamado antes de executar o use case
- `current_broker.reset(token)` é chamado no `finally` para limpar o contexto
- O `ExataPropertyRepository` e o `EvolutionGateway` leem `get_current_broker()` internamente para usar o `site_base_url` e `instance_id` corretos

---

### 8.4 Circuit Breaker

**Arquivo:** `src/shared/circuit_breaker.py`

Implementação genérica e assíncrona do padrão Circuit Breaker:

**Estados:**
- `CLOSED` → operação normal
- `OPEN` → bloqueia chamadas (lança `CircuitBreakerOpenException`)
- `HALF-OPEN` → testa recuperação após `recovery_timeout`

**Parâmetros padrão:** `failure_threshold=3`, `recovery_timeout=60.0s`

**Uso atual:** Protege chamadas ao LLM (`LLMPreferenceExtractor`)

---

### 8.5 Logger Estruturado

**Arquivo:** `src/shared/logger.py`

Usa `structlog` configurado. Log em formato estruturado (JSON em produção). Invocação:

```python
from src.shared.logger import logger

logger.info("Mensagem", chave=valor, outra_chave=outro_valor)
logger.error("Erro", error=str(e))
logger.warning("Aviso", phone=phone)
```

---

## 9. Fluxo Completo de uma Mensagem

```
[WhatsApp do Cliente]
        │
        ▼
[Evolution API]
  POST /webhook
        │
        ▼
[webhook.py] 
  Valida apikey
  Parseia payload
  Extrai phone + text
  asyncio.create_task(run_with_broker_context)
  Retorna {"status": "processing"}
        │
        ▼ (async, em background)
[run_with_broker_context]
  Carrega BrokerProfile por instance_id
  set_current_broker(profile) → ContextVar
        │
        ▼
[HandleMessageUseCase.execute(phone, text)]
  1. Verifica horário de atendimento
  2. session_store.get_or_create(phone) → Session
  3. session.increment_messages()
  4. session.history.append("Cliente: {text}")
  5. log_repo.save(MessageLog(direction="in")) [async task]
  6. Se step ∉ {SHOWING, DETAIL}:
       extractor.extract(text, history) → {intent, property_type, ...}
       session.update_preferences(**extracted)
  7. Loop (max 5):
       handler = handlers[session.step]
       should_continue = await handler.handle(session, text)
       if step unchanged or not should_continue: break
  8. session_store.save(session)
        │
        ▼
[Handler correspondente]
  Executa lógica do estado
  Chama message_gateway.send_text/send_image/send_typing
  Transiciona session.step se necessário
  Retorna bool
        │
        ▼
[EvolutionGateway] (ou MessageLogMiddleware wrapping it)
  POST /message/sendText/{instance}
  Registra log de saída se MessageLogMiddleware ativo
        │
        ▼
[WhatsApp do Cliente]
  Recebe resposta da "Ana"
```

---

## 10. Fluxo de Alertas Proativos

```
[APScheduler] (a cada notify_check_interval_minutes = 15 min)
        │
        ▼
[NotifyNewListingsUseCase.execute()]
  1. subscription_store.list_all() → lista de Subscriptions
  2. Para cada Subscription:
       a. Cria Session fake com os parâmetros da assinatura
       b. property_repo.find_by_preferences(fake_session) → listings
       c. Filtra: sub.matches(listing) == True
       d. Filtra: subscription_store.is_notified(phone, listing.id) == False
       e. Para cada novo imóvel:
            - message_gateway.send_image() (se tiver foto)
            - message_gateway.send_text(alerta formatado)
            - subscription_store.mark_notified(phone, listing.id)
```

---

## 11. Multi-Tenancy (Suporte a Múltiplos Corretores)

O sistema suporta múltiplos corretores/imobiliárias, cada um com sua instância do WhatsApp na Evolution API.

**Como funciona:**

1. Cada corretor possui um `BrokerProfile` com `instance_id` único (=nome da instância na Evolution API)
2. Ao receber um webhook, o `instance_id` vem no campo `payload["instance"]`
3. O sistema carrega o `BrokerProfile` correspondente via `broker_repo.get_by_instance(instance_id)`
4. O perfil é armazenado no `ContextVar current_broker` para a duração do processamento
5. `ExataPropertyRepository.site_base_url` lê o `broker.site_base_url` → scraping isolado por corretor
6. `EvolutionGateway.instance` lê o `broker.instance_id` → envios isolados por instância

**Sessões:** As sessões dos clientes são compartilhadas por `phone` (independente do corretor). Uma melhoria futura seria prefixar as chaves de sessão com o `instance_id`.

---

## 12. Infraestrutura Docker

### Serviços (`docker-compose.yml`)

| Serviço | Imagem | Porta | Função |
|---|---|---|---|
| `exatabot` | Dockerfile local | `8000:8000` | Aplicação principal |
| `evolution-api` | `atendai/evolution-api:latest` | `8080:8080` | Gateway WhatsApp |
| `redis` | `redis:7-alpine` | `6379:6379` | Cache + sessões + assinaturas |
| `postgres` | `postgres:16-alpine` | `5432:5432` | Banco de dados (logs + corretores) |

**Rede interna:** `exatabot-network` (bridge). Os serviços se comunicam pelo nome do container.

**Healthcheck do exatabot:** `GET /health` a cada 30s.

**Volumes persistentes:** `evolution_data`, `redis_data`, `postgres_data`

### Dockerfile (multi-stage simplificado)
- Base: `python:3.12-slim`
- Instala dependências via `pip` do `pyproject.toml`
- Cmd: `uvicorn main:app --host 0.0.0.0 --port 8000`

### Configuração de desenvolvimento (`docker-compose.dev.yml`)
- Apenas Redis + Evolution API (sem Postgres)
- Usa stores in-memory

---

## 13. Variáveis de Ambiente

Arquivo de referência: `.env.example`. Arquivo local: `.env.local` (não versionado).

### Mínimo obrigatório para produção

```env
EVOLUTION_API_KEY=sua_chave_aqui
EVOLUTION_INSTANCE=nome_da_instancia

# Para Redis
REDIS_URL=redis://redis:6379/0
SESSION_STORE_TYPE=redis
CACHE_TYPE=redis
SUBSCRIPTION_STORE_TYPE=redis

# Para banco de dados
DATABASE_URL=postgresql+asyncpg://postgres:senha@postgres:5432/exatabot
MESSAGE_LOG_ENABLED=true

# Para painel admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...  # bcrypt hash
JWT_SECRET_KEY=chave_secreta_muito_longa

# Opcional: LLM
LLM_PROVIDER=openai  # ou deepseek
OPENAI_API_KEY=sk-...
```

---

## 14. Testes

### Estrutura de testes

```
tests/
├── fakes/
│   └── spy_message_gateway.py  # Captura calls ao gateway para assertions
├── unit/
│   ├── test_handle_message.py  # Testa o orquestrador com fakes
│   ├── test_session.py
│   ├── test_subscription.py
│   ├── test_regex_extractor.py
│   ├── test_llm_extractor.py
│   ├── test_circuit_breaker.py
│   ├── test_message_log_middleware.py
│   ├── test_notify_new_listings.py
│   ├── test_admin_router.py
│   ├── test_auth_service.py
│   ├── test_fakes.py
│   ├── test_money.py
│   ├── test_phone_number.py
│   ├── test_multi_tenant_concurrency.py
│   ├── test_redis_cache.py
│   ├── test_redis_store.py
│   ├── test_redis_subscription_store.py
│   ├── test_sql_broker_profile_repository.py  # SQLite in-memory
│   ├── test_sql_log_repository.py             # SQLite in-memory
│   └── test_null_log_repository.py
└── integration/
    └── (testes de integração com internet real)
```

### Comandos

```bash
# Todos os testes (sem integração)
pytest tests/unit/ -v

# Com cobertura
pytest tests/unit/ --cov=src --cov-report=html

# Testes de integração (requerem internet)
pytest tests/integration/ -m integration -v
```

### `SpyMessageGateway`

Test double que implementa `IMessageGateway` e captura os envios:

```python
spy.sent_texts    # list[{"phone": str, "text": str}]
spy.sent_images   # list[{"phone": str, "image_url": str, "caption": str}]
```

---

## 15. Padrões de Design Adotados

| Padrão | Onde usado |
|---|---|
| **Clean Architecture** | Organização em 4 camadas com inversão de dependências |
| **Repository** | `IPropertyRepository`, `ISessionStore`, etc. com implementações intercambiáveis |
| **Strategy** | `IPreferenceExtractor` → `RegexPreferenceExtractor` ou `LLMPreferenceExtractor` |
| **State Machine** | `ConversationStep` + handlers individuais por estado |
| **Factory** | `create_container(settings)` para montagem do grafo de DI |
| **Decorator** | `MessageLogMiddleware` sobre `EvolutionGateway` |
| **Circuit Breaker** | `CircuitBreaker` protegendo chamadas ao LLM |
| **Null Object** | `NullMessageLogRepository` para ambientes sem banco |
| **Context Variable** | `ContextVar[BrokerProfile]` para isolamento de contexto async |

---

## 16. Convenções de Código

### Nomenclatura

- **Interfaces:** prefixo `I` + PascalCase → `IPropertyRepository`, `IMessageGateway`
- **Implementações de memória:** `Memory` + PascalCase → `MemorySessionStore`
- **Implementações Redis:** `Redis` + PascalCase → `RedisSessionStore`
- **Implementações SQL:** `Sql` + PascalCase → `SqlBrokerProfileRepository`
- **Entidades:** PascalCase puro → `Session`, `PropertyListing`
- **Value Objects:** PascalCase puro → `Money`, `PhoneNumber`
- **Handlers:** PascalCase + `Handler` → `StartHandler`, `ShowingHandler`
- **Use Cases:** PascalCase + `UseCase` → `HandleMessageUseCase`
- **Modelos ORM:** PascalCase plural → `MessageLogs`, `BrokerProfiles`

### Padrões técnicos

- Código **100% assíncrono** (`async/await`). Não usar operações síncronas bloqueantes.
- **Type hints** obrigatórios em todas as funções e classes (mypy strict).
- **Docstrings** em português para todos os métodos e classes públicas.
- Logs via `logger` do `shared/logger.py` com campos estruturados.
- **Nunca importar infraestrutura no domínio.** Nunca importar aplicação no domínio.
- Novos repositórios: criar interface em `domain/repositories/`, implementações em `infrastructure/`.
- Novos casos de uso: criar em `application/use_cases/`.
- Registrar novas dependências no `container.py`.

### Adicionando um novo `ConversationStep`

1. Adicionar ao enum `ConversationStep` em `session.py`
2. Criar o handler em `application/use_cases/handlers/`
3. Registrar no dict `_handlers` de `HandleMessageUseCase.__init__`
4. Escrever testes unitários no handler e no `test_handle_message.py`

### Adicionando um novo repositório

1. Criar interface em `src/domain/repositories/i_<nome>.py`
2. Implementar em `src/infrastructure/persistence/` (memory + redis ou sql conforme necessidade)
3. Injetar em `src/shared/container.py`
4. Adicionar ao `HandleMessageUseCase` ou use case relevante via construtor
5. Criar testes com fakes

---

## 17. Roadmap e Fases de Desenvolvimento

| Fase | Status | Descrição |
|---|---|---|
| **Fase 1** | ✅ | Fundação da Clean Architecture — entidades, interfaces, DI container, configurações |
| **Fase 2** | ✅ | Infraestrutura — scraper, Evolution gateway, memory stores, fakes |
| **Fase 3** | ✅ | Casos de uso — HandleMessageUseCase, máquina de estados completa, extratores |
| **Fase 4** | ✅ | Containerização Docker — Dockerfile, docker-compose, scripts de setup |
| **Fase 5** | ✅ | Extrator LLM — LLMPreferenceExtractor + CircuitBreaker + DeepSeek/OpenAI |
| **Fase 6** | ✅ | Redis — RedisCache, RedisSessionStore, testes de integração Redis |
| **Fase 7** | ✅ | Alertas proativos — Subscription, RedisSubscriptionStore, NotifyNewListingsUseCase, APScheduler |
| **Fase 8A** | ✅ | Logs de mensagens — MessageLog, SqlMessageLogRepository, MessageLogMiddleware, Alembic |
| **Fase 8B** | ✅ | Multi-tenancy — BrokerProfile, SqlBrokerProfileRepository, ContextVar |
| **Fase 8C** | ✅ | Painel admin — AdminRouter, JWT Auth, Dashboard estático |
| **Fase 9+** | 🔲 | Futuras melhorias (ver abaixo) |

### Possíveis melhorias futuras (Fase 9+)

- **Isolamento de sessão por tenant**: prefixar chaves de sessão com `instance_id`
- **Suporte a áudio**: transcrição de mensagens de voz via Whisper API
- **Suporte a imagens recebidas**: análise de plantas e fotos enviadas pelo cliente
- **Webhook de retorno do Evolution API**: confirmação de entrega e leitura
- **Paginação do painel admin**: API de logs com cursor-based pagination
- **Rate limiting por cliente**: evitar abuso de mensagens em sequência
- **Métricas**: integração com Prometheus/Grafana para monitoramento
- **Testes de carga**: validar comportamento sob alta concorrência
- **Cache distribuído de sessão**: compartilhamento entre múltiplas instâncias do bot

---

*Documentação gerada em: Junho/2026 — versão do sistema: 0.3.0*

---

## 18. Como Executar e Testar

### 18.1 Pré-requisitos

| Ferramenta | Versão mínima | Verificação |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | v2 (plugin) | `docker compose version` |
| curl | qualquer | `curl --version` |
| jq | qualquer | `jq --version` |

---

### 18.2 Modo 1 — Desenvolvimento Local (sem Docker, testes mais rápidos)

Ideal para rodar testes e iterar no código sem depender de containers.

#### Passo 1 — Criar e ativar o ambiente virtual

```bash
cd /Users/alexandrerocha/botexata
python -m venv .venv
source .venv/bin/activate
```

#### Passo 2 — Instalar dependências

```bash
pip install -e ".[dev]"
```

> Instala todas as dependências do `pyproject.toml` incluindo as de desenvolvimento (pytest, mypy, ruff, aiosqlite).

#### Passo 3 — Configurar o `.env.local`

O arquivo `.env.local` já existe e contém configurações prontas para desenvolvimento local:
- Usa **stores em memória** (sem Redis/PostgreSQL)
- `LLM_PROVIDER=regex` (sem chamadas a APIs pagas)
- `MESSAGE_LOG_ENABLED=false` (sem banco de dados)
- `DATABASE_URL=sqlite+aiosqlite:///exatabot.db` (SQLite local se ativado)
- Senha admin: `admin123` (hash já configurado)

Se quiser ajustar algo:

```bash
# Editar configurações locais
nano .env.local
```

#### Passo 4 — Rodar o servidor local

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

O servidor sobe em: **http://localhost:8000**

> **Nota:** Sem a Evolution API rodando, o bot consegue processar mensagens internamente mas não conseguirá enviar respostas de WhatsApp para um número real. Use o endpoint `/test-mensagem` para simular.

---

### 18.3 Modo 2 — Docker Compose (ambiente completo)

#### Opção A — Setup automatizado com o script

```bash
cd /Users/alexandrerocha/botexata

# Garante permissão de execução
chmod +x scripts/setup.sh

# Roda o setup completo
bash scripts/setup.sh
```

O script:
1. Verifica dependências (`docker`, `curl`, `jq`)
2. Cria o `.env` a partir do `.env.local` ou `.env.example`
3. Sobe todos os containers (`docker compose up -d`)
4. Aguarda a Evolution API ficar ativa
5. Cria a instância do WhatsApp se não existir
6. Exibe a URL do QR Code para pareamento

#### Opção B — Subir manualmente

```bash
# Produção (Redis + PostgreSQL + Evolution API + ExataBot)
docker compose up -d

# Ver logs em tempo real
docker compose logs -f exatabot

# Parar tudo
docker compose down
```

#### Opção C — Apenas dependências (Redis + Evolution API) com app local

Útil para ter hot-reload no código sem reconstruir imagens:

```bash
# Sobe só Redis e Evolution API
docker compose up -d redis evolution-api

# Roda o app localmente com hot-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 18.4 Verificar se o Bot está Rodando

```bash
# Health check
curl http://localhost:8000/health
```

Resposta esperada:
```json
{
  "status": "ok",
  "bot_name": "Ana",
  "llm_provider": "regex",
  "instance": "exatabot",
  "site_url": "https://www.exataservicos.net"
}
```

```bash
# Documentação interativa da API (Swagger UI)
open http://localhost:8000/docs

# Painel admin
open http://localhost:8000/admin
```

---

### 18.5 Testar o Scraping

Verifica se o scraping do site exataservicos.net está funcionando, sem precisar de WhatsApp:

```bash
# Busca imóveis de Locação no bairro Centro
curl "http://localhost:8000/test-scraping?finalidade=Loca%C3%A7%C3%A3o&bairro=Centro"

# Busca casas para Venda
curl "http://localhost:8000/test-scraping?finalidade=Venda&tipo=casa"

# Busca apartamentos para locação
curl "http://localhost:8000/test-scraping?finalidade=Loca%C3%A7%C3%A3o&tipo=apartamento&bairro=Derby"
```

Retorna uma lista de imóveis em JSON. Se retornar `[]`, o site pode estar indisponível ou sem resultados.

---

### 18.6 Simular uma Conversa Completa (sem WhatsApp real)

O endpoint `/test-mensagem` simula toda a lógica do bot e retorna o que a "Ana" responderia, **sem enviar nada pelo WhatsApp**:

```bash
# Simular primeira mensagem (boas-vindas)
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=oi"

# Responder que quer locação
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=locacao"

# Informar preferências
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=quero+um+apartamento+no+centro+ate+1200"

# Ver mais imóveis
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=mais"

# Ver detalhe do primeiro imóvel
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=1"

# Voltar para a lista
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=voltar"

# Ativar alertas
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=alertar"

# Reiniciar a conversa
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=reiniciar"
```

Resposta esperada:
```json
{
  "phone": "5588999999999",
  "sent_texts": ["Olá! Sou a Ana..."],
  "sent_images": []
}
```

> **Importante:** O estado da sessão é mantido entre chamadas (mesmo número de telefone). Para reiniciar do zero, use um número diferente ou envie `"reiniciar"`.

---

### 18.7 Testar o Painel Administrativo

#### Login e obtenção do token JWT

```bash
# As credenciais padrão do .env.local são admin / admin123
curl -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Resposta:
```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

```bash
# Salvar o token em variável (copie o valor do access_token)
TOKEN="eyJ..."

# Listar logs de mensagens
curl http://localhost:8000/api/admin/logs \
  -H "Authorization: Bearer $TOKEN"

# Listar logs de um número específico
curl "http://localhost:8000/api/admin/logs?phone=5588999999999" \
  -H "Authorization: Bearer $TOKEN"

# Listar assinaturas de alerta
curl http://localhost:8000/api/admin/subscriptions \
  -H "Authorization: Bearer $TOKEN"

# Cancelar assinatura
curl -X DELETE http://localhost:8000/api/admin/subscriptions/5588999999999 \
  -H "Authorization: Bearer $TOKEN"

# Listar corretores
curl http://localhost:8000/api/admin/brokers \
  -H "Authorization: Bearer $TOKEN"

# Cadastrar novo corretor
curl -X POST http://localhost:8000/api/admin/brokers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "minha_instancia",
    "broker_name": "João Corretor",
    "phone_number": "5588999998888",
    "site_base_url": "https://www.exataservicos.net",
    "bot_name": "Ana",
    "is_active": true
  }'
```

Ou acesse o dashboard visual em: **http://localhost:8000/admin**

---

### 18.8 Executar os Testes Automatizados

#### Testes unitários (sem internet, sem Docker)

```bash
# Ativar o venv se necessário
source .venv/bin/activate

# Rodar todos os testes unitários
pytest tests/unit/ -v

# Com relatório de cobertura
pytest tests/unit/ --cov=src --cov-report=term-missing

# Gerar relatório HTML de cobertura
pytest tests/unit/ --cov=src --cov-report=html
open htmlcov/index.html

# Rodar um arquivo de teste específico
pytest tests/unit/test_handle_message.py -v

# Rodar um teste específico pelo nome
pytest tests/unit/test_handle_message.py::test_nome_do_teste -v

# Rodar com output detalhado de prints/logs
pytest tests/unit/ -v -s
```

#### Testes de integração (requerem internet)

```bash
# Rodar apenas testes marcados como integration
pytest tests/integration/ -m integration -v
```

> Os testes de integração fazem requests reais ao site `exataservicos.net` e ao Redis. Certifique-se de ter conexão com a internet e Redis rodando.

#### Checar qualidade de código

```bash
# Linting com ruff
ruff check src/ tests/

# Type checking com mypy
mypy src/

# Auto-formatar
ruff format src/ tests/
```

---

### 18.9 Conectar o WhatsApp Real (Produção)

1. **Suba os containers** com `bash scripts/setup.sh` ou `docker compose up -d`

2. **Obtenha o QR Code** para parear o WhatsApp:
   ```bash
   # Abrir imagem do QR Code no navegador
   open http://localhost:8080/instance/qrcode/exatabot/image
   ```

3. **Escaneie o QR Code** com o WhatsApp do número que será o bot (no celular: *Aparelhos conectados → Conectar aparelho*)

4. **Verifique o status da conexão:**
   ```bash
   curl -H "apikey: minha_chave_secreta_forte" \
     http://localhost:8080/instance/connectionState/exatabot
   ```
   Resposta esperada: `{"instance": {"state": "open"}}`

5. **Configurar o webhook** na Evolution API (o `setup.sh` faz isso automaticamente via variável `WEBHOOK_GLOBAL_URL=http://exatabot:8000/webhook`):
   ```bash
   # Verificar se o webhook está configurado
   curl -H "apikey: minha_chave_secreta_forte" \
     http://localhost:8080/webhook/find/exatabot
   ```

6. **Enviar uma mensagem de teste** do celular para o número pareado e verificar os logs:
   ```bash
   docker compose logs -f exatabot
   ```

---

### 18.10 Comandos Úteis de Operação

```bash
# Ver logs do bot em tempo real
docker compose logs -f exatabot

# Ver logs de todos os serviços
docker compose logs -f

# Reiniciar apenas o bot (sem recriar containers de deps)
docker compose restart exatabot

# Reconstruir a imagem após mudanças no código
docker compose build exatabot && docker compose up -d exatabot

# Verificar status dos containers
docker compose ps

# Acessar o Redis interativamente
docker exec -it exatabot-redis redis-cli

# Ver todas as sessões salvas no Redis
docker exec -it exatabot-redis redis-cli --scan --pattern 'session:*'

# Ver todas as assinaturas
docker exec -it exatabot-redis redis-cli --scan --pattern 'subscription:*'

# Acessar o PostgreSQL interativamente
docker exec -it exatabot-postgres psql -U postgres -d exatabot

# Contar mensagens no banco
docker exec -it exatabot-postgres psql -U postgres -d exatabot -c "SELECT COUNT(*) FROM messagelogs;"
```

---

### 18.11 Solução de Problemas Comuns

#### Bot não responde às mensagens

1. Checar se o webhook está registrado: `curl http://localhost:8000/health`
2. Checar logs do bot: `docker compose logs --tail=50 exatabot`
3. Verificar se a Evolution API está pareada: status da instância
4. Confirmar que a `EVOLUTION_API_KEY` é a mesma nos dois serviços

#### Scraping retorna lista vazia

1. Testar diretamente: `curl "http://localhost:8000/test-scraping?finalidade=Locação"`
2. Verificar se o site `exataservicos.net` está acessível
3. Limpar cache Redis: `docker exec -it exatabot-redis redis-cli FLUSHALL`
4. Verificar a variável `SITE_BASE_URL` no `.env`

#### Erro de autenticação no painel admin

1. Confirmar que `ADMIN_PASSWORD_HASH` é um hash bcrypt válido
2. Gerar novo hash: `python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('suasenha'))"`
3. Verificar se `JWT_SECRET_KEY` está definida

#### Testes falhando com `ModuleNotFoundError`

```bash
# Garantir que o pacote está instalado em modo editável
pip install -e ".[dev]"
```

#### Sessões perdidas ao reiniciar o bot

Isso é esperado quando `SESSION_STORE_TYPE=memory`. Para persistir sessões entre reinicializações, configure:
```env
SESSION_STORE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
```
