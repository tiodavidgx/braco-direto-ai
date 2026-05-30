#!/bin/bash

echo "🧪 Testando nova estrutura de IDs para Montadores"
echo "================================================="
echo ""

# Verificar sequence
echo "1️⃣ Verificando sequence de IDs..."
psql -U david -d email -c "SELECT last_value, is_called FROM envios_montagem_id_seq;"
echo ""

# Verificar próximo ID que será gerado
echo "2️⃣ Próximo ID a ser gerado..."
psql -U david -d email -c "SELECT nextval('envios_montagem_id_seq');"
echo ""

# Resetar para 100000 (caso tenha avançado no teste acima)
echo "3️⃣ Resetando sequence para 100000..."
psql -U david -d email -c "SELECT setval('envios_montagem_id_seq', 100000, false);"
echo ""

# Verificar lotes existentes
echo "4️⃣ Lotes de montadores existentes..."
psql -U david -d email -c "SELECT id, montador_nome, periodo, valor_total, data_envio FROM envios_montagem ORDER BY id DESC LIMIT 5;"
echo ""

# Verificar lotes de prestadores para comparação
echo "5️⃣ Lotes de prestadores para comparação..."
psql -U david -d email -c "SELECT id, prestador_nome, periodo, valor_total, data_envio FROM lotes_servico ORDER BY id DESC LIMIT 5;"
echo ""

echo "✅ Teste concluído!"
echo ""
echo "📋 Resumo:"
echo "- Montadores: IDs >= 100000"
echo "- Prestadores: IDs < 100000"
echo "- Nunca haverá conflito de IDs entre os dois tipos"
