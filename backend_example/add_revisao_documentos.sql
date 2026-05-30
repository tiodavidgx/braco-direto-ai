-- Adicionar colunas para revisão de documentos na tabela pre_cadastro_montadores

-- Status de cada documento: null (não revisado), 'aprovado', 'recusado'
ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_documento_pessoal_status VARCHAR(20) DEFAULT NULL;

ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_documento_pessoal_motivo TEXT DEFAULT NULL;

ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_comprovante_endereco_status VARCHAR(20) DEFAULT NULL;

ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_comprovante_endereco_motivo TEXT DEFAULT NULL;

ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_comprovante_bancario_status VARCHAR(20) DEFAULT NULL;

ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_comprovante_bancario_motivo TEXT DEFAULT NULL;

ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_comprovante_mei_status VARCHAR(20) DEFAULT NULL;

ALTER TABLE pre_cadastro_montadores 
ADD COLUMN IF NOT EXISTS doc_comprovante_mei_motivo TEXT DEFAULT NULL;

-- Adicionar check constraints para os status
-- (PostgreSQL não suporta ALTER ADD CONSTRAINT IF NOT EXISTS, então usamos DO block)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_doc_documento_pessoal_status'
    ) THEN
        ALTER TABLE pre_cadastro_montadores 
        ADD CONSTRAINT chk_doc_documento_pessoal_status 
        CHECK (doc_documento_pessoal_status IS NULL OR doc_documento_pessoal_status IN ('aprovado', 'recusado'));
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_doc_comprovante_endereco_status'
    ) THEN
        ALTER TABLE pre_cadastro_montadores 
        ADD CONSTRAINT chk_doc_comprovante_endereco_status 
        CHECK (doc_comprovante_endereco_status IS NULL OR doc_comprovante_endereco_status IN ('aprovado', 'recusado'));
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_doc_comprovante_bancario_status'
    ) THEN
        ALTER TABLE pre_cadastro_montadores 
        ADD CONSTRAINT chk_doc_comprovante_bancario_status 
        CHECK (doc_comprovante_bancario_status IS NULL OR doc_comprovante_bancario_status IN ('aprovado', 'recusado'));
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_doc_comprovante_mei_status'
    ) THEN
        ALTER TABLE pre_cadastro_montadores 
        ADD CONSTRAINT chk_doc_comprovante_mei_status 
        CHECK (doc_comprovante_mei_status IS NULL OR doc_comprovante_mei_status IN ('aprovado', 'recusado'));
    END IF;
END
$$;

-- Comentários
COMMENT ON COLUMN pre_cadastro_montadores.doc_documento_pessoal_status IS 'Status da revisão: null=pendente, aprovado, recusado';
COMMENT ON COLUMN pre_cadastro_montadores.doc_documento_pessoal_motivo IS 'Motivo da recusa (se recusado)';
COMMENT ON COLUMN pre_cadastro_montadores.doc_comprovante_endereco_status IS 'Status da revisão: null=pendente, aprovado, recusado';
COMMENT ON COLUMN pre_cadastro_montadores.doc_comprovante_endereco_motivo IS 'Motivo da recusa (se recusado)';
COMMENT ON COLUMN pre_cadastro_montadores.doc_comprovante_bancario_status IS 'Status da revisão: null=pendente, aprovado, recusado';
COMMENT ON COLUMN pre_cadastro_montadores.doc_comprovante_bancario_motivo IS 'Motivo da recusa (se recusado)';
COMMENT ON COLUMN pre_cadastro_montadores.doc_comprovante_mei_status IS 'Status da revisão: null=pendente, aprovado, recusado';
COMMENT ON COLUMN pre_cadastro_montadores.doc_comprovante_mei_motivo IS 'Motivo da recusa (se recusado)';
