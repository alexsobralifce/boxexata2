# ExataBot — Guia Completo de Desenvolvimento

> Guia técnico para construção de um chatbot de WhatsApp com scraping imobiliário,
> integrado ao site exataservicos.net e conectado via Evolution API.

---

## 1. Visão Geral da Arquitetura

```
Cliente WhatsApp
       │
       ▼
 Evolution API  ◄──── QR Code / WhatsApp Web
  (porta 8080)
       │  webhook POST /webhook
       ▼
   ExataBot API
  FastAPI Python
  (porta 8000)
       │
       ├──► Sessão do cliente (memória)
       ├──► Scraper BeautifulSoup ──► exataservicos.net
       └──► Resposta humanizada ──► Evolution API ──► Cliente
```

**Fluxo resumido:**
1. Cliente manda mensagem no WhatsApp
2. Evolution API recebe e dispara webhook para o ExataBot
3. ExataBot interpreta a mensagem, extrai preferências
4. Scraper busca imóveis no site da Exata Serviços
5. Bot monta resposta humanizada e envia de volta via Evolution API

---

## 2. Comparativo de APIs do WhatsApp

| API | Tipo | Custo | Requer verificação Meta | Ideal para |
|---|---|---|---|---|
| **Evolution API** | Open source / não oficial | Gratuito (self-hosted) | Não | Projetos próprios, MVPs, bots internos |
| **WhatsApp Cloud API (Meta)** | Oficial | Gratuito até 1.000 conversas/mês | Sim (CNPJ + verificação) | Empresas formalizadas |
| **WATI** | SaaS sobre Cloud API | A partir de US$ 49/mês | Sim | Equipes sem infra própria |
| **Z-API** | Pago / não oficial | R$ 49–149/mês | Não | Empresas brasileiras, fácil integração |

### Por que Evolution API para este projeto

- **Gratuita e open source** — sem mensalidade [cite:11]
- **Self-hosted** — dados ficam no seu servidor
- **Deploy via Docker** em 1 comando [cite:16]
- **Webhook nativo** — dispara eventos em tempo real
- **Suporta Baileys** (WhatsApp Web) e **Cloud API oficial** na mesma plataforma [cite:10]
- Amplamente usada no Brasil — comunidade ativa no Discord [cite:12]

> ⚠️ **Atenção:** A Evolution API usa engenharia reversa do WhatsApp Web.
> Isso viola os termos de serviço do WhatsApp e pode resultar em banimento do número.
> Para uso comercial formal, considere a **WhatsApp Cloud API oficial** da Meta.

---

## 3. Stack Tecnológica

### Backend (Python)

| Tecnologia | Versão | Função |
|---|---|---|
| **FastAPI** | 0.115+ | Framework web assíncrono — endpoints e webhook |
| **Uvicorn** | 0.30+ | Servidor ASGI de alta performance |
| **httpx** | 0.27+ | Requisições HTTP assíncronas (scraping + chamadas à API) |
| **BeautifulSoup4** | 4.12+ | Parser HTML para scraping do site |
| **python-dotenv** | 1.0+ | Gerenciamento de variáveis de ambiente |
| **Pydantic v2** | 2.8+ | Validação de dados e modelos |

### Infraestrutura

| Tecnologia | Função |
|---|---|
| **Docker + Docker Compose** | Orquestração de contêineres |
| **Evolution API** | Gateway WhatsApp |
| **Railway / VPS Ubuntu** | Hospedagem em produção |

### Opcional (para escalar)

| Tecnologia | Função |
|---|---|
| **Redis** | Cache distribuído das sessões (substituir dict em memória) |
| **PostgreSQL** | Persistência de histórico de conversas |
| **OpenAI / DeepSeek** | NLP avançado para extração de preferências |
| **Celery** | Fila de tarefas para scraping assíncrono |

---

## 4. Estrutura de Arquivos do Projeto

```
exatabot/
├── main.py                  # Aplicação principal (bot + scraper + webhook)
├── requirements.txt         # Dependências Python
├── Dockerfile               # Imagem do bot
├── docker-compose.yml       # Orquestração bot + Evolution API
├── .env                     # Variáveis de ambiente (NÃO commitar)
├── .env.example             # Modelo das variáveis
└── README.md                # Documentação
```

---

