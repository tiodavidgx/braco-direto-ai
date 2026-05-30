-- Tabela de Custos Extras de Montadores
-- Gerencia custos adicionais (ajustes, bonificações, descontos) para montadores

CREATE TABLE IF NOT EXISTS custos_extras (
    id SERIAL PRIMARY KEY,
    montador_id INTEGER REFERENCES montadores(id),
    identificador_montador VARCHAR(255) NOT NULL,
    identificador_boletim VARCHAR(255),
    valor DECIMAL(10,2) NOT NULL,
    motivo TEXT NOT NULL,
    observacao TEXT,
    status VARCHAR(50) DEFAULT 'pendente',
    cadastrado_por INTEGER REFERENCES users(id),
    processado_em TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_custos_extras_montador ON custos_extras(identificador_montador);
CREATE INDEX IF NOT EXISTS idx_custos_extras_status ON custos_extras(status);
CREATE INDEX IF NOT EXISTS idx_custos_extras_boletim ON custos_extras(identificador_boletim);
