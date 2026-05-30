-- ============================================================
-- Vínculo Montador → Terceirizada
-- Adiciona tipo_pagamento e terceirizada_id nas tabelas
-- ============================================================

-- Na tabela montadores
ALTER TABLE montadores 
    ADD COLUMN IF NOT EXISTS tipo_pagamento VARCHAR(20) DEFAULT 'novo_mundo'
        CHECK (tipo_pagamento IN ('novo_mundo', 'terceirizada')),
    ADD COLUMN IF NOT EXISTS terceirizada_id INTEGER REFERENCES terceirizadas(id);

CREATE INDEX IF NOT EXISTS idx_montadores_terceirizada 
    ON montadores (terceirizada_id) WHERE terceirizada_id IS NOT NULL;

-- Na tabela pre_cadastro_montadores
ALTER TABLE pre_cadastro_montadores 
    ADD COLUMN IF NOT EXISTS tipo_pagamento VARCHAR(20) DEFAULT 'novo_mundo'
        CHECK (tipo_pagamento IN ('novo_mundo', 'terceirizada')),
    ADD COLUMN IF NOT EXISTS terceirizada_id INTEGER REFERENCES terceirizadas(id);
