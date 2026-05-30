-- Configuração compartilhada do kanban de Montagem 24h.
-- Guarda a seleção de filiais que TODOS os usuários com permissão vão ver.
CREATE TABLE IF NOT EXISTS montagem_config (
    id          INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    filiais     JSONB   NOT NULL DEFAULT '[]'::jsonb,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por  INTEGER NULL
);

INSERT INTO montagem_config (id, filiais)
VALUES (1, '[]'::jsonb)
ON CONFLICT (id) DO NOTHING;
