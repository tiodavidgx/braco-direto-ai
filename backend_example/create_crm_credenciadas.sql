-- Tabela de Credenciadas (parâmetro do CRM)
-- Mesma estrutura plana de crm_plataformas / crm_areas
CREATE TABLE IF NOT EXISTS crm_credenciadas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL UNIQUE,
    ativo BOOLEAN DEFAULT TRUE,
    ordem INTEGER DEFAULT 0,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_credenciadas_ativo ON crm_credenciadas(ativo);
CREATE INDEX IF NOT EXISTS idx_crm_credenciadas_ordem ON crm_credenciadas(ordem);
