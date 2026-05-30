-- ============================================================
-- Tabela de Ingestão de Boletins de Montadores
-- Recebe dados via API no mesmo formato do Excel de Importação
-- ============================================================

CREATE TABLE IF NOT EXISTS ingestao_boletins_montador (
    id SERIAL PRIMARY KEY,
    
    -- Dados do montador
    identificador_montador VARCHAR(100) NOT NULL,
    nome_montador VARCHAR(255),
    
    -- Dados do boletim
    boletim VARCHAR(100) NOT NULL,
    data_montagem DATE,
    valor_venda DECIMAL(15, 2) DEFAULT 0,
    nome_cliente VARCHAR(255),
    nome_produto VARCHAR(255),
    tipo_servico VARCHAR(30) DEFAULT 'MONTAGEM' 
        CHECK (tipo_servico IN ('MONTAGEM', 'ASSISTENCIA_TECNICA', 'DESMONTAGEM')),
    
    -- Valores extras
    valor_extra DECIMAL(15, 2) DEFAULT 0,
    motivo_valor_extra TEXT,
    
    -- Comissão calculada na ingestão
    comissao_calculada DECIMAL(15, 2) DEFAULT 0,
    
    -- Controle de envio
    lote_envio_id INTEGER,
    status VARCHAR(20) DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'processado', 'bloqueado', 'duplicado', 'erro')),
    
    -- Metadados
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_ingestao_montador_boletim 
    ON ingestao_boletins_montador (identificador_montador, boletim);
CREATE INDEX IF NOT EXISTS idx_ingestao_status 
    ON ingestao_boletins_montador (status);
CREATE INDEX IF NOT EXISTS idx_ingestao_lote 
    ON ingestao_boletins_montador (lote_envio_id);
CREATE INDEX IF NOT EXISTS idx_ingestao_created 
    ON ingestao_boletins_montador (created_at);
