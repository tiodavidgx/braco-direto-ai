#!/bin/bash
#
# Script para copiar arquivos para VPS e fazer deploy
# Execute este script do seu Mac
#
# Uso: bash upload_to_vps.sh
#

set -e

# Configurações — leia do ambiente ou exporte antes de rodar:
#   export VPS_IP=... VPS_USER=root VPS_PASS=...
VPS_IP="${VPS_IP:?Defina VPS_IP no ambiente}"
VPS_USER="${VPS_USER:-root}"
VPS_PASS="${VPS_PASS:?Defina VPS_PASS no ambiente (ou use chave SSH)}"
APP_DIR="/var/www/braco-direto-ai"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "  Upload para VPS - Braço Direito AI"
echo "=========================================="

# Verificar se sshpass está instalado
if ! command -v sshpass &> /dev/null; then
    echo "Instalando sshpass..."
    brew install hudochenkov/sshpass/sshpass
fi

echo "[1/6] Criando estrutura de diretórios na VPS..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP "mkdir -p $APP_DIR/{frontend,deploy,uploads,logs}"

echo "[2/6] Enviando backend..."
sshpass -p "$VPS_PASS" rsync -avz --progress \
    --exclude 'venv' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '.wwebjs_auth' \
    --exclude '.wwebjs_cache' \
    --exclude '*.log' \
    --exclude '.env' \
    -e "ssh -o StrictHostKeyChecking=no" \
    "$LOCAL_DIR/backend_example/" "$VPS_USER@$VPS_IP:$APP_DIR/backend_example/"

echo "[3/7] Enviando whatsapp-service..."
sshpass -p "$VPS_PASS" rsync -avz --progress \
    --exclude 'node_modules' \
    --exclude 'auth_info_baileys' \
    --exclude '.wwebjs_auth' \
    --exclude '.wwebjs_cache' \
    --exclude '*.log' \
    -e "ssh -o StrictHostKeyChecking=no" \
    "$LOCAL_DIR/whatsapp-service/" "$VPS_USER@$VPS_IP:$APP_DIR/whatsapp-service/"

echo "[4/7] Enviando frontend (build)..."
sshpass -p "$VPS_PASS" rsync -avz --progress --delete \
    -e "ssh -o StrictHostKeyChecking=no" \
    "$LOCAL_DIR/dist/" "$VPS_USER@$VPS_IP:$APP_DIR/frontend/"

echo "[5/7] Enviando scripts de deploy..."
sshpass -p "$VPS_PASS" rsync -avz --progress \
    -e "ssh -o StrictHostKeyChecking=no" \
    "$LOCAL_DIR/deploy/" "$VPS_USER@$VPS_IP:$APP_DIR/deploy/"

echo "[6/7] Enviando backup do banco de dados..."
sshpass -p "$VPS_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/deploy/database_backup.sql" "$VPS_USER@$VPS_IP:$APP_DIR/deploy/"

echo "[7/7] Configurando permissões e instalando dependências do WhatsApp..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP "chmod +x $APP_DIR/deploy/*.sh && cd $APP_DIR/whatsapp-service && npm install --production 2>/dev/null || true"

echo ""
echo "=========================================="
echo "  Upload concluído!"
echo "=========================================="
echo ""
echo "Próximos passos (executar na VPS):"
echo ""
echo "1. Conectar na VPS:"
echo "   ssh root@$VPS_IP"
echo ""
echo "2. Executar instalação (se primeira vez):"
echo "   cd $APP_DIR/deploy && bash install.sh"
echo ""
echo "3. Importar banco de dados:"
echo "   sudo -u postgres psql braco_db < $APP_DIR/deploy/database_backup.sql"
echo ""
echo "4. Executar deploy:"
echo "   cd $APP_DIR/deploy && bash deploy.sh"
echo ""
