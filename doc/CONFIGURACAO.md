# ExataBot — Guia de Configuração

> Referência completa de todas as variáveis de ambiente, modos de operação e comportamentos configuráveis do ExataBot.

---

## Índice

1. [Arquivo de Configuração](#1-arquivo-de-configuração)
2. [Configurações do Gateway WhatsApp (Evolution API)](#2-configurações-do-gateway-whatsapp-evolution-api)
3. [Configurações do Chatbot](#3-configurações-do-chatbot)
4. [Configurações do Scraper e Cache](#4-configurações-do-scraper-e-cache)
5. [Configurações de Inteligência Artificial (LLM)](#5-configurações-de-inteligência-artificial-llm)
6. [Configurações do Redis](#6-configurações-do-redis)
7. [Configurações de Alertas Proativos](#7-configurações-de-alertas-proativos)
8. [Configurações de Banco de Dados e Logs](#8-configurações-de-banco-de-dados-e-logs)
9. [Configurações do Painel Administrativo](#9-configurações-do-painel-administrativo)
10. [Perfis de Ambiente](#10-perfis-de-ambiente)
11. [Como Funciona a Extração de Preferências](#11-como-funciona-a-extração-de-preferências)
12. [Como Funciona a Máquina de Estados](#12-como-funciona-a-máquina-de-estados)
13. [Comandos Reconhecidos pelo Bot](#13-comandos-reconhecidos-pelo-bot)
14. [Configuração de Multi-Tenant (Múltiplos Corretores)](#14-configuração-de-multi-tenant-múltiplos-corretores)
15. [Gerar Hash de Senha para o Painel Admin](#15-gerar-hash-de-senha-para-o-painel-admin)

---

## 1. Arquivo de Configuração

O ExataBot usa `pydantic-settings` para carregar configurações de **variáveis de ambiente** ou de arquivos `.env`. A ordem de prioridade é:

```
Variável de ambiente do sistema
  → .env.local   (uso local, não versionado)
    → .env        (produção, gerado pelo setup.sh)
      → valor padrão da classe Settings
```

**Arquivos disponíveis no projeto:**

| Arquivo | Propósito | Versionado? |
|---|---|---|
| `.env.example` | Template com todas as variáveis documentadas | ✅ Sim |
| `.env.local` | Configuração local de desenvolvimento | ❌ Não |
| `.env` | Configuração de produção (gerado pelo setup.sh) | ❌ Não |

**Para criar seu arquivo de configuração:**

```bash
# Desenvolvimento local
cp .env.example .env.local
nano .env.local

# Produção (o setup.sh faz isso automaticamente)
cp .env.local .env
```

---

## 2. Configurações do Gateway WhatsApp (Evolution API)

| Variável | Padrão | Obrigatório | Descrição |
|---|---|---|---|
| `EVOLUTION_API_URL` | `http://localhost:8080` | ✅ | URL da Evolution API. Dentro do Docker use `http://evolution-api:8080` |
| `EVOLUTION_API_KEY` | — | ✅ | Chave de autenticação. **Deve ser a mesma** nos dois serviços |
| `EVOLUTION_INSTANCE` | `exatabot` | ✅ | Nome da instância/linha do WhatsApp |

**Exemplo:**

```env
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=minha_chave_super_secreta_123
EVOLUTION_INSTANCE=exatabot
```

> ⚠️ **Atenção:** A `EVOLUTION_API_KEY` é usada para autenticar o webhook recebido. Se os valores divergirem entre o bot e a Evolution API, o webhook retornará `401 Unauthorized`.

---

## 3. Configurações do Chatbot

| Variável | Padrão | Descrição |
|---|---|---|
| `BOT_NAME` | `Ana` | Nome da atendente virtual exibido nas mensagens |
| `BUSINESS_HOURS_START` | `8` | Hora de início do atendimento (formato 24h) |
| `BUSINESS_HOURS_END` | `18` | Hora de término do atendimento (formato 24h) |

**Horário de atendimento:** O bot atende de **Segunda a Sexta**, entre `BUSINESS_HOURS_START` e `BUSINESS_HOURS_END`. Fora desse horário, o bot responde com uma mensagem padrão e não processa a conversa.

**Exemplos de configuração:**

```env
# Atendimento comercial padrão
BOT_NAME=Ana
BUSINESS_HOURS_START=8
BUSINESS_HOURS_END=18

# Atendimento estendido
BOT_NAME=Sofia
BUSINESS_HOURS_START=7
BUSINESS_HOURS_END=20
```

**Personalização do nome do bot por corretor:** O nome também pode ser configurado individualmente por perfil de corretor no painel admin (campo `bot_name`), sobrepondo a configuração global.

---

## 4. Configurações do Scraper e Cache

| Variável | Padrão | Descrição |
|---|---|---|
| `SITE_BASE_URL` | `https://www.exataservicos.net` | URL base do site de imóveis para scraping |
| `CACHE_TTL_MINUTES` | `30` | Tempo de cache dos resultados de scraping (em minutos) |
| `RESULTS_PAGE_SIZE` | `3` | Quantidade de imóveis exibidos por página na conversa |
| `MAX_PHOTOS_PER_PROPERTY` | `3` | Número máximo de fotos enviadas ao detalhar um imóvel |

**Como o cache funciona:**

```
Primeira busca → scraping do site → resultado salvo no cache por 30 min
Segunda busca (mesmos critérios dentro de 30 min) → retorna do cache
```

O cache evita sobrecarregar o site com requisições repetidas. O TTL pode ser ajustado conforme a frequência de atualização dos anúncios:

```env
# Atualização mais frequente (mais requisições ao site)
CACHE_TTL_MINUTES=10

# Atualização mais lenta (menos requisições, dados podem ficar desatualizados)
CACHE_TTL_MINUTES=60
```

**URL do site por corretor:** Em modo multi-tenant, cada `BrokerProfile` possui seu próprio `site_base_url`, sobrepondo `SITE_BASE_URL`. Configure via painel admin.

---

## 5. Configurações de Inteligência Artificial (LLM)

| Variável | Padrão | Opções | Descrição |
|---|---|---|---|
| `LLM_PROVIDER` | `regex` | `regex`, `openai`, `deepseek` | Motor de extração de preferências |
| `OPENAI_API_KEY` | — | — | Chave da API OpenAI (apenas se `LLM_PROVIDER=openai`) |
| `DEEPSEEK_API_KEY` | — | — | Chave da API DeepSeek (apenas se `LLM_PROVIDER=deepseek`) |

### Modo `regex` (padrão, sem custo)

Usa expressões regulares e listas de palavras-chave para extrair intenções. É rápido, offline e sem custo, mas menos flexível para linguagem natural complexa.

**O que o extrator regex reconhece:**

| Campo | Exemplos de mensagem |
|---|---|
| **Intenção** (Locação/Venda) | "quero alugar", "locação", "comprar", "venda" |
| **Tipo de imóvel** | "casa", "apartamento", "apto", "quitinete", "kitnet", "galpão", "terreno", "sala", "sítio", "lote" |
| **Bairro** (Sobral/CE) | "centro", "derby", "junco", "pedrinhas", "renato parente", "cohab", "domingos olímpio", "betânia", "alto do cristo", "recanto", "terrenos novos", "sinhá sabóia" |
| **Valor máximo** | "até 1200", "R$ 1.500", "1,5 mil", "máximo de 2000" |
| **Nome do cliente** | "me chamo João", "meu nome é Maria", "sou o Carlos", "sou a Ana" |

### Modo `openai` ou `deepseek` (LLM, recomendado para produção)

Usa um modelo de linguagem para extrair preferências de forma muito mais flexível, entendendo linguagem natural complexa, gírias e frases indiretas.

**Modelos utilizados:**
- OpenAI: `gpt-4o-mini`
- DeepSeek: `deepseek-chat`

**Campos extras que o LLM extrai** (além dos do Regex):
- `quartos_min` — número mínimo de quartos
- `pet_friendly` — aceita animais
- `garagem` — tem garagem
- `mobiliado` — imóvel mobiliado
- `cidade` — cidade mencionada

> **Circuit Breaker:** Se o LLM falhar 3 vezes consecutivas, o sistema bloqueia chamadas por 60 segundos e usa o extrator Regex como fallback automaticamente.

```env
# Usar OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...

# Usar DeepSeek (geralmente mais barato)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...

# Sem LLM (padrão)
LLM_PROVIDER=regex
```

---

## 6. Configurações do Redis

| Variável | Padrão | Opções | Descrição |
|---|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | — | URL de conexão ao Redis |
| `SESSION_STORE_TYPE` | `memory` | `memory`, `redis` | Onde as sessões de conversa são armazenadas |
| `CACHE_TYPE` | `memory` | `memory`, `redis` | Onde o cache do scraper é armazenado |

**Diferenças entre os modos:**

| | `memory` | `redis` |
|---|---|---|
| **Sessões perdidas ao reiniciar** | ✅ Sim (perde tudo) | ❌ Não (persiste no Redis) |
| **Suporte a múltiplas instâncias do bot** | ❌ Não | ✅ Sim |
| **Dependência externa** | ❌ Nenhuma | ✅ Redis rodando |
| **Recomendado para** | Desenvolvimento/testes | Produção |

**TTL das sessões no Redis:** 24 horas (86400 segundos). Sessões inativas por mais de 24h são automaticamente removidas.

```env
# Desenvolvimento (sem Redis)
SESSION_STORE_TYPE=memory
CACHE_TYPE=memory

# Produção (com Redis)
REDIS_URL=redis://redis:6379/0
SESSION_STORE_TYPE=redis
CACHE_TYPE=redis
```

---

## 7. Configurações de Alertas Proativos

| Variável | Padrão | Opções | Descrição |
|---|---|---|---|
| `SUBSCRIPTION_STORE_TYPE` | `memory` | `memory`, `redis` | Onde as assinaturas de alerta são armazenadas |
| `NOTIFY_CHECK_INTERVAL_MINUTES` | `15` | — | Intervalo de verificação de novos imóveis (em minutos) |

**Como funcionam os alertas:**

1. O usuário finaliza uma busca e digita `alertar` no chat
2. O sistema salva uma `Subscription` com as preferências do usuário (tipo, bairro, valor)
3. A cada `NOTIFY_CHECK_INTERVAL_MINUTES`, o bot busca novos imóveis no site
4. Se encontrar imóvel que não foi notificado ainda → envia alerta via WhatsApp
5. O ID do imóvel notificado é salvo por **7 dias** para evitar spam

```env
# Verificar novos imóveis a cada 15 minutos
NOTIFY_CHECK_INTERVAL_MINUTES=15

# Armazenar assinaturas no Redis (recomendado para produção)
SUBSCRIPTION_STORE_TYPE=redis
```

---

## 8. Configurações de Banco de Dados e Logs

| Variável | Padrão | Descrição |
|---|---|---|
| `MESSAGE_LOG_ENABLED` | `false` | Habilitar persistência de logs de mensagens no banco |
| `DATABASE_URL` | — | URL de conexão async ao PostgreSQL ou SQLite |

**Quando ativado**, o banco de dados armazena:
- Todas as mensagens recebidas e enviadas
- Estado da conversa no momento de cada mensagem
- Intenção detectada

**Tabelas criadas automaticamente no startup:**
- `messagelogs` — logs de mensagens
- `brokerprofiles` — perfis de corretores

```env
# Produção com PostgreSQL (via Docker)
MESSAGE_LOG_ENABLED=true
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/exatabot

# Desenvolvimento local com SQLite
MESSAGE_LOG_ENABLED=true
DATABASE_URL=sqlite+aiosqlite:///exatabot.db
```

> **Nota:** Se `MESSAGE_LOG_ENABLED=false` ou `DATABASE_URL` estiver vazio, o sistema usa `NullMessageLogRepository` (descarta logs silenciosamente) e `MemoryBrokerProfileRepository`. O bot funciona normalmente sem banco de dados.

---

## 9. Configurações do Painel Administrativo

| Variável | Padrão | Descrição |
|---|---|---|
| `ADMIN_USERNAME` | `admin` | Usuário de login do painel admin |
| `ADMIN_PASSWORD_HASH` | — | Hash bcrypt da senha do admin |
| `JWT_SECRET_KEY` | `exatabot_super_secret_key_change_me` | Chave para assinar tokens JWT |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT |
| `JWT_EXPIRATION_MINUTES` | `120` | Validade do token JWT em minutos |

> ⚠️ **CRÍTICO:** Mude `JWT_SECRET_KEY` para uma string aleatória longa em produção. O valor padrão é inseguro.

**Acessar o painel admin:** `http://localhost:8000/admin`

**Endpoints da API admin:** Prefixo `/api/admin` — requerem token JWT via header `Authorization: Bearer <token>`.

---

## 10. Perfis de Ambiente

### Desenvolvimento Local (`.env.local` atual)

```env
# Gateway
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=minha_chave_secreta_forte
EVOLUTION_INSTANCE=exatabot

# Bot
BOT_NAME=Ana
BUSINESS_HOURS_START=8
BUSINESS_HOURS_END=18
SITE_BASE_URL=https://www.exataservicos.net
CACHE_TTL_MINUTES=30
RESULTS_PAGE_SIZE=3
MAX_PHOTOS_PER_PROPERTY=3

# LLM - modo regex (sem custo)
LLM_PROVIDER=regex

# Stores em memória (sem Redis)
SESSION_STORE_TYPE=memory
CACHE_TYPE=memory
SUBSCRIPTION_STORE_TYPE=memory

# Sem banco de dados
MESSAGE_LOG_ENABLED=false
DATABASE_URL=sqlite+aiosqlite:///exatabot.db

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$Zsz0GgBqN/7WJ9DkC/3F7un69K1FzH8p.zG9T6jH6y6.2.X7.xW.O
JWT_SECRET_KEY=chave_local_teste
```

### Produção (`.env` gerado pelo `setup.sh`)

```env
# Gateway (URL interna do Docker)
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=CHAVE_FORTE_GERADA_ALEATORIAMENTE
EVOLUTION_INSTANCE=exatabot

# Bot
BOT_NAME=Ana
BUSINESS_HOURS_START=8
BUSINESS_HOURS_END=18
SITE_BASE_URL=https://www.exataservicos.net
CACHE_TTL_MINUTES=30
RESULTS_PAGE_SIZE=3
MAX_PHOTOS_PER_PROPERTY=3

# LLM (opcional)
LLM_PROVIDER=regex

# Redis (produção)
REDIS_URL=redis://redis:6379/0
SESSION_STORE_TYPE=redis
CACHE_TYPE=redis
SUBSCRIPTION_STORE_TYPE=redis
NOTIFY_CHECK_INTERVAL_MINUTES=15

# PostgreSQL
MESSAGE_LOG_ENABLED=true
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/exatabot

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...hash_bcrypt_real...
JWT_SECRET_KEY=CHAVE_JWT_LONGA_E_ALEATORIA_MINIMO_32_CHARS
JWT_EXPIRATION_MINUTES=120
```

---

## 11. Como Funciona a Extração de Preferências

A cada mensagem recebida (exceto nos estados `SHOWING` e `DETAIL`), o bot tenta extrair campos da mensagem e atualizar a sessão do cliente:

```
Mensagem: "quero alugar um apartamento no centro até R$ 1.200"
                    ↓
          [Extrator (Regex ou LLM)]
                    ↓
{
  "intent": "Locação",
  "property_type": "Apartamento",
  "neighborhood": "Centro",
  "max_value": 1200.0
}
                    ↓
          session.update_preferences(**resultado)
```

**Campos extraídos e como usá-los na conversa:**

| Campo na sessão | Exemplo de frase do cliente |
|---|---|
| `intent = "Locação"` | "quero alugar", "para locação", "aluguel" |
| `intent = "Venda"` | "quero comprar", "para venda", "comprar" |
| `property_type = "Apartamento"` | "apartamento", "apto" |
| `property_type = "Casa"` | "casa" |
| `property_type = "Quitinete"` | "quitinete", "kitnet", "kitinete" |
| `neighborhood = "Centro"` | "no centro", "centro de sobral" |
| `max_value = 1200.0` | "até 1200", "R$ 1.200", "máximo 1,2 mil" |
| `client_name = "João"` | "me chamo João", "sou o João" |

---

## 12. Como Funciona a Máquina de Estados

O bot percorre os seguintes estados em ordem lógica:

```
START → [coleta nome] → INTENT → [coleta finalidade] → PREFERENCES → [coleta tipo e bairro] → SHOWING → DETAIL
```

| Estado | Gatilho de entrada | O bot faz |
|---|---|---|
| `START` | Primeira mensagem de qualquer cliente | Pede o nome |
| `INTENT` | Nome coletado | Pergunta Locação ou Venda |
| `PREFERENCES` | Intenção coletada | Pede tipo → pede bairro → busca e exibe |
| `SHOWING` | Busca concluída | Navega pelos resultados, aceita seleção ou comandos |
| `DETAIL` | Imóvel selecionado | Exibe fotos e detalhes completos |

**Comportamento especial do extrator:** Se o cliente mandar tudo de uma vez ("quero alugar apartamento no centro"), o bot pode pular estados automaticamente porque o extrator já preencheu `intent`, `property_type` e `neighborhood` na sessão antes de o loop de estados executar.

---

## 13. Comandos Reconhecidos pelo Bot

Comandos que o cliente pode digitar em qualquer momento durante os estados `SHOWING` e `DETAIL`:

| Comando | Ação |
|---|---|
| `reiniciar`, `reinicia`, `começar`, `comecar`, `inicio`, `início` | Zera a sessão e volta ao início |
| `alertar`, `alerta`, `alertas`, `receber alerta`, `ativar alerta` | Ativa alertas de novos imóveis com as preferências atuais |
| `desativar alerta`, `cancelar alerta`, `remover alerta` | Cancela a assinatura de alertas |
| `mais`, `outro`, `outros`, `mais resultados`, `proxima`, `próxima` | Exibe a próxima página de resultados |
| `1`, `2`, `3` … | Seleciona o imóvel pelo número para ver detalhes |
| `voltar` (estado DETAIL) | Retorna à lista de resultados |

---

## 14. Configuração de Multi-Tenant (Múltiplos Corretores)

O ExataBot suporta múltiplos corretores/imobiliárias, cada um com sua própria instância do WhatsApp.

**Como configurar um novo corretor:**

```bash
# 1. Obter token JWT do admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# 2. Cadastrar o corretor
curl -X POST http://localhost:8000/api/admin/brokers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "corretor_joao",
    "broker_name": "João Imóveis",
    "phone_number": "5588999998888",
    "site_base_url": "https://www.exataservicos.net",
    "bot_name": "Sofia",
    "is_active": true
  }'
```

**O que acontece:**
- Mensagens recebidas na instância `corretor_joao` da Evolution API serão atendidas pela "Sofia"
- O scraping usará o `site_base_url` específico deste corretor
- As sessões continuam identificadas pelo número de telefone do cliente

---

## 15. Gerar Hash de Senha para o Painel Admin

```bash
# Com Python (dentro do venv)
source .venv/bin/activate
python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('SUA_SENHA_AQUI'))"
```

Cole o resultado em `ADMIN_PASSWORD_HASH` no arquivo `.env` ou `.env.local`.

**Senha padrão de exemplo** (senha: `admin123`):
```
$2b$12$Zsz0GgBqN/7WJ9DkC/3F7un69K1FzH8p.zG9T6jH6y6.2.X7.xW.O
```

> ⚠️ **Nunca use a senha padrão em produção.** Gere um hash com uma senha forte antes de fazer o deploy.

---

*ExataBot — Guia de Configuração | Versão 0.3.0*
