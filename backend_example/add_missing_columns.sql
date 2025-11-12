-- Script para adicionar colunas faltantes nas tabelas lotes_servico e envios_montagem
-- Execute este script no banco de dados PostgreSQL

-- Adicionar colunas em lotes_servico
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_recebimento_nf TIMESTAMP;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_vencimento_pagamento DATE;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS pago BOOLEAN DEFAULT FALSE;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_pagamento TIMESTAMP;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS id_controle INTEGER;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS link_upload TEXT;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS validade_link DATE;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS status_api INTEGER DEFAULT 0;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_envio_api TIMESTAMP;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS nota_fiscal_path TEXT;
ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS api_message TEXT;

-- Adicionar colunas em envios_montagem
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_recebimento_nf TIMESTAMP;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_vencimento_pagamento DATE;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS pago BOOLEAN DEFAULT FALSE;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_pagamento TIMESTAMP;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS id_controle INTEGER;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS link_upload TEXT;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS validade_link DATE;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS status_api INTEGER DEFAULT 0;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_envio_api TIMESTAMP;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS nota_fiscal_path TEXT;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS api_message TEXT;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS upload_hash TEXT;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS status_arquivo INTEGER DEFAULT 0;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_ultima_consulta TIMESTAMP;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS quantidade_os INTEGER;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS montador_nome TEXT;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS periodo TEXT;
ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS valor_total NUMERIC(10, 2);

-- Adicionar índice na tabela os_enviadas se não existir
CREATE INDEX IF NOT EXISTS idx_os_enviadas_lote_id ON os_enviadas(lote_id);
