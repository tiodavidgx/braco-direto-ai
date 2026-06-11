-- Tabela exclusiva para envios automáticos de montadores
-- Recebe dados do Excel (13 colunas) via API de sync

CREATE TABLE IF NOT EXISTS boletins_montagem_envios (
    id SERIAL PRIMARY KEY,
    
    -- Dados do montador
    nome_montador VARCHAR(255),
    identificador_montador VARCHAR(100) NOT NULL,
    
    -- Dados do boletim
    boletim VARCHAR(100) NOT NULL,
    data_montagem DATE,
    data_previsao_montagem DATE,
    
    -- Venda
    valor_venda DECIMAL(15,2) DEFAULT 0,
    nome_cliente VARCHAR(255),
    nome_produto VARCHAR(255),
    tipo_servico VARCHAR(30) DEFAULT 'MONTAGEM',
    
    -- Nota Fiscal
    filial_saida VARCHAR(100),
    nota_fiscal VARCHAR(50),
    serie_nota_fiscal VARCHAR(10),
    
    -- Comissão calculada na ingestão
    comissao_calculada DECIMAL(15,2) DEFAULT 0,
    
    -- Valores extras (adicionados manualmente)
    valor_extra DECIMAL(15,2) DEFAULT 0,
    motivo_valor_extra TEXT,
    
    -- Controle de envio
    lote_envio_id INTEGER,
    status VARCHAR(20) DEFAULT 'pendente',
    
    -- Metadados
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_boletins_envio_mont_bol 
    ON boletins_montagem_envios (identificador_montador, boletim);
CREATE INDEX IF NOT EXISTS idx_boletins_envio_status 
    ON boletins_montagem_envios (status);
CREATE INDEX IF NOT EXISTS idx_boletins_envio_lote 
    ON boletins_montagem_envios (lote_envio_id);
