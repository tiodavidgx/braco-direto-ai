-- Comentários do kanban de Montagem 24h. Cada registro é imutável.
CREATE TABLE IF NOT EXISTS montagem_comentarios (
    id            BIGSERIAL PRIMARY KEY,
    pedido_id     TEXT        NOT NULL,
    texto         TEXT        NOT NULL,
    tipo          TEXT        NOT NULL DEFAULT 'comentario',
        -- valores: comentario | adiamento_cliente_outra_data
        --         | adiamento_telefone_invalido | retomada
    nova_data     TIMESTAMP   NULL,
    autor_id      INTEGER     NULL,
    autor_nome    TEXT        NULL,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_montagem_comentarios_pedido
    ON montagem_comentarios (pedido_id, criado_em);

-- Adiamento ativo (um por pedido). Quando retomado, ativo = FALSE.
CREATE TABLE IF NOT EXISTS montagem_adiamentos (
    id                   BIGSERIAL PRIMARY KEY,
    pedido_id            TEXT        NOT NULL,
    motivo               TEXT        NOT NULL,
    motivo_descricao     TEXT        NULL,
    nova_data            TIMESTAMP   NULL,
    retorno_em           TIMESTAMP   NULL,
    confirmou_vitrine    BOOLEAN     NOT NULL DEFAULT FALSE,
    observacao           TEXT        NULL,
    criado_em            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por_user_id   INTEGER     NULL,
    criado_por_nome      TEXT        NULL,
    ativo                BOOLEAN     NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_montagem_adiamentos_ativo
    ON montagem_adiamentos (pedido_id) WHERE ativo;
CREATE INDEX IF NOT EXISTS idx_montagem_adiamentos_pedido
    ON montagem_adiamentos (pedido_id, criado_em);
