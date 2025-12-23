#!/bin/bash
# Script para verificar e criar estrutura do sistema de upload interno

echo "🔍 Verificando estrutura do sistema de upload interno..."

# Carregar variáveis de ambiente
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DB_NAME="${DB_NAME:-email}"
DB_USER="${DB_USER:-bracodireto}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo "📦 Banco: $DB_NAME @ $DB_HOST:$DB_PORT"

# Verificar se tabela uploads_nf existe
echo ""
echo "1️⃣ Verificando tabela uploads_nf..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'uploads_nf'
) as tabela_existe;
"

# Verificar se tabela uploads_nf_arquivos existe  
echo ""
echo "2️⃣ Verificando tabela uploads_nf_arquivos..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'uploads_nf_arquivos'
) as tabela_existe;
"

# Verificar se função gerar_hash_upload existe
echo ""
echo "3️⃣ Verificando função gerar_hash_upload..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT EXISTS (
    SELECT FROM pg_proc 
    WHERE proname = 'gerar_hash_upload'
) as funcao_existe;
"

# Se não existir, criar tudo
echo ""
echo "4️⃣ Para criar as tabelas e funções, execute:"
echo "   PGPASSWORD=\"\$DB_PASSWORD\" psql -h \"\$DB_HOST\" -p \"\$DB_PORT\" -U \"\$DB_USER\" -d \"\$DB_NAME\" -f criar_tabela_uploads_nf.sql"