## 5. Passo a Passo de Desenvolvimento

### Passo 1 — Ambiente local

```bash
# Clonar o projeto
git clone <seu-repositorio> exatabot
cd exatabot

# Criar ambiente virtual Python
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# Instalar dependências
pip install fastapi uvicorn httpx beautifulsoup4 python-dotenv pydantic
pip freeze > requirements.txt
```

### Passo 2 — Subir Evolution API com Docker

```bash
# docker-compose.yml já incluído no projeto
docker-compose up -d evolution-api

# Verificar se subiu
curl http://localhost:8080
```

### Passo 3 — Conectar o WhatsApp

```bash
# Criar instância
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{"instanceName": "exatabot", "qrcode": true}'

# Gerar QR Code
curl http://localhost:8080/instance/qrcode/exatabot \
  -H "apikey: SUA_CHAVE"
```

Acesse `http://localhost:8081` para escanear o QR Code pelo painel visual.

### Passo 4 — Rodar o bot localmente

```bash
uvicorn main:app --reload --port 8000
```

### Passo 5 — Expor localmente para testes (ngrok)

```bash
# Instalar ngrok e expor porta 8000
ngrok http 8000

# Registrar webhook na Evolution API
curl -X POST http://localhost:8080/webhook/set/exatabot \
  -H "apikey: SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://SEU-NGROK.ngrok.io/webhook",
    "webhook_by_events": true,
    "events": ["MESSAGES_UPSERT"]
  }'
```

### Passo 6 — Testar o scraper sem WhatsApp

```bash
# Listar imóveis
curl "http://localhost:8000/test-scraping?finalidade=Locação&bairro=Centro"

# Detalhe de um imóvel
curl "http://localhost:8000/test-detalhe?codigo=721"

# Simular conversa
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=oi"
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=quero%20alugar%20uma%20casa%20no%20centro"
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=1"
```

### Passo 7 — Deploy em produção (Railway)

```bash
# Instalar Railway CLI
npm i -g @railway/cli
railway login

# Criar projeto
railway new exatabot
railway up

# Configurar variáveis
railway variables set EVOLUTION_API_URL=https://evolution.seudominio.com
railway variables set EVOLUTION_API_KEY=SUA_CHAVE
railway variables set EVOLUTION_INSTANCE=exatabot
```

---

## 6. Configuração do .env

```bash
# .env — NÃO commitar este arquivo no Git!

# Evolution API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=minha_chave_secreta_forte
EVOLUTION_INSTANCE=exatabot

# (Opcional) Para usar LLM na extração de preferências
OPENAI_API_KEY=sk-...
# ou
DEEPSEEK_API_KEY=sk-...
```

---

## 7. Prompts para Geração de Código com IA

Use os prompts abaixo no Claude, ChatGPT ou Cursor para gerar cada parte do sistema.

---

### Prompt 1 — Scraper do site Exata Serviços

```
Você é um engenheiro Python especialista em web scraping.

Crie um módulo `scraper.py` assíncrono com httpx e BeautifulSoup4 para scraping
do site https://www.exataservicos.net

O site tem estas páginas:
- /imovel.php — lista todos os imóveis
- /resultado_imovel.php?codigo=N — filtra por tipo (4=casa, 5=apartamento, 6=kitnet)
- /detalhe_imovel.php?codigo=N — detalhe completo com fotos

Requisitos:
1. Função async `scrape_lista(finalidade, bairro, tipo_codigo)` → List[dict]
   - Extrai: codigo, ref, tipo, endereco, bairro, valor, url
   - Filtra por finalidade ("Locação" ou "Venda")
   - Filtra por bairro (substring case-insensitive)
   - Retorna lista de dicionários

2. Função async `scrape_detalhe(codigo)` → dict | None
   - Extrai: codigo, ref, endereco, bairro, valor, taxas, caracteristicas (lista), fotos (lista de URLs)

3. Cache em memória com TTL de 30 minutos usando dict + datetime
4. User-Agent realista nos headers
5. Tratamento de erros com try/except + logging
6. Timeout de 15 segundos nas requisições

Retorne o código completo do módulo com docstrings.
```

---

### Prompt 2 — Máquina de estados da conversa

