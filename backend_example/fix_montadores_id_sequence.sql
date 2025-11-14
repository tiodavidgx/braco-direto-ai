-- Script para ajustar IDs de montadores para começar em 100000
-- Isso garante que montadores e prestadores nunca tenham IDs conflitantes

-- 1. Criar sequence para montadores começando em 100000
DROP SEQUENCE IF EXISTS envios_montagem_id_seq CASCADE;
CREATE SEQUENCE envios_montagem_id_seq START 100000;

-- 2. Alterar a tabela para usar a nova sequence
ALTER TABLE envios_montagem 
  ALTER COLUMN id SET DEFAULT nextval('envios_montagem_id_seq');

-- 3. Atualizar a sequence para o próximo valor disponível
-- Se já existem registros, ajustar para o máximo + 1
SELECT setval('envios_montagem_id_seq', 
  GREATEST(100000, (SELECT COALESCE(MAX(id), 99999) + 1 FROM envios_montagem))
);

-- Verificar a configuração
SELECT 
  'envios_montagem' as tabela,
  last_value as proximo_id,
  is_called
FROM envios_montagem_id_seq;
