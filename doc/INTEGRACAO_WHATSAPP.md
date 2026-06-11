# ExataBot — Integração com WhatsApp (Evolution API)

> Guia completo para conectar o ExataBot ao WhatsApp usando a Evolution API v2 como gateway.

---

## Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [O que é a Evolution API](#2-o-que-é-a-evolution-api)
3. [Pré-requisitos](#3-pré-requisitos)
4. [Passo a Passo — Instalação e Conexão](#4-passo-a-passo--instalação-e-conexão)
5. [Configurar o Webhook (Evolution API → Bot)](#5-configurar-o-webhook-evolution-api--bot)
6. [Como o Bot Recebe Mensagens](#6-como-o-bot-recebe-mensagens)
7. [Como o Bot Envia Mensagens](#7-como-o-bot-envia-mensagens)
8. [Referência da API Evolution (Endpoints Usados)](#8-referência-da-api-evolution-endpoints-usados)
9. [Testar a Integração End-to-End](#9-testar-a-integração-end-to-end)
10. [Expor o Bot para a Internet (ngrok)](#10-expor-o-bot-para-a-internet-ngrok)
11. [Gerenciar Múltiplas Instâncias (Multi-Tenant)](#11-gerenciar-múltiplas-instâncias-multi-tenant)
12. [Manutenção e Reconexão](#12-manutenção-e-reconexão)
13. [Solução de Problemas](#13-solução-de-problemas)

---

## 1. Visão Geral da Arquitetura

```
┌──────────────────────────────────────────────────────────┐
│                  CELULAR DO CLIENTE                       │
│              (WhatsApp instalado)                         │
└───────────────────────┬──────────────────────────────────┘
                        │  Protocolo WhatsApp Web (WebSocket)
                        ▼
┌──────────────────────────────────────────────────────────┐
│              EVOLUTION API  :8080                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Instância "exatabot"                               │ │
│  │  • Gerencia a sessão WhatsApp Web                   │ │
│  │  • Recebe mensagens → dispara webhook               │ │
│  │  • Aceita comandos REST para enviar mensagens       │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────┬───────────────────────┬───────────────────┘
               │  POST /webhook         │  POST /message/sendText
               │  (mensagem chegou)     │  (bot quer responder)
               ▼                        ▲
┌──────────────────────────────────────────────────────────┐
│              EXATABOT  :8000                              │
│  • Processa a mensagem                                    │
│  • Executa a máquina de estados                          │
│  • Faz scraping do site de imóveis                       │
│  • Envia respostas via EvolutionGateway                  │
└──────────────────────────────────────────────────────────┘
```

**Fluxo resumido:**
1. Cliente manda mensagem pelo WhatsApp
2. Evolution API recebe e faz `POST /webhook` no ExataBot
3. ExataBot processa e chama `POST /message/sendText/{instancia}` na Evolution API
4. Evolution API entrega a resposta ao cliente

---

## 2. O que é a Evolution API

A [Evolution API](https://github.com/EvolutionAPI/evolution-api) é um projeto open-source que implementa uma API REST para o WhatsApp Web. Ela **não usa a API oficial do WhatsApp Business** — funciona emulando o cliente WhatsApp Web via navegador headless.

**Vantagens:**
- Gratuita e open-source
- Sem aprovação de conta Business necessária
- Suporta múltiplas instâncias (múltiplos números)
- API REST simples e bem documentada

**Limitações:**
- Pode ser bloqueada pelo WhatsApp se detectada como bot (use com moderação)
- Precisa de QR Code para conectar (como o WhatsApp Web normal)
- A sessão pode cair e precisar de reconexão

---

## 3. Pré-requisitos

| Requisito | Versão | Verificação |
|---|---|---|
| Docker | 24+ | `docker --version` |
| Docker Compose v2 | — | `docker compose version` |
| curl | qualquer | `curl --version` |
| jq | qualquer | `jq --version` |
| ExataBot rodando | — | `curl http://localhost:8000/health` |
| Número de WhatsApp dedicado | — | Um número que será o "bot" |

> **Importante:** O número do WhatsApp que você conectar **não poderá ser usado no celular normalmente** enquanto a Evolution API estiver conectada. Use um chip/número dedicado para o bot.

---

## 4. Passo a Passo — Instalação e Conexão

### 4.1 Subir a Evolution API

**Via Docker Compose (recomendado):**

```bash
cd /Users/alexandrerocha/botexata

# Sobe apenas a Evolution API (útil para testes isolados)
docker compose up -d evolution-api

# Ou sobe toda a stack de produção
docker compose up -d
```

Aguardar a Evolution API ficar disponível:

```bash
# Testar se a API está respondendo
curl http://localhost:8080
# Deve retornar algum JSON de status
```

### 4.2 Criar a Instância do WhatsApp

```bash
# Substituir MINHA_CHAVE pelo valor de EVOLUTION_API_KEY do seu .env.local
API_KEY="minha_chave_secreta_forte"
INSTANCE="exatabot"

curl -X POST http://localhost:8080/instance/create \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"instanceName\": \"$INSTANCE\",
    \"qrcode\": true,
    \"token\": \"$API_KEY\"
  }"
```

**Resposta esperada:**

```json
{
  "instance": {
    "instanceName": "exatabot",
    "status": "created"
  },
  "hash": {
    "apikey": "minha_chave_secreta_forte"
  }
}
```

### 4.3 Conectar o WhatsApp via QR Code

**Opção A — Imagem no navegador:**

```bash
open http://localhost:8080/instance/qrcode/exatabot/image
```

**Opção B — Base64 via API:**

```bash
curl -H "apikey: $API_KEY" \
  "http://localhost:8080/instance/qrcode/exatabot?image=false"
```

**No celular:**
1. Abra o WhatsApp no celular
2. Vá em **⋮ (três pontos) → Aparelhos conectados → Conectar aparelho**
3. Escaneie o QR Code exibido no navegador

> ⚠️ O QR Code expira em **aproximadamente 1 minuto**. Se expirar, acesse a URL do QR Code novamente — um novo será gerado automaticamente.

### 4.4 Verificar a Conexão

```bash
curl -H "apikey: $API_KEY" \
  "http://localhost:8080/instance/connectionState/exatabot"
```

**Resposta esperada (conectado):**

```json
{
  "instance": {
    "instanceName": "exatabot",
    "state": "open"
  }
}
```

Estados possíveis:
| Estado | Significado |
|---|---|
| `open` | ✅ Conectado e pronto |
| `connecting` | ⏳ Tentando conectar |
| `close` | ❌ Desconectado |
| `qrcode` | 📱 Aguardando escaneamento do QR Code |

---

## 5. Configurar o Webhook (Evolution API → Bot)

O webhook define para onde a Evolution API envia as mensagens recebidas. O `docker-compose.yml` já configura automaticamente via variável de ambiente:

```yaml
WEBHOOK_GLOBAL_URL=http://exatabot:8000/webhook
```

**Para configurar ou atualizar manualmente:**

```bash
# Quando o bot está dentro do Docker (use o nome do container)
curl -X POST http://localhost:8080/webhook/set/exatabot \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://exatabot:8000/webhook",
    "webhook_by_events": true,
    "webhook_base64": false,
    "events": ["MESSAGES_UPSERT"]
  }'

# Quando o bot está fora do Docker (localhost)
curl -X POST http://localhost:8080/webhook/set/exatabot \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://host.docker.internal:8000/webhook",
    "webhook_by_events": true,
    "webhook_base64": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

**Verificar a configuração atual do webhook:**

```bash
curl -H "apikey: $API_KEY" \
  "http://localhost:8080/webhook/find/exatabot"
```

**Eventos disponíveis** (o ExataBot só usa `MESSAGES_UPSERT`):

| Evento | Descrição |
|---|---|
| `MESSAGES_UPSERT` | Nova mensagem recebida ← **usado pelo ExataBot** |
| `MESSAGES_UPDATE` | Mensagem atualizada (ex: lida) |
| `CONNECTION_UPDATE` | Mudança no estado da conexão |
| `QRCODE_UPDATED` | Novo QR Code gerado |
| `SEND_MESSAGE` | Mensagem enviada pelo bot |

---

## 6. Como o Bot Recebe Mensagens

Quando o cliente manda uma mensagem, a Evolution API faz um `POST /webhook` com o seguinte payload JSON:

### Estrutura do Payload

```json
{
  "event": "messages.upsert",
  "instance": "exatabot",
  "data": {
    "key": {
      "remoteJid": "5588999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "3EB0A0B1C2D3E4F5A6B7"
    },
    "pushName": "João Cliente",
    "message": {
      "conversation": "quero alugar um apartamento no centro"
    },
    "messageTimestamp": 1718125200,
    "status": "DELIVERY_ACK"
  }
}
```

### Como o ExataBot processa

```python
# 1. Valida o header apikey
# 2. Ignora se event != "messages.upsert"
# 3. Ignora se fromMe == true (mensagem enviada pelo próprio bot)
# 4. Ignora se remoteJid contém "@g.us" (grupo)
# 5. Extrai phone = "5588999999999"
# 6. Extrai text da mensagem
```

### Tipos de Mensagem Suportados

| Campo no `message` | Tipo | Como é extraído |
|---|---|---|
| `conversation` | Texto simples | `message["conversation"]` |
| `extendedTextMessage.text` | Texto com link/formatação | `message["extendedTextMessage"]["text"]` |
| `buttonsResponseMessage` | Clique em botão | `selectedDisplayText` ou `selectedButtonId` |
| `listResponseMessage` | Seleção de lista | `title` |

### Tipos Ignorados (retornam `"status": "ignored"`)

- Mensagens de áudio (`audioMessage`)
- Imagens enviadas pelo cliente (`imageMessage`)
- Vídeos (`videoMessage`)
- Documentos (`documentMessage`)
- Stickers (`stickerMessage`)
- Reações

---

## 7. Como o Bot Envia Mensagens

O `EvolutionGateway` usa 3 endpoints para enviar respostas:

### 7.1 Enviar Texto

```
POST http://localhost:8080/message/sendText/exatabot
```

```json
{
  "number": "5588999999999",
  "text": "Olá! Eu sou a Ana, atendente virtual da Exata Serviços.",
  "delay": 1200
}
```

- `number`: DDI + DDD + número (sem símbolos)
- `text`: suporta **negrito** com `*asteriscos*`
- `delay`: delay em ms antes de enviar (simula digitação)

### 7.2 Enviar Imagem

```
POST http://localhost:8080/message/sendMedia/exatabot
```

```json
{
  "number": "5588999999999",
  "mediatype": "image",
  "mimetype": "image/jpeg",
  "caption": "Foto do imóvel Ref 1234",
  "media": "https://www.exataservicos.net/fotos/imovel.jpg"
}
```

- `media`: URL pública da imagem (deve ser acessível pela Evolution API)
- `mimetype`: `image/jpeg`, `image/png` ou `image/gif`

### 7.3 Indicador "Digitando..."

```
POST http://localhost:8080/chat/sendPresence/exatabot
```

```json
{
  "number": "5588999999999",
  "delay": 1500,
  "presence": "composing"
}
```

- Fica "digitando..." por `delay` milissegundos
- Usado antes de respostas longas (ex: busca de imóveis)

---

## 8. Referência da API Evolution (Endpoints Usados)

| Método | Endpoint | Autenticação | Descrição |
|---|---|---|---|
| `POST` | `/instance/create` | apikey header | Cria uma nova instância/linha |
| `GET` | `/instance/connectionState/{instance}` | apikey header | Verifica o estado da conexão |
| `GET` | `/instance/qrcode/{instance}/image` | — | Retorna a imagem PNG do QR Code |
| `GET` | `/instance/qrcode/{instance}` | apikey header | Retorna QR Code em Base64 |
| `DELETE` | `/instance/delete/{instance}` | apikey header | Deleta uma instância |
| `POST` | `/webhook/set/{instance}` | apikey header | Configura URL do webhook |
| `GET` | `/webhook/find/{instance}` | apikey header | Consulta configuração do webhook |
| `POST` | `/message/sendText/{instance}` | apikey header | Envia mensagem de texto |
| `POST` | `/message/sendMedia/{instance}` | apikey header | Envia imagem/vídeo/documento |
| `POST` | `/chat/sendPresence/{instance}` | apikey header | Define status "digitando..." |

**Autenticação:** Todas as chamadas de gestão exigem o header `apikey: EVOLUTION_API_KEY`.

---

## 9. Testar a Integração End-to-End

### Teste 1 — Verificar serviços

```bash
# Bot funcionando?
curl http://localhost:8000/health

# Evolution API funcionando?
curl http://localhost:8080

# WhatsApp conectado?
curl -H "apikey: $API_KEY" \
  http://localhost:8080/instance/connectionState/exatabot
```

### Teste 2 — Enviar mensagem diretamente pela Evolution API

Envia uma mensagem de texto para um número real, sem passar pelo bot:

```bash
curl -X POST http://localhost:8080/message/sendText/exatabot \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5588999999999",
    "text": "Teste de envio direto pela Evolution API!"
  }'
```

Se a mensagem chegar no celular, a Evolution API está funcionando corretamente.

### Teste 3 — Simular o webhook manualmente

Simula o que a Evolution API enviaria ao receber uma mensagem:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "exatabot",
    "data": {
      "key": {
        "remoteJid": "5588999999999@s.whatsapp.net",
        "fromMe": false,
        "id": "TEST123"
      },
      "message": {
        "conversation": "oi"
      }
    }
  }'
```

**Resposta esperada:**

```json
{"status": "processing"}
```

Verificar nos logs se o bot processou:

```bash
docker compose logs --tail=20 exatabot
```

### Teste 4 — Conversa completa sem WhatsApp real

```bash
# Simula toda a lógica do bot sem depender de WhatsApp
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=oi"
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=João"
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=locacao"
curl -X POST "http://localhost:8000/test-mensagem?numero=5588999999999&mensagem=apartamento no centro ate 1200"
```

---

## 10. Expor o Bot para a Internet (ngrok)

Quando o bot roda localmente (`localhost:8000`), a Evolution API dentro do Docker não consegue acessá-lo via rede. Use o **ngrok** para criar um túnel público:

### Instalar e usar ngrok

```bash
# Instalar ngrok (macOS)
brew install ngrok/ngrok/ngrok

# Autenticar (criar conta gratuita em ngrok.com)
ngrok config add-authtoken SEU_TOKEN_AQUI

# Criar túnel para a porta 8000
ngrok http 8000
```

O ngrok exibirá algo como:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

### Configurar o webhook com a URL do ngrok

```bash
curl -X POST http://localhost:8080/webhook/set/exatabot \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://abc123.ngrok.io/webhook",
    "webhook_by_events": true,
    "webhook_base64": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

> **Atenção:** URLs do ngrok gratuito mudam a cada reinicialização. Atualize o webhook sempre que reiniciar o ngrok.

---

## 11. Gerenciar Múltiplas Instâncias (Multi-Tenant)

O ExataBot suporta múltiplos corretores, cada um com seu próprio número de WhatsApp.

### Criar segunda instância

```bash
# Criar instância para o corretor João
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "corretor_joao",
    "qrcode": true,
    "token": "minha_chave_secreta_forte"
  }'

# Conectar o WhatsApp do João
open http://localhost:8080/instance/qrcode/corretor_joao/image
```

### Registrar o corretor no ExataBot

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

curl -X POST http://localhost:8000/api/admin/brokers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "corretor_joao",
    "broker_name": "João Imóveis",
    "phone_number": "5588988887777",
    "site_base_url": "https://www.exataservicos.net",
    "bot_name": "Sofia",
    "is_active": true
  }'
```

### Como o roteamento funciona

Quando a Evolution API enviar um webhook, o campo `instance` identifica qual corretor enviou:

```json
{
  "event": "messages.upsert",
  "instance": "corretor_joao",   ← identifica o corretor
  ...
}
```

O ExataBot busca o `BrokerProfile` pelo `instance_id = "corretor_joao"` e usa:
- `broker.site_base_url` → para o scraping
- `broker.instance_id` → para enviar a resposta pelo canal correto
- `broker.bot_name` → para assinar as mensagens como "Sofia"

---

## 12. Manutenção e Reconexão

### Verificar estado de todas as instâncias

```bash
curl -H "apikey: $API_KEY" http://localhost:8080/instance/fetchInstances
```

### Reconectar instância desconectada

```bash
# Verifica estado
curl -H "apikey: $API_KEY" \
  http://localhost:8080/instance/connectionState/exatabot

# Se estiver "close", tenta reconectar
curl -X GET http://localhost:8080/instance/connect/exatabot \
  -H "apikey: $API_KEY"

# Obter novo QR Code
open http://localhost:8080/instance/qrcode/exatabot/image
```

### Logout / Desconectar

```bash
# Faz logout (mantém a instância, mas desconecta do WhatsApp)
curl -X DELETE http://localhost:8080/instance/logout/exatabot \
  -H "apikey: $API_KEY"

# Deleta a instância completamente
curl -X DELETE http://localhost:8080/instance/delete/exatabot \
  -H "apikey: $API_KEY"
```

### Persistência da sessão

A Evolution API persiste os dados de sessão do WhatsApp no volume Docker `evolution_data`. Enquanto este volume existir, não é necessário re-escanear o QR Code após reiniciar o container:

```bash
# Reiniciar sem perder a sessão
docker compose restart evolution-api

# Ver onde a sessão está armazenada
docker volume inspect botexata_evolution_data
```

---

## 13. Solução de Problemas

### Bot não recebe mensagens (webhook não chega)

**1. Verificar se o webhook está configurado:**
```bash
curl -H "apikey: $API_KEY" \
  http://localhost:8080/webhook/find/exatabot
```

**2. Verificar se a URL do webhook está correta:**
- Bot no Docker: `http://exatabot:8000/webhook`
- Bot local + Evolution API no Docker: `http://host.docker.internal:8000/webhook`
- Bot local + ngrok: `https://xxxx.ngrok.io/webhook`

**3. Testar o webhook manualmente:**
```bash
curl -X POST http://localhost:8000/webhook \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"event":"messages.upsert","instance":"exatabot","data":{"key":{"remoteJid":"5588999999999@s.whatsapp.net","fromMe":false},"message":{"conversation":"oi"}}}'
```

---

### Webhook retorna 401 Unauthorized

Causa: `EVOLUTION_API_KEY` diferente nos dois serviços.

```bash
# Verificar chave no bot
grep EVOLUTION_API_KEY .env.local

# Verificar chave na Evolution API (via variável do container)
docker compose exec evolution-api env | grep API_KEY
```

Ambos devem ter o mesmo valor.

---

### QR Code não aparece ou expira muito rápido

```bash
# Forçar geração de novo QR Code
curl -X GET http://localhost:8080/instance/connect/exatabot \
  -H "apikey: $API_KEY"

# Ver como imagem
open http://localhost:8080/instance/qrcode/exatabot/image
```

---

### Mensagens enviadas não chegam no WhatsApp

**1. Verificar se a instância está conectada:**
```bash
curl -H "apikey: $API_KEY" \
  http://localhost:8080/instance/connectionState/exatabot
# state deve ser "open"
```

**2. Verificar formato do número:**
```bash
# Formato correto: DDI + DDD + número (somente dígitos)
# Exemplo: 5588999999999 (Brasil 55, DDD 88, número 999999999)
```

**3. Testar envio direto:**
```bash
curl -X POST http://localhost:8080/message/sendText/exatabot \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"number": "5588999999999", "text": "Teste"}'
```

---

### Sessão caiu (state: close) após reiniciar Docker

Se o volume `evolution_data` não foi mantido:

```bash
# Recriar a instância e re-escanear o QR Code
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instanceName": "exatabot", "qrcode": true}'

open http://localhost:8080/instance/qrcode/exatabot/image
```

Se o volume foi mantido, apenas reconecte:

```bash
curl -X GET http://localhost:8080/instance/connect/exatabot \
  -H "apikey: $API_KEY"
```

---

### Logs úteis para diagnóstico

```bash
# Logs do ExataBot (processamento de mensagens)
docker compose logs -f exatabot

# Logs da Evolution API (conexão WhatsApp, envios)
docker compose logs -f evolution-api

# Filtrar apenas erros
docker compose logs exatabot 2>&1 | grep -i error

# Ver últimas 50 linhas de ambos
docker compose logs --tail=50 exatabot evolution-api
```

---

*ExataBot — Integração WhatsApp (Evolution API) | Versão 0.3.0*
