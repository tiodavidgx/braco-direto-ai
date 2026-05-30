#!/bin/bash
# Script para carregar dados de teste de montadores
# Uso: bash carregar_dados_teste.sh

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-test-key-braco-direto-2026}"
CSV_FILE="carga_teste_montadores.csv"

echo "============================================"
echo "  Carga de Dados de Teste - Montadores"
echo "============================================"
echo ""
echo "API: $API_URL"
echo "Arquivo: $CSV_FILE"
echo ""

if [ ! -f "$CSV_FILE" ]; then
    echo "❌ Arquivo $CSV_FILE não encontrado!"
    exit 1
fi

# Criar montador de teste se não existir
echo "1. Verificando/criando montador de teste..."
curl -s -X POST "$API_URL/api/v1/montadores" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "nome": "João Silva",
    "identificador": "TESTE123",
    "email": "joao@teste.com",
    "fornecedor_id": "FOR001",
    "pix": "joao@teste.com",
    "telefone": "62999999999",
    "filial": "Goiânia",
    "cidade": "Goiânia",
    "email_responsavel_nm": "gestor@novomundo.com.br",
    "envio_automatico": true,
    "dias_envio_mes": [16, 26],
    "prazo_pagamento_dias": 10
  }' > /dev/null 2>&1

echo "   ✅ Montador TESTE123 criado/atualizado"

# Enviar CSV de boletins
echo "2. Enviando boletins..."
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/ingestao/montadores/csv" \
  -H "X-Bot-Key: $API_KEY" \
  -F "file=@$CSV_FILE")

echo "   Resposta: $RESPONSE"

# Verificar se foram inseridos
echo ""
echo "3. Verificando dados no banco..."
PGPASSWORD="" psql -h localhost -U david -d email -c "
SELECT identificador_montador, COUNT(*) as qtd, SUM(valor_venda) as total_venda, SUM(comissao_calculada) as total_comissao
FROM ingestao_boletins_montador
WHERE status = 'pendente' AND identificador_montador = 'TESTE123'
GROUP BY identificador_montador;
" 2>&1

echo ""
echo "============================================"
echo "  ✅ Carga concluída!"
echo "  Acesse: http://localhost:8080/envio-automatico-montadores"
echo "============================================"
