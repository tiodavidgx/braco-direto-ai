-- Tabela de tipos de resolução para CRM
CREATE TABLE IF NOT EXISTS crm_resolucoes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    ordem INT DEFAULT 0,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Seed com os valores atuais hardcoded
INSERT INTO crm_resolucoes (nome, ordem) VALUES
    ('Produto substituído', 1),
    ('Reembolso efetuado', 2),
    ('Entrega realizada', 3),
    ('Montagem concluída', 4),
    ('Peças enviadas', 5),
    ('Cancelamento processado', 6),
    ('Acordo com cliente', 7),
    ('Sem procedência', 8),
    ('Outro', 9)
ON CONFLICT DO NOTHING;
