-- Remover constraint UNIQUE de período duplicado para montadores
-- Isso permite enviar múltiplos relatórios para o mesmo montador no mesmo período

DROP INDEX IF EXISTS idx_unique_montagem;

-- Verificar se foi removido
SELECT 
    conname AS constraint_name,
    contype AS constraint_type
FROM pg_constraint
WHERE conrelid = 'envios_montagem'::regclass;
