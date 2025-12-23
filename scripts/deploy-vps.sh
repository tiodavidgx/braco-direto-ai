#!/bin/bash

# ===========================================
# Script de Deploy Automatizado
# VPS: 72.60.244.138
# Domínio: suportedg.site
# ===========================================

set -e  # Para em caso de erro

echo "🚀 Iniciando deploy do Braço Direto AI..."
echo "=========================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variáveis
DOMAIN="suportedg.site"
API_SUBDOMAIN="api.suportedg.site"
REPO_URL="https://github.com/davidgsas/braco-direto-ai.git"
BRANCH="melhorias"
APP_DIR="/var/www/braco-direto-ai"
DB_NAME="email"
DB_USER="bracodireto"
DB_PASSWORD="BracoDireto2025Prod!"

# ===========================================
# 1. ATUALIZAR SISTEMA
# ===========================================
echo -e "${YELLOW}[1/10] Atualizando sistema...${NC}"
apt update && apt upgrade -y

# ===========================================
# 2. INSTALAR DEPENDÊNCIAS
# ===========================================
echo -e "${YELLOW}[2/10] Instalando dependências...${NC}"
apt install -y curl git nginx certbot python3-certbot-nginx \
  postgresql postgresql-contrib python3 python3-pip python3-venv \
  build-essential libpq-dev ufw

# Instalar Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

echo -e "${GREEN}✅ Node.js $(node -v) instalado${NC}"
echo -e "${GREEN}✅ Python $(python3 --version) instalado${NC}"

# ===========================================
# 3. CONFIGURAR POSTGRESQL
# ===========================================
echo -e "${YELLOW}[3/10] Configurando PostgreSQL...${NC}"

# Iniciar PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Criar usuário e banco
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS ${DB_NAME};
DROP USER IF EXISTS ${DB_USER};
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
\q
EOF

echo -e "${GREEN}✅ Banco de dados criado${NC}"

# ===========================================
# 4. CLONAR REPOSITÓRIO
# ===========================================
echo -e "${YELLOW}[4/10] Clonando repositório...${NC}"

mkdir -p /var/www
cd /var/www

# Remover se existir
rm -rf braco-direto-ai

git clone ${REPO_URL}
cd braco-direto-ai
git checkout ${BRANCH}

echo -e "${GREEN}✅ Repositório clonado${NC}"

# ===========================================
# 5. CONFIGURAR BACKEND
# ===========================================
echo -e "${YELLOW}[5/10] Configurando Backend...${NC}"

cd ${APP_DIR}/backend_example

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências Python
pip install --upgrade pip
pip install -r requirements.txt

# Criar arquivo de configuração do banco
cat > app/database.py << 'DBEOF'
import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "dbname": "email",
    "user": "bracodireto",
    "password": "BracoDireto2025Prod!",
    "host": "localhost",
    "port": "5432"
}

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()
DBEOF

# Atualizar link_upload_interno.py com credenciais corretas
sed -i 's/user="david"/user="bracodireto"/g' app/utils/link_upload_interno.py
sed -i 's/password=""/password="BracoDireto2025Prod!"/g' app/utils/link_upload_interno.py

# Criar .env
cat > .env << EOF
# Database
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=localhost
DB_PORT=5432

# Frontend URL (para links de upload)
FRONTEND_URL=https://${DOMAIN}
EOF

# Executar SQLs
echo "Criando tabelas..."
PGPASSWORD=${DB_PASSWORD} psql -U ${DB_USER} -d ${DB_NAME} -h localhost -f criar_tabela_uploads_nf.sql || true
PGPASSWORD=${DB_PASSWORD} psql -U ${DB_USER} -d ${DB_NAME} -h localhost -f add_coluna_fonte.sql || true

deactivate

echo -e "${GREEN}✅ Backend configurado${NC}"

# ===========================================
# 6. CONFIGURAR FRONTEND
# ===========================================
echo -e "${YELLOW}[6/10] Configurando Frontend...${NC}"

cd ${APP_DIR}

# Criar .env.production
cat > .env.production << EOF
VITE_API_URL=https://${API_SUBDOMAIN}
EOF

# Instalar dependências e buildar
npm install
npm run build

echo -e "${GREEN}✅ Frontend compilado${NC}"

# ===========================================
# 7. CONFIGURAR NGINX
# ===========================================
echo -e "${YELLOW}[7/10] Configurando Nginx...${NC}"

cat > /etc/nginx/sites-available/${DOMAIN} << 'NGINXEOF'
# Frontend - suportedg.site
server {
    listen 80;
    server_name suportedg.site www.suportedg.site;
    
    root /var/www/braco-direto-ai/dist;
    index index.html;
    
    # SPA - redireciona todas as rotas para index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Cache de assets estáticos
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Uploads
    location /uploads/ {
        alias /var/www/braco-direto-ai/backend_example/uploads/;
    }
}

# Backend API - api.suportedg.site
server {
    listen 80;
    server_name api.suportedg.site;
    
    location / {
        proxy_pass http://127.0.0.1:3080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout para WebSocket
        proxy_read_timeout 86400;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }
    
    # Upload de arquivos (até 50MB)
    client_max_body_size 50M;
}
NGINXEOF

# Ativar site
ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Testar e reiniciar
nginx -t
systemctl restart nginx
systemctl enable nginx

echo -e "${GREEN}✅ Nginx configurado${NC}"

# ===========================================
# 8. CRIAR SERVIÇO SYSTEMD
# ===========================================
echo -e "${YELLOW}[8/10] Criando serviço systemd...${NC}"

cat > /etc/systemd/system/bracodireto-api.service << 'SERVICEEOF'
[Unit]
Description=Braco Direto API
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/braco-direto-ai/backend_example
Environment="PATH=/var/www/braco-direto-ai/backend_example/venv/bin"
ExecStart=/var/www/braco-direto-ai/backend_example/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3080
Restart=always
RestartSec=10
StandardOutput=append:/var/log/bracodireto-api.log
StandardError=append:/var/log/bracodireto-api-error.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable bracodireto-api
systemctl start bracodireto-api

echo -e "${GREEN}✅ Serviço criado e iniciado${NC}"

# ===========================================
# 9. CONFIGURAR FIREWALL
# ===========================================
echo -e "${YELLOW}[9/10] Configurando Firewall...${NC}"

ufw allow ssh
ufw allow 'Nginx Full'
ufw --force enable

echo -e "${GREEN}✅ Firewall configurado${NC}"

# ===========================================
# 10. VERIFICAR STATUS
# ===========================================
echo -e "${YELLOW}[10/10] Verificando status...${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 DEPLOY CONCLUÍDO!${NC}"
echo "=========================================="
echo ""
echo "📌 Próximos passos:"
echo "   1. Configure o DNS do domínio suportedg.site"
echo "      - A @ -> 72.60.244.138"
echo "      - A www -> 72.60.244.138"
echo "      - A api -> 72.60.244.138"
echo ""
echo "   2. Após DNS propagar, execute SSL:"
echo "      certbot --nginx -d suportedg.site -d www.suportedg.site -d api.suportedg.site"
echo ""
echo "📊 Status dos serviços:"
systemctl status bracodireto-api --no-pager | head -5
echo ""
systemctl status nginx --no-pager | head -5
echo ""
echo "🌐 URLs (após DNS e SSL):"
echo "   Frontend: https://suportedg.site"
echo "   API: https://api.suportedg.site"
echo ""
echo "📝 Logs:"
echo "   tail -f /var/log/bracodireto-api.log"
echo "   tail -f /var/log/nginx/error.log"
echo ""
