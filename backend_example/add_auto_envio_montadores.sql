-- ============================================================
-- Novos campos de Envio Automático na tabela montadores
-- ============================================================

-- Colunas de envio automático
ALTER TABLE montadores 
    ADD COLUMN IF NOT EXISTS envio_automatico BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS dia_fechamento INTEGER DEFAULT 25,
    ADD COLUMN IF NOT EXISTS dias_envio_mes INTEGER[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS prazo_pagamento_dias INTEGER DEFAULT 10,
    ADD COLUMN IF NOT EXISTS email_responsavel_nm VARCHAR(255);

-- Tornar PIX obrigatório (se tiver registros sem PIX, preencher com vazio primeiro)
UPDATE montadores SET pix = '' WHERE pix IS NULL;
ALTER TABLE montadores ALTER COLUMN pix SET DEFAULT '';
ALTER TABLE montadores ALTER COLUMN pix SET NOT NULL;

-- Índice para busca por dias de envio
CREATE INDEX IF NOT EXISTS idx_montadores_envio_automatico 
    ON montadores (envio_automatico) WHERE envio_automatico = TRUE;
