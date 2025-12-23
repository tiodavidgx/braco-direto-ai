#!/bin/bash

# ===========================================
# Script de Setup Automático - Braço Direto AI
# Execute como root na VPS nova
# ===========================================

set -e  # Para em caso de erro

echo "🚀 Iniciando setup do Braço Direto AI..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variáveis - EDITE ANTES DE EXECUTAR
DOMAIN="seu-dominio.com.br"
DB_PASSWORD="SUA_SENHA_FORTE_AQUI"
REPO_URL="https://github.com/davidgsas/braco-direto-ai.git"
APP_DIR="/var/www/braco-direto-ai"

echo -e "${YELLOW}⚠️  ATENÇÃO: Edite as variáveis no início deste script antes de executar!${NC}"
echo "DOMAIN: $DOMAIN"
echo "DB_PASSWORD: $DB_PASSWORD"
read -p "Pressione ENTER para continuar ou Ctrl+C para cancelar..."

# ===========================================
# 1. Atualizar sistema
# ===========================================
echo -e "${GREEN}📦 Atualizando sistema...${NC}"
apt update && apt upgrade -y

# ===========================================
# 2. Instalar dependências
# ===========================================
echo -e "${GREEN}📦 Instalando dependências...${NC}"
apt install -y curl git build-essential nginx certbot python3-certbot-nginx \
    python3 python3-pip python3-venv postgresql postgresql-contrib ufw

# ===========================================
# 3. Instalar Node.js 20 LTS
# ===========================================
echo -e "${GREEN}📦 Instalando Node.js 20...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# ===========================================
# 4. Instalar PM2
# ===========================================
echo -e "${GREEN}📦 Instalando PM2...${NC}"
npm install -g pm2

# ===========================================
# 5. Configurar PostgreSQL
# ===========================================
echo -e "${GREEN}🗄️ Configurando PostgreSQL...${NC}"
sudo -u postgres psql -c "CREATE USER bracodireto WITH PASSWORD '$DB_PASSWORD';" || true
sudo -u postgres psql -c "CREATE DATABASE bracodireto OWNER bracodireto;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE bracodireto TO bracodireto;" || true

# ===========================================
# 6. Clonar repositório
# ===========================================
echo -e "${GREEN}📁 Clonando repositório...${NC}"
mkdir -p /var/www
cd /var/www
if [ -d "$APP_DIR" ]; then
    echo "Diretório já existe, atualizando..."
    cd $APP_DIR
    git pull
else
    git clone $REPO_URL
    cd $APP_DIR
fi

# ===========================================
# 7. Configurar Backend
# ===========================================
echo -e "${GREEN}⚙️ Configurando Backend...${NC}"
cd $APP_DIR/backend_example

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > .env << EOF
DATABASE_URL=postgresql://bracodireto:$DB_PASSWORD@localhost:5432/bracodireto
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bracodireto
DB_USER=bracodireto
DB_PASSWORD=$DB_PASSWORD
HOST=0.0.0.0
PORT=3080
WHATSAPP_SERVICE_URL=http://localhost:3001
ENVIRONMENT=production
EOF

deactivate

# ===========================================
# 8. Configurar WhatsApp Service
# ===========================================
echo -e "${GREEN}📱 Configurando WhatsApp Service...${NC}"
cd $APP_DIR/whatsapp-service
npm install
sed -i 's/const PORT = 3000/const PORT = 3001/' server.js 2>/dev/null || true

# ===========================================
# 9. Configurar Frontend
# ===========================================
echo -e "${GREEN}🎨 Configurando Frontend...${NC}"
cd $APP_DIR
npm install

cat > .env.production << EOF
VITE_API_URL=https://$DOMAIN/api
EOF

npm run build

# ===========================================
# 10. Configurar PM2
# ===========================================
echo -e "${GREEN}🔄 Configurando PM2...${NC}"
cat > $APP_DIR/ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'braco-backend',
      cwd: '/var/www/braco-direto-ai/backend_example',
      script: 'venv/bin/python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 3080',
      env: {
        NODE_ENV: 'production',
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
    },
    {
      name: 'braco-whatsapp',
      cwd: '/var/www/braco-direto-ai/whatsapp-service',
      script: 'server.js',
      env: {
        NODE_ENV: 'production',
        PORT: 3001,
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
    },
  ],
};
EOF

cd $APP_DIR
pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u root --hp /root

# ===========================================
# 11. Configurar Nginx
# ===========================================
echo -e "${GREEN}🌐 Configurando Nginx...${NC}"
cat > /etc/nginx/sites-available/braco-direto << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    root /var/www/braco-direto-ai/dist;
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;

    location /api/ {
        proxy_pass http://localhost:3080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /ws/ {
        proxy_pass http://localhost:3001/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

ln -sf /etc/nginx/sites-available/braco-direto /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ===========================================
# 12. Configurar Firewall
# ===========================================
echo -e "${GREEN}🔥 Configurando Firewall...${NC}"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# ===========================================
# 13. Permissões
# ===========================================
echo -e "${GREEN}🔐 Ajustando permissões...${NC}"
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR

# ===========================================
# Finalização
# ===========================================
echo ""
echo -e "${GREEN}✅ Setup concluído com sucesso!${NC}"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure o DNS do domínio $DOMAIN para apontar para este servidor"
echo "2. Execute: certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo "3. Acesse https://$DOMAIN"
echo ""
echo "📊 Status dos serviços:"
pm2 status
echo ""
echo "🔍 Comandos úteis:"
echo "  pm2 logs          - Ver logs"
echo "  pm2 restart all   - Reiniciar serviços"
echo "  pm2 status        - Ver status"
