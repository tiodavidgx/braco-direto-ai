#!/bin/bash
#
# Deploy Completo - Braço Direito AI
# Este script faz o deploy completo do sistema na VPS
#
# Uso: bash deploy.sh
#

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/var/www/braco-direto-ai"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           BRAÇO DIREITO AI - DEPLOY COMPLETO                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar se é root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Execute como root: sudo bash deploy.sh${NC}"
    exit 1
fi

# Verificar se os arquivos existem
if [ ! -d "$APP_DIR/backend_example" ]; then
    echo -e "${RED}Erro: Pasta backend_example não encontrada em $APP_DIR${NC}"
    echo "Certifique-se de ter copiado os arquivos do projeto primeiro."
    exit 1
fi

echo -e "${GREEN}[1/7] Configurando Backend Python...${NC}"
cd $APP_DIR/backend_example

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Configurar .env
# Preserva o .env existente se j\u00e1 configurado (n\u00e3o sobrescreve secrets em produ\u00e7\u00e3o)
if [ -f .env ]; then
    echo -e "${YELLOW}.env j\u00e1 existe \u2014 n\u00e3o ser\u00e1 sobrescrito. Ajuste manualmente se necess\u00e1rio.${NC}"
else
    if [ -z "${DB_PASSWORD:-}" ] || [ -z "${SECRET_KEY:-}" ] || [ -z "${API_UPLOAD_KEY:-}" ]; then
        echo "ERRO: exporte DB_PASSWORD, SECRET_KEY e API_UPLOAD_KEY antes de rodar o deploy inicial." >&2
        exit 1
    fi
    cat > .env << EOF
# Database Configuration (Produ\u00e7\u00e3o VPS)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=braco_db
DB_USER=braco
DB_PASS=${DB_PASSWORD}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
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

# WhatsApp Integration
WHATSAPP_BASE_URL=http://localhost:3000
WHATSAPP_INTERNAL_TOKEN=${WHATSAPP_INTERNAL_TOKEN:-}

# Trello Integration
TRELLO_API_KEY=${TRELLO_API_KEY:-}
TRELLO_TOKEN=${TRELLO_TOKEN:-}
TRELLO_BOARD_ID=${TRELLO_BOARD_ID:-}
TRELLO_LIST_ID=${TRELLO_LIST_ID:-}

# Jobs Scheduler
SCHEDULER_ENABLED=True
EOF
    chmod 600 .env
fi

echo -e "${GREEN}[2/7] Configurando WhatsApp Server (Node.js)...${NC}"
cd $APP_DIR/backend_example
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
npm install --production
mkdir -p .wwebjs_auth .wwebjs_cache

echo -e "${GREEN}[3/7] Configurando Frontend...${NC}"
cd $APP_DIR/frontend
# O build já deve estar pronto (pasta dist)
if [ ! -d "dist" ]; then
    echo -e "${YELLOW}Build não encontrado, gerando...${NC}"
    npm install
    npm run build
fi
chown -R www-data:www-data $APP_DIR/frontend

echo -e "${GREEN}[4/7] Configurando diretórios e permissões...${NC}"
mkdir -p $APP_DIR/uploads
mkdir -p $APP_DIR/logs
chown -R www-data:www-data $APP_DIR/uploads

echo -e "${GREEN}[5/7] Instalando serviços systemd...${NC}"
cp $APP_DIR/deploy/braco-backend.service /etc/systemd/system/
cp $APP_DIR/deploy/braco-whatsapp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable braco-backend.service
systemctl enable braco-whatsapp.service

echo -e "${GREEN}[6/7] Configurando Nginx...${NC}"
rm -f /etc/nginx/sites-enabled/default
cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/braco-direto-ai
ln -sf /etc/nginx/sites-available/braco-direto-ai /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

echo -e "${GREEN}[7/7] Iniciando serviços...${NC}"
systemctl restart braco-backend.service
systemctl restart braco-whatsapp.service

# Aguardar inicialização
sleep 5

echo ""
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOY CONCLUÍDO!                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${GREEN}Status dos Serviços:${NC}"
echo "────────────────────"
systemctl is-active --quiet nginx && echo -e "Nginx:      ${GREEN}✓ Ativo${NC}" || echo -e "Nginx:      ${RED}✗ Inativo${NC}"
systemctl is-active --quiet braco-backend && echo -e "Backend:    ${GREEN}✓ Ativo${NC}" || echo -e "Backend:    ${RED}✗ Inativo${NC}"
systemctl is-active --quiet braco-whatsapp && echo -e "WhatsApp:   ${GREEN}✓ Ativo${NC}" || echo -e "WhatsApp:   ${RED}✗ Inativo${NC}"
systemctl is-active --quiet postgresql && echo -e "PostgreSQL: ${GREEN}✓ Ativo${NC}" || echo -e "PostgreSQL: ${RED}✗ Inativo${NC}"
echo ""
echo -e "${YELLOW}URLs de Acesso:${NC}"
echo "────────────────────"
echo "Frontend:   http://72.60.244.138"
echo "API Docs:   http://72.60.244.138/docs"
echo "Health:     http://72.60.244.138/health"
echo ""
echo -e "${YELLOW}Comandos Úteis:${NC}"
echo "────────────────────"
echo "Ver logs backend:   journalctl -u braco-backend -f"
echo "Ver logs whatsapp:  journalctl -u braco-whatsapp -f"
echo "Ver logs nginx:     tail -f /var/log/nginx/braco-direto-ai.error.log"
echo "Reiniciar tudo:     systemctl restart braco-backend braco-whatsapp nginx"
