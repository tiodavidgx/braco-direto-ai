-- ============================================================
-- Novos campos de Envio Automático no pré-cadastro de montadores
-- ============================================================

ALTER TABLE pre_cadastro_montadores 
    ADD COLUMN IF NOT EXISTS envio_automatico BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS dia_fechamento INTEGER DEFAULT 25,
    ADD COLUMN IF NOT EXISTS dias_envio_mes INTEGER[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS prazo_pagamento_dias INTEGER DEFAULT 10,
    ADD COLUMN IF NOT EXISTS email_responsavel_nm VARCHAR(255);

-- Tornar PIX obrigatório no pré-cadastro
UPDATE pre_cadastro_montadores SET pix = '' WHERE pix IS NULL;
ALTER TABLE pre_cadastro_montadores ALTER COLUMN pix SET DEFAULT '';
ALTER TABLE pre_cadastro_montadores ALTER COLUMN pix SET NOT NULL;
