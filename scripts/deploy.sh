#!/bin/bash

# ===========================================
# Script de Deploy/Atualização - Braço Direto AI
# Execute quando quiser atualizar o código
# ===========================================

set -e

APP_DIR="/var/www/braco-direto-ai"

echo "🔄 Iniciando atualização do Braço Direto AI..."

cd $APP_DIR

# Backup do .env
cp backend_example/.env backend_example/.env.backup 2>/dev/null || true
cp .env.production .env.production.backup 2>/dev/null || true

# Pull do código
echo "📥 Baixando atualizações..."
git pull origin main

# Restaurar .env
cp backend_example/.env.backup backend_example/.env 2>/dev/null || true
cp .env.production.backup .env.production 2>/dev/null || true

# Atualizar dependências do backend
echo "🐍 Atualizando dependências Python..."
cd $APP_DIR/backend_example
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Atualizar dependências do WhatsApp
echo "📱 Atualizando dependências WhatsApp..."
cd $APP_DIR/whatsapp-service
npm install

# Atualizar frontend
echo "🎨 Atualizando Frontend..."
cd $APP_DIR
npm install
npm run build

# Reiniciar serviços
echo "🔄 Reiniciando serviços..."
pm2 restart all

# Ajustar permissões
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR

echo ""
echo "✅ Atualização concluída!"
echo ""
pm2 status
