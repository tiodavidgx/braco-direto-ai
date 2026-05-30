#!/bin/bash
#
# Setup WhatsApp Server (Node.js) - Braço Direito AI
#

set -e

APP_DIR="/var/www/braco-direto-ai"
WHATSAPP_DIR="$APP_DIR/backend_example"

echo "=========================================="
echo "  Configurando WhatsApp Server"
echo "=========================================="

cd $WHATSAPP_DIR

echo "[1/3] Instalando dependências Node.js..."
npm install

echo "[2/3] Configurando Puppeteer para servidor..."
# Configurar variáveis de ambiente para Puppeteer em servidor headless
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
export PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

echo "[3/3] Criando diretórios de sessão WhatsApp..."
mkdir -p .wwebjs_auth
mkdir -p .wwebjs_cache

echo ""
echo "=========================================="
echo "  WhatsApp Server configurado!"
echo "=========================================="
echo ""
echo "O servidor WhatsApp será gerenciado pelo PM2"
