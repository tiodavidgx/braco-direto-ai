-- Tabela de Pré-Cadastro de Montadores (Onboarding)
-- Permite salvar cadastros em andamento para continuar depois

CREATE TABLE IF NOT EXISTS pre_cadastro_montadores (
    id SERIAL PRIMARY KEY,
    
    -- Dados básicos
    tipo_pessoa VARCHAR(4) NOT NULL CHECK (tipo_pessoa IN ('PF', 'PJ')), -- PF = Pessoa Física, PJ = Pessoa Jurídica
    nome VARCHAR(255) NOT NULL,
    cpf_cnpj VARCHAR(20),
    email VARCHAR(255),
    telefone VARCHAR(20),
    
    -- Localização
    filial VARCHAR(100),
    cidade VARCHAR(100),
    endereco TEXT,
    
    -- Dados bancários
    banco VARCHAR(100),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    tipo_conta VARCHAR(20), -- corrente, poupança, etc
    pix VARCHAR(100),
    
    -- Valores e comissões (preenchidos na negociação)
    percentual_montagem DECIMAL(5,2) DEFAULT 5.00,
    percentual_assistencia DECIMAL(5,2) DEFAULT 5.00,
    percentual_desmontagem DECIMAL(5,2) DEFAULT 5.00,
    auxilio_semanal DECIMAL(10,2) DEFAULT 100.00,
    
    -- Documentos (caminhos dos arquivos)
    doc_comprovante_endereco VARCHAR(500),
    doc_comprovante_bancario VARCHAR(500),
    doc_documento_pessoal VARCHAR(500),
    doc_comprovante_mei VARCHAR(500), -- Apenas para PJ
    
    -- Status do cadastro
    status VARCHAR(20) DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'aguardando_docs', 'em_analise', 'aprovado', 'rejeitado', 'convertido')),
    etapa_atual INTEGER DEFAULT 1, -- 1=Tipo, 2=Dados Pessoais, 3=Documentos, 4=Valores, 5=Revisão
    observacoes TEXT,
    
    -- Controle
    criado_por INTEGER REFERENCES users(id),
    atualizado_por INTEGER REFERENCES users(id),
    montador_id INTEGER REFERENCES montadores(id), -- Preenchido quando convertido
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_pre_cadastro_status ON pre_cadastro_montadores(status);
CREATE INDEX IF NOT EXISTS idx_pre_cadastro_criado_por ON pre_cadastro_montadores(criado_por);
CREATE INDEX IF NOT EXISTS idx_pre_cadastro_cpf_cnpj ON pre_cadastro_montadores(cpf_cnpj);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_pre_cadastro_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_pre_cadastro_timestamp ON pre_cadastro_montadores;
CREATE TRIGGER trigger_update_pre_cadastro_timestamp
    BEFORE UPDATE ON pre_cadastro_montadores
    FOR EACH ROW
    EXECUTE FUNCTION update_pre_cadastro_timestamp();