```
Você é um engenheiro Python especialista em chatbots.

Crie um módulo `conversa.py` com a máquina de estados para um bot imobiliário
humanizado chamado "Ana" da Exata Serviços Imobiliária em Sobral/CE.

A sessão de cada cliente tem estes campos:
- etapa: "inicio" | "finalidade" | "tipo" | "buscando" | "mostrando" | "detalhe"
- nome_cliente: str
- finalidade: "Locação" | "Venda"
- tipo: str (código do tipo de imóvel)
- bairro: str
- valor_max: float
- resultados: list
- resultado_offset: int

Implemente:
1. `processar_mensagem(numero, texto, sessao)` → Sessao atualizada + lista de respostas

2. Extrações via regex:
   - `extrair_nome(texto)` → detecta "me chamo X", "sou o X", "oi, sou a X"
   - `extrair_valor_max(texto)` → R$ 1.500, 1500, 1,5 mil, até 2000
   - `extrair_bairro(texto)` → lista de bairros de Sobral/CE
   - `extrair_tipo(texto)` → casa, apartamento, kitnet, galpão, etc.

3. Respostas humanizadas com variações aleatórias (random.choice) para:
   - Saudações, confirmações, buscando, resultado encontrado, sem resultado,
     erro técnico, despedida

4. Saudação dinâmica: Bom dia / Boa tarde / Boa noite por horário
5. Detecção de fora do horário (seg-sex 8h–18h)
6. Personalização: usar nome do cliente nas respostas quando disponível
7. Paginação de resultados: 3 imóveis por mensagem, "mais" para avançar

Retorne o código completo com docstrings e exemplos de uso.
```

---

### Prompt 3 — Webhook FastAPI + Evolution API

```
Você é um engenheiro Python especialista em FastAPI e integrações com WhatsApp.

Crie um módulo `webhook.py` com:

1. Endpoint POST `/webhook` que recebe eventos da Evolution API v2
   - Filtra apenas evento "messages.upsert"
   - Ignora mensagens enviadas pelo próprio bot (fromMe: true)
   - Ignora mensagens de grupos (@g.us)
   - Extrai o número do remetente e o texto da mensagem
   - Suporta tipos: conversation, extendedTextMessage, buttonsResponseMessage, listResponseMessage
   - Processa em background com asyncio.create_task

2. Função async `enviar_texto(numero, texto, digitar_segundos)`:
   - Primeiro chama /chat/sendPresence com "composing" + delay em ms
   - Depois chama /message/sendText com o texto
   - Headers: apikey, Content-Type: application/json
   - Timeout de 10s

3. Função async `enviar_imagem(numero, url_imagem, caption)`:
   - Chama /message/sendMedia com mediatype: "image"
   - Timeout de 15s

4. Variáveis de configuração via os.getenv:
   - EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE

5. Logging estruturado de todas as operações
6. Tratamento de erros sem interromper o processamento

Base URL da Evolution API: http://localhost:8080
Retorne o código completo com tipagem e docstrings.
```

---

### Prompt 4 — Docker Compose completo

```
Crie um arquivo docker-compose.yml para orquestrar dois serviços:

1. Serviço "evolution-api":
   - Imagem: atendai/evolution-api:latest
   - Porta: 8080:8080
   - Variáveis de ambiente:
     * SERVER_URL=http://evolution-api:8080
     * AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY}
     * WEBHOOK_GLOBAL_URL=http://exatabot:8000/webhook
     * WEBHOOK_GLOBAL_ENABLED=true
     * WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=true
     * QRCODE_LIMIT=10
   - Volume para persistência: ./evolution_data:/evolution/instances

2. Serviço "exatabot":
   - Build: . (usa Dockerfile local)
   - Porta: 8000:8000
   - Depende de: evolution-api
   - Variáveis de ambiente via arquivo .env
   - Restart: always
   - Healthcheck: GET /health a cada 30s

Rede interna compartilhada entre os serviços.
Inclua comentários explicando cada bloco.
```

---

### Prompt 5 — Adicionando LLM para NLP avançado

