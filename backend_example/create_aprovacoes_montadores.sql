-- ============================================================
-- Tabela de Aprovações de Edições de Montadores
-- Edições em campos críticos exigem aprovação do admin
-- ============================================================

CREATE TABLE IF NOT EXISTS aprovacoes_montador (
    id SERIAL PRIMARY KEY,
    
    -- Referência ao montador
    montador_id INTEGER NOT NULL REFERENCES montadores(id) ON DELETE CASCADE,
    
    -- Quem solicitou a edição
    usuario_id INTEGER NOT NULL,
    usuario_nome VARCHAR(255) NOT NULL,
    
    -- Detalhes da alteração
    campo VARCHAR(100) NOT NULL,
    valor_antigo TEXT,
    valor_novo TEXT NOT NULL,
    
    -- Status da aprovação
    status VARCHAR(20) DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'aprovado', 'rejeitado')),
    
    -- Quem aprovou/rejeitou
    aprovador_id INTEGER,
    aprovador_nome VARCHAR(255),
    motivo_rejeicao TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_aprovacoes_status ON aprovacoes_montador (status);
CREATE INDEX IF NOT EXISTS idx_aprovacoes_montador ON aprovacoes_montador (montador_id);
CREATE INDEX IF NOT EXISTS idx_aprovacoes_usuario ON aprovacoes_montador (usuario_id);
