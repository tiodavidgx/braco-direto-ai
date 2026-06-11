#!/bin/bash
#
# Script de Instalação - Braço Direito AI
# VPS Ubuntu 24.04 LTS
#
# Uso: bash install.sh
#

set -e

echo "=========================================="
echo "  Braço Direito AI - Instalação VPS"
echo "=========================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variáveis
APP_DIR="/var/www/braco-direto-ai"
DOMAIN="72.60.244.138"  # Alterar para domínio quando tiver

# Verificar se é root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Execute como root: sudo bash install.sh${NC}"
    exit 1
fi

echo -e "${GREEN}[1/8] Atualizando sistema...${NC}"
apt update && apt upgrade -y

echo -e "${GREEN}[2/8] Instalando dependências do sistema...${NC}"
apt install -y \
    curl \
    wget \
    git \
    nginx \
    postgresql \
    postgresql-contrib \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    libpq-dev \
    chromium-browser \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1

echo -e "${GREEN}[3/8] Instalando Node.js 20 LTS...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Verificar versões
echo -e "${YELLOW}Versões instaladas:${NC}"
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo "Python: $(python3 --version)"
echo "PostgreSQL: $(psql --version)"

echo -e "${GREEN}[4/8] Configurando PostgreSQL...${NC}"
# Iniciar PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Criar usuário e banco de dados
# DB_PASSWORD deve ser definida no ambiente antes de rodar este script.
if [ -z "${DB_PASSWORD:-}" ]; then
    echo "ERRO: exporte DB_PASSWORD antes de rodar este script." >&2
    exit 1
fi
sudo -u postgres psql <<EOF
-- Criar usuário
CREATE USER braco WITH PASSWORD '${DB_PASSWORD}';

-- Criar banco de dados
CREATE DATABASE braco_db OWNER braco;

-- Dar permissões
GRANT ALL PRIVILEGES ON DATABASE braco_db TO braco;

-- Permitir criar tabelas
\c braco_db
GRANT ALL ON SCHEMA public TO braco;
EOF

echo -e "${GREEN}[5/8] Criando estrutura de diretórios...${NC}"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/backend_example
mkdir -p $APP_DIR/frontend
mkdir -p $APP_DIR/uploads
mkdir -p $APP_DIR/logs

echo -e "${GREEN}[6/8] Configurando Nginx...${NC}"
# O arquivo de configuração será copiado separadamente
systemctl enable nginx

echo -e "${GREEN}[7/8] Instalando PM2 para gerenciamento de processos Node.js...${NC}"
npm install -g pm2

echo -e "${GREEN}[8/8] Configurando firewall...${NC}"
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 14001/tcp  # API Backend (temporário para debug)
ufw allow 14003/tcp  # WhatsApp Server (temporário para debug)
ufw --force enable

echo ""
echo -e "${GREEN}=========================================="
echo "  Instalação base concluída!"
echo "==========================================${NC}"
echo ""
echo "Próximos passos:"
echo "1. Copie os arquivos do projeto para $APP_DIR"
echo "2. Execute: bash setup_backend.sh"
echo "3. Execute: bash setup_frontend.sh"
echo "4. Execute: bash setup_services.sh"
echo "5. Importe o banco de dados"
echo ""
echo -e "${YELLOW}Credenciais do banco de dados:${NC}"
echo "Host: localhost"
echo "Database: braco_db"
echo "User: braco"
echo "Password: (definida via DB_PASSWORD durante a instalação — guarde em cofre)"