```
Você é um engenheiro Python especialista em LLMs e NLP.

Melhore o módulo de extração de preferências substituindo regex por LLM.

Crie `extrator_llm.py` compatível com OpenAI e DeepSeek:

1. Classe `ExtratorPreferencias` com método async `extrair(mensagem, historico)` → dict

2. System prompt em português que instrui o modelo a retornar JSON com:
   {
     "finalidade": "Locação"|"Venda"|null,
     "tipo": "casa"|"apartamento"|"kitnet"|null,
     "bairro": string|null,
     "cidade": string|null,
     "valor_max": number|null,
     "quartos_min": number|null,
     "pet_friendly": bool|null,
     "garagem": bool|null,
     "mobiliado": bool|null,
     "nome_cliente": string|null
   }

3. Mantém contexto das últimas 6 mensagens da conversa
4. Fallback para extração por regex se a chamada LLM falhar
5. Compatível com:
   - OpenAI: model="gpt-4o-mini", base_url padrão
   - DeepSeek: model="deepseek-chat", base_url="https://api.deepseek.com"
   - Configuração via variável de ambiente LLM_PROVIDER=openai|deepseek

Inclua tratamento de erros e logging.
```

---

### Prompt 6 — Testes automatizados

```
Crie um arquivo `test_bot.py` com testes usando pytest e pytest-asyncio.

Teste os seguintes fluxos completos de conversa:

1. Fluxo de locação simples:
   "oi" → apresentação
   "quero alugar" → pergunta tipo
   "casa no centro" → scraping (mock) → lista resultados
   "1" → detalhe do imóvel
   "agendar" → dados de contato

2. Fluxo com informações completas de uma vez:
   "oi, quero uma kitnet em benfica até R$ 800" → scraping → resultados

3. Fluxo sem resultados:
   "mansão na zona rural por R$ 100" → mensagem amigável de sem resultados

4. Extração de nome:
   "oi, me chamo Francisco" → bot usa o nome nas respostas seguintes

5. Paginação:
   Lista > "mais" > próxima página

Use unittest.mock para mockar:
- httpx.AsyncClient (evita chamadas reais ao site)
- Evolution API (evita envio real de WhatsApp)

Inclua fixtures para sessão limpa entre testes.
```

---

## 8. Diagrama de Fluxo da Conversa

```
[CLIENTE] "oi"
    │
    ▼
[ANA] Saudação + apresentação
    │
    ▼
[CLIENTE] "Locação" ou "Venda"
    │
    ▼
[ANA] Pergunta tipo de imóvel
    │
    ▼
[CLIENTE] "casa no centro até R$1.500"
    │                │
    │           extrai: tipo=casa
    │                  bairro=centro
    │                  valor_max=1500
    ▼
[SCRAPER] GET exataservicos.net/imovel.php
    │
    ▼
[ANA] Lista 3 imóveis com endereço + valor + link
    │
    ├── [CLIENTE] "1"  ──► detalhe + fotos ──► [CLIENTE] "agendar" ──► dados de contato
    ├── [CLIENTE] "mais" ──► próximos 3 imóveis
    ├── [CLIENTE] "bairro X" ──► nova busca filtrada
    └── [CLIENTE] "reiniciar" ──► volta ao início
```

---

## 9. Checklist de Deploy em Produção

- [ ] Servidor Ubuntu 22.04+ com 1GB RAM mínimo (Digital Ocean, Hetzner, ou Railway)
- [ ] Docker e Docker Compose instalados
- [ ] Porta 8000 liberada no firewall
- [ ] Domínio ou IP público configurado
- [ ] `.env` configurado com chave forte (nunca no Git)
- [ ] `docker-compose up -d` executado
- [ ] QR Code escaneado e sessão WhatsApp ativa
- [ ] Webhook registrado apontando para o servidor de produção
- [ ] Endpoint `/health` retornando `{"status": "ok"}`
- [ ] Teste manual de ponta a ponta no WhatsApp
- [ ] Monitoramento de logs: `docker-compose logs -f exatabot`

---

## 10. Pontos de Melhoria Futura

| Feature | Tecnologia | Complexidade |
|---|---|---|
| NLP avançado com LLM | DeepSeek Chat / GPT-4o-mini | Média |
| Persistência de sessões | Redis | Baixa |
| Histórico de conversas | PostgreSQL | Média |
| Painel de administração | FastAPI + React | Alta |
| Múltiplos números WhatsApp | Evolution API multi-instância | Baixa |
| Alertas de novos imóveis | Cron + WhatsApp proativo | Média |
| Integração com Google Maps | Maps API | Média |

