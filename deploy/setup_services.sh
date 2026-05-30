#!/bin/bash
#
# Setup Serviços Systemd - Braço Direito AI
#

set -e

echo "=========================================="
echo "  Configurando Serviços Systemd"
echo "=========================================="

APP_DIR="/var/www/braco-direto-ai"

# Criar pasta de logs
mkdir -p $APP_DIR/logs

echo "[1/5] Copiando arquivos de serviço..."
cp $APP_DIR/deploy/braco-backend.service /etc/systemd/system/
cp $APP_DIR/deploy/braco-whatsapp.service /etc/systemd/system/

echo "[2/5] Recarregando systemd..."
systemctl daemon-reload

echo "[3/5] Habilitando serviços para iniciar no boot..."
systemctl enable braco-backend.service
systemctl enable braco-whatsapp.service

echo "[4/5] Configurando Nginx..."
# Remover configuração default
rm -f /etc/nginx/sites-enabled/default

# Copiar configuração do projeto
cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/braco-direto-ai
ln -sf /etc/nginx/sites-available/braco-direto-ai /etc/nginx/sites-enabled/

# Testar configuração
nginx -t

echo "[5/5] Iniciando serviços..."
systemctl restart nginx
systemctl start braco-backend.service
systemctl start braco-whatsapp.service

# Verificar status
echo ""
echo "=========================================="
echo "  Status dos Serviços"
echo "=========================================="
echo ""
echo "Nginx:"
systemctl status nginx --no-pager | head -5
echo ""
echo "Backend Python:"
systemctl status braco-backend.service --no-pager | head -5
echo ""
echo "WhatsApp Server:"
systemctl status braco-whatsapp.service --no-pager | head -5

echo ""
echo "=========================================="
echo "  Serviços configurados com sucesso!"
echo "=========================================="
echo ""
echo "Comandos úteis:"
echo "  - Ver logs do backend: journalctl -u braco-backend -f"
echo "  - Ver logs do WhatsApp: journalctl -u braco-whatsapp -f"
echo "  - Reiniciar backend: systemctl restart braco-backend"
echo "  - Reiniciar WhatsApp: systemctl restart braco-whatsapp"
