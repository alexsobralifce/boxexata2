# ExataBot — Chatbot Imobiliário Inteligente

[![CI](https://github.com/alexandresobral2004/botexata/actions/workflows/ci.yml/badge.svg)](https://github.com/alexandresobral2004/botexata/actions/workflows/ci.yml)

O **ExataBot** é um chatbot de WhatsApp para automação de atendimento de imobiliárias, integrado diretamente com o portal de imóveis **Exata Serviços** (sobral/CE). Ele funciona interpretando as mensagens dos clientes, extraindo suas preferências (bairro, tipo de imóvel, finalidade de locação ou venda e faixa de preço) através de Processamento de Linguagem Natural (Regex/LLM), realizando a raspagem em tempo real (web scraping) e respondendo com as melhores correspondências de imóveis direto no WhatsApp.

Construído sob os princípios de **Clean Architecture**, **SOLID** e **Design Patterns** (State, Strategy, Gateway, Repository e Factory), o sistema é resiliente, modular e extensivo.

---

## 🛠️ Stack Tecnológica

- **Core**: Python 3.12+
- **Framework Web**: FastAPI + Uvicorn
- **Parsing/Scraping**: BeautifulSoup4 + HTTPX (com rate limiting e cache)
- **Integração WhatsApp**: Evolution API v2 (Instância baseada em Baileys / WhatsApp Web)
- **Segurança**: Validação de assinaturas de webhook e execução de container não-root
- **Containerização**: Docker & Docker Compose

---

## ⚙️ Arquitetura do Sistema

O fluxo de mensagens e scraping segue uma sequência assíncrona desacoplada:

```
                  ┌───────────────┐
                  │   WhatsApp    │
                  └───────┬───────┘
                          │ (Mensagem do Usuário)
                          ▼
                  ┌───────────────┐
                  │ Evolution API │
                  └───────┬───────┘
                          │ POST /webhook (Assíncrono)
                          ▼
┌───────────────────────────────────────────────────┐
│ ExataBot API (FastAPI)                            │
│                                                   │
│    ┌───────────┐      Extrai      ┌───────────┐   │
│    │  Message  │─────────────────►│ Preference│   │
│    │  Handler  │                  │ Extractor │   │
│    └─────┬─────┘                  └───────────┘   │
│          │                                        │
│          │ Busca                                  │
│          ▼                                        │
│    ┌───────────┐  Web Scraping    ┌───────────┐   │
│    │ Property  │─────────────────►│   Exata   │   │
│    │Repository │                  │ Serviços  │   │
│    └───────────┘                  └───────────┘   │
└───────────────────────────────────────────────────┘
```

---

## 🚀 Como Iniciar (Quickstart)

Siga os 3 passos simples abaixo para rodar todo o ambiente localmente:

### 1. Clonar e Configurar o Ambiente
Copie o template de ambiente e configure as chaves secretas:
```bash
cp .env.example .env
```
Abra o arquivo `.env` e configure a variável `EVOLUTION_API_KEY` com um segredo forte.

### 2. Rodar o Setup Automatizado
O script de setup criará a rede, subirá os contêineres Docker do bot e da Evolution API, aguardará a inicialização e provisionará a instância do WhatsApp automaticamente:
```bash
./scripts/setup.sh
```

### 3. Escanear o QR Code
Com a infraestrutura ativa, gere o QR Code no seu navegador ou terminal e escaneie com a câmera do seu celular (Opção *Aparelhos Conectados* no WhatsApp):
```
http://localhost:8080/instance/qrcode/exatabot/image
```
*Assim que o celular estiver conectado, o bot começará a responder no seu WhatsApp de forma automatizada.*

---

## 💻 Ambiente de Desenvolvimento (Hot-Reload)

Para modificar o código e testar as mudanças em tempo real sem precisar recompilar a imagem Docker, utilize os arquivos de override de desenvolvimento:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```
Desta forma, qualquer alteração na pasta `src/` ou no arquivo `main.py` reiniciará o servidor FastAPI automaticamente dentro do container.

### Rodar os Testes Locais
Para rodar a suíte completa de testes unitários e de integração:
```bash
# Entre na virtualenv local se necessário
source .venv/bin/activate
pytest tests/ -v
```

---

## 🔑 Variáveis de Ambiente (.env)

| Variável | Descrição | Valor Padrão |
|---|---|---|
| `EVOLUTION_API_URL` | URL de comunicação com a Evolution API. | `http://localhost:8080` |
| `EVOLUTION_API_KEY` | Chave de segurança para controle de instâncias. | *(Obrigatório)* |
| `EVOLUTION_INSTANCE` | Nome da instância do WhatsApp a ser criada. | `exatabot` |
| `BOT_NAME` | Nome de apresentação da inteligência artificial (Ana). | `Ana` |
| `BUSINESS_HOURS_START` | Hora de início do atendimento comercial (24h). | `8` |
| `BUSINESS_HOURS_END` | Hora de término do atendimento comercial (24h). | `18` |
| `SITE_BASE_URL` | Site de imóveis que sofrerá o scraping. | `https://www.exataservicos.net` |
| `CACHE_TTL_MINUTES` | Duração do cache local do scraper de imóveis. | `30` |
| `RESULTS_PAGE_SIZE` | Quantidade de imóveis listados por mensagem. | `3` |
| `MAX_PHOTOS_PER_PROPERTY`| Limite de fotos enviadas no detalhamento do imóvel.| `3` |
| `LLM_PROVIDER` | Algoritmo de extração de termos (`regex`, `openai`, `deepseek`). | `regex` |
| `OPENAI_API_KEY` | Chave de API caso utilize o LLM do GPT-4o-mini. | *(Opcional)* |
| `DEEPSEEK_API_KEY` | Chave de API caso utilize o LLM do DeepSeek Chat. | *(Opcional)* |

---

## 💬 Fluxo da Conversa

```
[Cliente] "Oi" 
   │
   ▼
[Ana] "Olá! Sou a Ana, assistente virtual da Exata Serviços. Gostaria de alugar ou comprar um imóvel?"
   │
   ▼
[Cliente] "Quero Alugar"
   │
   ▼
[Ana] "Excelente! E qual tipo de imóvel você busca? (Casa, Apartamento, Kitnet, etc.)"
   │
   ▼
[Cliente] "Uma casa no centro de Sobral até 1500" (Extrai: casa, centro, R$ 1500,00)
   │
   ▼
[Ana] (Pesquisa no site) 🔍 "Encontrei estes imóveis para você:"
   │  - 1. Casa comercial no Centro - R$ 1.200
   │  - 2. Casa residencial no Centro - R$ 1.500
   │  - Digite "mais" para ver outros ou o número (ex: "1") para detalhes completos.
   │
   ├──► [Cliente] "1" ──► Ana envia fotos, taxas adicionais, características e link para agendamento.
   ├──► [Cliente] "mais" ──► Ana pagina os resultados mostrando as próximas 3 opções.
   └──► [Cliente] "alertar" ──► Ana ativa os alertas, avisa o cliente e pergunta se deseja continuar (1) ou encerrar (2).
```

---

## 📋 Checklist de Deploy em Produção

Antes de realizar o deploy em um servidor Linux (VPS) ou serviço de Cloud (Railway/Render):

- [ ] Garantir que o Docker e Docker Compose estão instalados.
- [ ] Bloquear portas administrativas no firewall (`8080` para a Evolution API não deve ser pública se houver dados sensíveis; utilize proxies reversos/VPN ou limite o acesso).
- [ ] Alterar o `EVOLUTION_API_KEY` para uma chave forte e única.
- [ ] Certificar-se de que a variável `SERVER_URL` da Evolution API aponta para o domínio público correto com `https`.
- [ ] Garantir que o bot FastAPI (`exatabot`) esteja configurado para validar o cabeçalho `apikey` no webhook.
- [ ] Habilitar SSL/HTTPS para todos os endpoints expostos.
