-- =====================================================
-- ACOMPANHAMENTO DE MONTAGEM
-- Marcações locais (início/conclusão) que complementam a
-- view vw_acompanhamento_montagem provida pelo ERP.
-- =====================================================

CREATE TABLE IF NOT EXISTS montagem_marcacoes (
    pedido_id            VARCHAR(80) PRIMARY KEY,
    iniciado_em          TIMESTAMP WITH TIME ZONE,
    iniciado_por_user_id INTEGER,
    concluido_em         TIMESTAMP WITH TIME ZONE,
    concluido_por_user_id INTEGER,
    observacao           TEXT,
    motivo_atraso        TEXT,
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_montagem_marcacoes_concluido
    ON montagem_marcacoes (concluido_em);

CREATE INDEX IF NOT EXISTS idx_montagem_marcacoes_iniciado
    ON montagem_marcacoes (iniciado_em);

-- Trigger para manter updated_at
CREATE OR REPLACE FUNCTION set_montagem_marcacoes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_montagem_marcacoes_updated_at ON montagem_marcacoes;
CREATE TRIGGER trg_montagem_marcacoes_updated_at
    BEFORE UPDATE ON montagem_marcacoes
    FOR EACH ROW EXECUTE FUNCTION set_montagem_marcacoes_updated_at();
