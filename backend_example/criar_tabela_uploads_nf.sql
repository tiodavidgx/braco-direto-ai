-- Sistema interno de upload de Notas Fiscais
-- Compatível com sistema externo (api.link.dev.br) - migração gradual

-- Tabela para controlar links de upload
CREATE TABLE IF NOT EXISTS uploads_nf (
    id SERIAL PRIMARY KEY,
    
    -- Hash único para o link público
    hash VARCHAR(64) UNIQUE NOT NULL,
    
    -- Tipo: 'prestador' ou 'montador'
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('prestador', 'montador')),
    
    -- Referência ao lote ou envio
    lote_id INTEGER REFERENCES lotes_servico(id) ON DELETE CASCADE,
    envio_montagem_id INTEGER REFERENCES envios_montagem(id) ON DELETE CASCADE,
    
    -- Status: 0=aguardando, 1=upload realizado, 2=expirado
    status INTEGER DEFAULT 0,
    
    -- Controle de validade
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_expiracao TIMESTAMP NOT NULL,
    data_upload TIMESTAMP,
    
    -- Quem acessou/fez upload (IP para auditoria)
    ip_acesso VARCHAR(50),
    ip_upload VARCHAR(50),
    
    -- Flag para identificar se é sistema interno ou externo
    sistema VARCHAR(20) DEFAULT 'interno' CHECK (sistema IN ('interno', 'externo')),
    
    -- Constraint: deve ter lote_id OU envio_montagem_id
    CONSTRAINT check_referencia CHECK (
        (tipo = 'prestador' AND lote_id IS NOT NULL AND envio_montagem_id IS NULL) OR
        (tipo = 'montador' AND envio_montagem_id IS NOT NULL AND lote_id IS NULL)
    )
);

-- Tabela para armazenar os arquivos enviados
CREATE TABLE IF NOT EXISTS uploads_nf_arquivos (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER NOT NULL REFERENCES uploads_nf(id) ON DELETE CASCADE,
    
    -- Informações do arquivo
    nome_original VARCHAR(255) NOT NULL,
    nome_salvo VARCHAR(255) NOT NULL,
    caminho VARCHAR(500) NOT NULL,
    extensao VARCHAR(10) NOT NULL,
    tamanho_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100),
    
    -- Hash do arquivo para verificar integridade
    hash_arquivo VARCHAR(64),
    
    data_upload TIMESTAMP DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_uploads_nf_hash ON uploads_nf(hash);
CREATE INDEX IF NOT EXISTS idx_uploads_nf_lote ON uploads_nf(lote_id) WHERE lote_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_uploads_nf_envio ON uploads_nf(envio_montagem_id) WHERE envio_montagem_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_uploads_nf_status ON uploads_nf(status);
CREATE INDEX IF NOT EXISTS idx_uploads_nf_expiracao ON uploads_nf(data_expiracao);

CREATE INDEX IF NOT EXISTS idx_uploads_nf_arquivos_upload ON uploads_nf_arquivos(upload_id);

-- Comentários
COMMENT ON TABLE uploads_nf IS 'Controle de links de upload de notas fiscais (sistema interno)';
COMMENT ON COLUMN uploads_nf.hash IS 'Hash único usado na URL pública do upload';
COMMENT ON COLUMN uploads_nf.sistema IS 'interno = novo sistema, externo = api.link.dev.br (legado)';
COMMENT ON TABLE uploads_nf_arquivos IS 'Arquivos enviados através do sistema de upload';

-- Função para gerar hash único
CREATE OR REPLACE FUNCTION gerar_hash_upload() RETURNS VARCHAR(64) AS $$
DECLARE
    novo_hash VARCHAR(64);
    existe BOOLEAN;
BEGIN
    LOOP
        -- Gera hash com timestamp + random
        novo_hash := encode(
            sha256(
                (extract(epoch from now())::text || random()::text || random()::text)::bytea
            ),
            'hex'
        );
        -- Pega apenas 32 caracteres
        novo_hash := substring(novo_hash from 1 for 32);
        
        -- Verifica se já existe
        SELECT EXISTS(SELECT 1 FROM uploads_nf WHERE hash = novo_hash) INTO existe;
        
        IF NOT existe THEN
            RETURN novo_hash;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- View para consultar uploads pendentes (compatível com sistema antigo)
CREATE OR REPLACE VIEW v_uploads_pendentes AS
SELECT 
    u.id,
    u.hash,
    u.tipo,
    u.lote_id,
    u.envio_montagem_id,
    u.status,
    u.data_criacao,
    u.data_expiracao,
    u.data_upload,
    u.sistema,
    CASE 
        WHEN u.tipo = 'prestador' THEN l.prestador_nome
        WHEN u.tipo = 'montador' THEN e.montador_nome
    END as nome_entidade,
    CASE 
        WHEN u.tipo = 'prestador' THEN l.periodo
        WHEN u.tipo = 'montador' THEN e.periodo
    END as periodo,
    CASE 
        WHEN u.tipo = 'prestador' THEN l.valor_total
        WHEN u.tipo = 'montador' THEN e.valor_total
    END as valor_total,
    COALESCE(
        (SELECT COUNT(*) FROM uploads_nf_arquivos WHERE upload_id = u.id),
        0
    ) as total_arquivos
FROM uploads_nf u
LEFT JOIN lotes_servico l ON u.lote_id = l.id
LEFT JOIN envios_montagem e ON u.envio_montagem_id = e.id
WHERE u.status = 0 
  AND u.data_expiracao > NOW()
  AND u.sistema = 'interno';

SELECT 'Tabelas de upload interno criadas com sucesso!' as resultado;
