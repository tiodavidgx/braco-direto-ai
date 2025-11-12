-- Tabela de configuração de integrações (incluindo Trello)
CREATE TABLE IF NOT EXISTS integracoes_config (
    id SERIAL PRIMARY KEY,
    trello_api_key TEXT,
    trello_token TEXT,
    trello_board_id TEXT,
    trello_list_id TEXT,
    trello_ativo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir registro padrão se não existir
INSERT INTO integracoes_config (id, trello_ativo)
VALUES (1, FALSE)
ON CONFLICT (id) DO NOTHING;

-- Tabela para registrar cards criados no Trello
CREATE TABLE IF NOT EXISTS trello_cards (
    id SERIAL PRIMARY KEY,
    card_id TEXT NOT NULL UNIQUE,
    card_url TEXT,
    lote_id INTEGER,
    envio_id INTEGER,
    tipo TEXT CHECK (tipo IN ('prestador', 'montador')),
    card_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_trello_cards_lote_id ON trello_cards(lote_id);
CREATE INDEX IF NOT EXISTS idx_trello_cards_envio_id ON trello_cards(envio_id);
CREATE INDEX IF NOT EXISTS idx_trello_cards_tipo ON trello_cards(tipo);
CREATE INDEX IF NOT EXISTS idx_trello_cards_created_at ON trello_cards(created_at);

-- Comentários
COMMENT ON TABLE integracoes_config IS 'Configurações de integrações externas (Trello, Slack, etc)';
COMMENT ON TABLE trello_cards IS 'Registro de cards criados no Trello automaticamente';
COMMENT ON COLUMN trello_cards.card_data IS 'JSON com dados completos do card do Trello';
COMMENT ON COLUMN trello_cards.tipo IS 'Tipo do lote/envio: prestador ou montador';
