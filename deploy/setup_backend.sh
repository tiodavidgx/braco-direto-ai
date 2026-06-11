#!/bin/bash
#
# Setup Backend Python - Braço Direito AI
#

set -e

APP_DIR="/var/www/braco-direto-ai"
BACKEND_DIR="$APP_DIR/backend_example"

echo "=========================================="
echo "  Configurando Backend Python"
echo "=========================================="

cd $BACKEND_DIR

# Criar ambiente virtual
echo "[1/4] Criando ambiente virtual Python..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
echo "[2/4] Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Criar arquivo .env de produção
echo "[3/4] Configurando variáveis de ambiente..."
if [ -f .env ]; then
    echo ".env já existe — não será sobrescrito."
else
    if [ -z "${DB_PASSWORD:-}" ] || [ -z "${SECRET_KEY:-}" ] || [ -z "${API_UPLOAD_KEY:-}" ]; then
        echo "ERRO: exporte DB_PASSWORD, SECRET_KEY e API_UPLOAD_KEY antes de rodar este script." >&2
        exit 1
    fi
    cat > .env << EOF
# Database Configuration (Produção VPS)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=braco_db
DB_USER=braco
DB_PASS=${DB_PASSWORD}

# API Configuration
API_HOST=0.0.0.0
API_PORT=14001
DEBUG=False
ENV=production

# Security
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=24

# CORS (Frontend URL)
FRONTEND_URL=${FRONTEND_URL:-https://suportedg.site}

# Microsoft OAuth2
MICROSOFT_CLIENT_ID=${MICROSOFT_CLIENT_ID:-}
MICROSOFT_TENANT_ID=${MICROSOFT_TENANT_ID:-}

# API de Upload de Notas Fiscais
API_UPLOAD_URL=${API_UPLOAD_URL:-https://api.link.dev.br/dvprocessamento/}
API_UPLOAD_KEY=${API_UPLOAD_KEY}

# WhatsApp Integration (local na VPS)
WHATSAPP_BASE_URL=http://localhost:14003
WHATSAPP_INTERNAL_TOKEN=${WHATSAPP_INTERNAL_TOKEN:-}

# Trello Integration (desabilitado por padrão)
TRELLO_API_KEY=${TRELLO_API_KEY:-}
TRELLO_TOKEN=${TRELLO_TOKEN:-}
TRELLO_BOARD_ID=${TRELLO_BOARD_ID:-}
TRELLO_LIST_ID=${TRELLO_LIST_ID:-}

# Jobs Scheduler
SCHEDULER_ENABLED=True
EOF
    chmod 600 .env
fi

# Criar pasta de uploads
echo "[4/4] Criando diretórios necessários..."
mkdir -p uploads
mkdir -p app/templates

# Testar conexão com banco
echo ""
echo "Testando conexão com banco de dados..."
source venv/bin/activate
python3 -c "from app.database import test_connection; test_connection()"

echo ""
echo "=========================================="
echo "  Backend configurado com sucesso!"
echo "=========================================="
