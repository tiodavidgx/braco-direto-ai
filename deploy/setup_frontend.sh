#!/bin/bash
#
# Setup Frontend React/Vite - Braço Direito AI
#

set -e

APP_DIR="/var/www/braco-direto-ai"
FRONTEND_DIR="$APP_DIR/frontend"

echo "=========================================="
echo "  Configurando Frontend React"
echo "=========================================="

cd $APP_DIR

# O frontend já deve vir com o build pronto (pasta dist)
# Este script apenas configura e verifica

echo "[1/2] Verificando build do frontend..."
if [ -d "$FRONTEND_DIR/dist" ]; then
    echo "✅ Build encontrado em $FRONTEND_DIR/dist"
    ls -la $FRONTEND_DIR/dist
else
    echo "⚠️  Build não encontrado. Gerando build..."
    cd $FRONTEND_DIR
    npm install
    npm run build
fi

echo "[2/2] Configurando permissões..."
chown -R www-data:www-data $FRONTEND_DIR
chmod -R 755 $FRONTEND_DIR

echo ""
echo "=========================================="
echo "  Frontend configurado com sucesso!"
echo "=========================================="
echo ""
echo "Os arquivos estáticos serão servidos pelo Nginx"
