-- Tabela de lançamentos do motorista
CREATE TABLE IF NOT EXISTS lancamentos_motorista (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL,  -- 'abastecimento', 'manutencao', 'outros'
    descricao VARCHAR(500),
    valor DECIMAL(10, 2) NOT NULL,
    km_atual INTEGER,
    observacao TEXT,
    comprovante_url VARCHAR(500),
    trello_card_id VARCHAR(100),
    trello_card_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
