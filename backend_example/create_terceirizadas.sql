-- ============================================================
-- Tabela de Terceirizadas (Empresas Intermediadoras)
-- ============================================================

CREATE TABLE IF NOT EXISTS terceirizadas (
    id SERIAL PRIMARY KEY,
    
    -- Dados básicos
    nome VARCHAR(255) NOT NULL,
    telefone VARCHAR(50),
    email VARCHAR(255),
    cnpj VARCHAR(20),
    
    -- Comissões (mesmo modelo do montador)
    percentual_montagem DECIMAL(5,2) DEFAULT 5.00,
    percentual_assistencia DECIMAL(5,2) DEFAULT 5.00,
    percentual_desmontagem DECIMAL(5,2) DEFAULT 5.00,
    
    -- Status
    ativo BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_terceirizadas_ativo ON terceirizadas (ativo);
