#!/bin/bash

# ===========================================
# Script de Backup - Braço Direto AI
# Crie um cron job para executar diariamente
# ===========================================

BACKUP_DIR="/var/backups/braco-direto"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="bracodireto"
DB_USER="bracodireto"

mkdir -p $BACKUP_DIR

# Backup do banco de dados
echo "🗄️ Fazendo backup do banco de dados..."
pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/db_$DATE.sql

# Backup dos arquivos de configuração
echo "📁 Fazendo backup das configurações..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /var/www/braco-direto-ai/backend_example/.env \
    /var/www/braco-direto-ai/.env.production \
    /var/www/braco-direto-ai/ecosystem.config.js \
    /etc/nginx/sites-available/braco-direto

# Backup da sessão do WhatsApp
echo "📱 Fazendo backup da sessão WhatsApp..."
tar -czf $BACKUP_DIR/whatsapp_session_$DATE.tar.gz \
    /var/www/braco-direto-ai/whatsapp-service/auth_info_baileys 2>/dev/null || true

# Limpar backups antigos (manter últimos 7 dias)
echo "🧹 Limpando backups antigos..."
find $BACKUP_DIR -type f -mtime +7 -delete

echo "✅ Backup concluído em $BACKUP_DIR"
ls -la $BACKUP_DIR
