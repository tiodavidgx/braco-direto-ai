-- Anexos dos comentários do kanban de Montagem 24h
CREATE TABLE IF NOT EXISTS montagem_comentario_anexos (
    id             BIGSERIAL PRIMARY KEY,
    comentario_id  BIGINT      NOT NULL REFERENCES montagem_comentarios(id) ON DELETE CASCADE,
    nome           TEXT        NOT NULL,
    url            TEXT        NOT NULL,
    tipo           TEXT        NULL,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_montagem_comentario_anexos_comentario
    ON montagem_comentario_anexos (comentario_id);
