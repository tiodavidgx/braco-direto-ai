#!/bin/bash

# ===========================================
# Script de Deploy Rápido para VPS
# Atualiza código e reinicia serviços
# ===========================================

# Configurações da VPS
VPS_HOST="72.60.244.138"
VPS_USER="root"
VPS_PASS="D123456789ss11#"
APP_DIR="/var/www/braco-direto-ai"
DB_USER="bracodireto"
DB_NAME="email"
DB_PASS="BracoDireto2025Prod!"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🚀 Deploy Rápido - Braço Direto AI"
echo "=================================="
echo "VPS: $VPS_HOST"
echo ""

# Verificar se sshpass está instalado
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}Instalando sshpass...${NC}"
    brew install hudochenkov/sshpass/sshpass 2>/dev/null || \
    sudo apt-get install -y sshpass 2>/dev/null || \
    echo -e "${RED}Por favor, instale sshpass manualmente${NC}"
fi

# Função para executar comandos na VPS
run_vps() {
    sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "$1"
}

# Menu de opções
echo "Selecione a operação:"
echo "1) Atualizar código (git pull)"
echo "2) Atualizar código + rebuild frontend"
echo "3) Reiniciar backend"
echo "4) Reiniciar todos os serviços"
echo "5) Executar SQL (criar tabela uploads_nf)"
echo "6) Ver logs do backend"
echo "7) Conectar SSH interativo"
echo "8) Deploy completo (git pull + build + restart)"
echo ""
read -p "Opção [1-8]: " opcao

case $opcao in
    1)
        echo -e "${YELLOW}Atualizando código...${NC}"
        run_vps "cd $APP_DIR && git pull origin melhorias"
        echo -e "${GREEN}✅ Código atualizado${NC}"
        ;;
    2)
        echo -e "${YELLOW}Atualizando código e rebuildando frontend...${NC}"
        run_vps "cd $APP_DIR && git pull origin melhorias && npm install && npm run build"
        echo -e "${GREEN}✅ Frontend atualizado e compilado${NC}"
        ;;
    3)
        echo -e "${YELLOW}Reiniciando backend...${NC}"
        run_vps "systemctl restart braco-backend"
        echo -e "${GREEN}✅ Backend reiniciado${NC}"
        ;;
    4)
        echo -e "${YELLOW}Reiniciando todos os serviços...${NC}"
        run_vps "systemctl restart braco-backend && systemctl restart nginx"
        echo -e "${GREEN}✅ Serviços reiniciados${NC}"
        ;;
    5)
        echo -e "${YELLOW}Executando SQL para criar tabela uploads_nf...${NC}"
        run_vps "cd $APP_DIR/backend_example && PGPASSWORD='$DB_PASS' psql -U $DB_USER -d $DB_NAME -h localhost -f criar_tabela_uploads_nf.sql"
        echo -e "${GREEN}✅ SQL executado${NC}"
        ;;
    6)
        echo -e "${YELLOW}Logs do backend (últimas 50 linhas):${NC}"
        run_vps "journalctl -u braco-backend -n 50 --no-pager"
        ;;
    7)
        echo -e "${YELLOW}Conectando via SSH...${NC}"
        sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST"
        ;;
    8)
        echo -e "${YELLOW}Deploy completo...${NC}"
        echo "1/4 - Atualizando código..."
        run_vps "cd $APP_DIR && git pull origin melhorias"
        
        echo "2/4 - Instalando dependências e compilando frontend..."
        run_vps "cd $APP_DIR && npm install && npm run build"
        
        echo "3/4 - Atualizando backend..."
        run_vps "cd $APP_DIR/backend_example && source venv/bin/activate && pip install -r requirements.txt && deactivate"
        
        echo "4/4 - Reiniciando serviços..."
        run_vps "systemctl restart braco-backend && systemctl restart nginx"
        
        echo -e "${GREEN}✅ Deploy completo finalizado!${NC}"
        ;;
    *)
        echo -e "${RED}Opção inválida${NC}"
        exit 1
        ;;
esac

echo ""
echo "🌐 Frontend: http://$VPS_HOST"
echo "🔧 API: http://$VPS_HOST:3080"
