-- Adicionar coluna 'fonte' nas tabelas existentes para diferenciar sistema interno do externo
-- Para migração gradual do sistema de API externa para interno

-- Adicionar coluna fonte em lotes_servico
ALTER TABLE lotes_servico 
ADD COLUMN IF NOT EXISTS fonte VARCHAR(20) DEFAULT NULL;

-- Adicionar coluna fonte em envios_montagem
ALTER TABLE envios_montagem 
ADD COLUMN IF NOT EXISTS fonte VARCHAR(20) DEFAULT NULL;

-- Adicionar coluna validade_link se não existir
ALTER TABLE lotes_servico 
ADD COLUMN IF NOT EXISTS validade_link TIMESTAMP;

ALTER TABLE envios_montagem 
ADD COLUMN IF NOT EXISTS validade_link TIMESTAMP;

-- Comentários
COMMENT ON COLUMN lotes_servico.fonte IS 'NULL = legado (antes da mudança), interno = sistema interno, api_externa = api.link.dev.br';
COMMENT ON COLUMN envios_montagem.fonte IS 'NULL = legado (antes da mudança), interno = sistema interno, api_externa = api.link.dev.br';

-- Registros antigos que têm link_upload e upload_hash são da API externa
UPDATE lotes_servico 
SET fonte = 'api_externa' 
WHERE fonte IS NULL 
  AND link_upload IS NOT NULL 
  AND upload_hash IS NOT NULL;

UPDATE envios_montagem 
SET fonte = 'api_externa' 
WHERE fonte IS NULL 
  AND link_upload IS NOT NULL 
  AND upload_hash IS NOT NULL;

SELECT 'Colunas de fonte adicionadas com sucesso!' as resultado;
