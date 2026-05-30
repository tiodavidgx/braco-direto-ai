#!/bin/bash
# Script para importar carga de teste de boletins via API
# Uso: ./importar_carga_teste.sh

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-test-key-braco-direto-2026}"
CSV_FILE="${1:-carga_teste_montadores.csv}"

echo "📤 Importando $CSV_FILE para $API_URL/api/v1/ingestao/montadores/csv"

# Converter CSV para JSON e enviar via endpoint JSON (mais confiável)
python3 -c "
import csv, json, sys, requests

with open('$CSV_FILE', 'r') as f:
    reader = csv.DictReader(f)
    rows = []
    for row in reader:
        entry = {
            'identificador_do_montador': row.get('identificador_do_montador', '').strip(),
            'nome_do_montador': row.get('nome_do_montador', '').strip(),
            'identificador_boletim_montagem': row.get('identificador_boletim_montagem', '').strip(),
            'data_da_montagem': row.get('data_da_montagem', '').strip(),
            'media_de_valor_venda': float(row.get('media_de_valor_venda', 0)),
            'nome_do_cliente': row.get('nome_do_cliente', '').strip(),
            'nome_produto': row.get('nome_produto', '').strip(),
            'tipo_servico': row.get('tipo_servico', 'MONTAGEM').strip(),
            'adicional': float(row.get('adicional', 0) or 0),
            'motivo_valor_extra': row.get('motivo_valor_extra', '').strip(),
        }
        rows.append(entry)
    
    print(f'📋 {len(rows)} registros lidos do CSV')
    
    response = requests.post(
        '$API_URL/api/v1/ingestao/montadores',
        json=rows,
        headers={'X-Bot-Key': '$API_KEY', 'Content-Type': 'application/json'},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f'✅ Status: {data.get(\"status\")}')
        print(f'   Inseridos: {data.get(\"inseridos\", 0)}')
        print(f'   Bloqueados: {data.get(\"bloqueados\", 0)}')
        print(f'   Duplicados: {data.get(\"duplicados\", 0)}')
        print(f'   Erros: {data.get(\"erros\", 0)}')
    else:
        print(f'❌ Erro HTTP {response.status_code}: {response.text[:300]}')
        sys.exit(1)
"

echo ""
echo "✅ Importação concluída!"
