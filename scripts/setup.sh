#!/usr/bin/env bash

# Script de Inicialização Automatizada - ExataBot & Evolution API
# Este script gerencia a configuração de variáveis de ambiente, sobe os containers do Docker
# e automatiza a criação da instância do WhatsApp e configuração de webhook.

set -e

# Cores para o output do terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # Sem cor

echo -e "${BLUE}=== Iniciando Configuração do ExataBot ===${NC}"

# 1. Verificar dependências necessárias
echo -e "${BLUE}[1/5] Verificando requisitos de sistema...${NC}"
for cmd in docker curl jq; do
  if ! command -v "$cmd" &> /dev/null; then
    echo -e "${RED}Erro: '$cmd' é obrigatório, mas não está instalado.${NC}"
    exit 1
  fi
done
echo -e "${GREEN}Todos os requisitos básicos instalados.${NC}"

# 2. Configurar arquivo de ambiente .env
echo -e "${BLUE}[2/5] Verificando configurações de ambiente...${NC}"
if [ ! -f .env ]; then
  if [ -f .env.local ]; then
    echo -e "${YELLOW}Copiando configurações existentes de .env.local para .env...${NC}"
    cp .env.local .env
  else
    echo -e "${YELLOW}Criando .env a partir de .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}ATENÇÃO: Por favor, edite o arquivo .env e defina suas chaves de API antes de prosseguir!${NC}"
  fi
else
  echo -e "${GREEN}Arquivo .env encontrado.${NC}"
fi

# Carregar variáveis do .env
# shellcheck disable=SC2046
export $(grep -v '^#' .env | xargs)

# Validar se as variáveis obrigatórias estão presentes
if [ -z "$EVOLUTION_API_KEY" ]; then
  echo -e "${RED}Erro: EVOLUTION_API_KEY não está definida no arquivo .env.${NC}"
  exit 1
fi

INSTANCE_NAME=${EVOLUTION_INSTANCE:-exatabot}
API_URL=${EVOLUTION_API_URL:-http://localhost:8080}
API_KEY=$EVOLUTION_API_KEY

# 3. Subir containers via Docker Compose
echo -e "${BLUE}[3/5] Subindo containers Docker...${NC}"
docker compose up -d

# 4. Aguardar Evolution API estar pronta
echo -e "${BLUE}[4/5] Aguardando a Evolution API iniciar em ${API_URL}...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
until curl -s "${API_URL}" > /dev/null || [ $ATTEMPT -eq $MAX_ATTEMPTS ]; do
  sleep 2
  ATTEMPT=$((ATTEMPT + 1))
  echo -n "."
done
echo ""

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
  echo -e "${RED}Erro: Evolution API não respondeu após 60 segundos.${NC}"
  echo -e "${RED}Verifique os logs usando: docker compose logs evolution-api${NC}"
  exit 1
fi
echo -e "${GREEN}Evolution API está ativa e respondendo!${NC}"

# 5. Criar instância do WhatsApp caso ela não exista
echo -e "${BLUE}[5/5] Provisionando instância de WhatsApp '${INSTANCE_NAME}'...${NC}"

# Verifica se a instância já existe
CHECK_INSTANCE=$(curl -s -o /dev/null -w "%{http_code}" -H "apikey: ${API_KEY}" "${API_URL}/instance/connectionState/${INSTANCE_NAME}" || true)

if [ "$CHECK_INSTANCE" = "200" ]; then
  echo -e "${GREEN}A instância '${INSTANCE_NAME}' já está criada.${NC}"
else
  echo -e "${YELLOW}Instância não encontrada. Criando nova instância '${INSTANCE_NAME}'...${NC}"
  
  CREATE_RESPONSE=$(curl -s -X POST \
    -H "apikey: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"instanceName\": \"${INSTANCE_NAME}\", \"qrcode\": true, \"token\": \"${API_KEY}\"}" \
    "${API_URL}/instance/create")
  
  if echo "$CREATE_RESPONSE" | grep -q "instance"; then
    echo -e "${GREEN}Instância '${INSTANCE_NAME}' criada com sucesso!${NC}"
  else
    echo -e "${RED}Falha ao criar instância. Resposta da API:${NC}"
    echo "$CREATE_RESPONSE"
    exit 1
  fi
fi

# Obter o QR Code para pareamento
echo -e "${BLUE}=== Pronto para Pareamento ===${NC}"
echo -e "Você precisa conectar o seu WhatsApp à Evolution API."
echo -e "Para obter o QR Code, você tem as seguintes opções:"
echo -e "1. Acesse o console interativo visual ou abra no seu navegador:"
echo -e "   ${GREEN}${API_URL}/instance/qrcode/${INSTANCE_NAME}/image${NC}"
echo -e "2. Ou simplesmente consulte as credenciais e status em:"
echo -e "   ${GREEN}docker compose logs -f evolution-api${NC}"
echo -e ""
echo -e "${GREEN}Setup concluído com sucesso! O ExataBot está rodando e pronto.${NC}"
