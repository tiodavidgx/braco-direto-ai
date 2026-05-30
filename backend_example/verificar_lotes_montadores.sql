-- Script para verificar lotes de montadores e seus IDs

-- Ver todos os lotes de montadores
SELECT 
    id as lote_banco,
    id_controle as id_api,
    montador_nome,
    periodo,
    valor_total,
    data_envio,
    link_upload IS NOT NULL as tem_link
FROM envios_montagem
ORDER BY id DESC
LIMIT 20;

-- Verificar se há algum com id_controle no range antigo (876231+)
SELECT 
    COUNT(*) as total_lotes_offset_antigo
FROM envios_montagem
WHERE id_controle > 876231 AND id_controle < 900000;

-- Verificar lotes no novo range (100000+)
SELECT 
    COUNT(*) as total_lotes_offset_novo
FROM envios_montagem
WHERE id_controle >= 100000 AND id_controle < 876231;
