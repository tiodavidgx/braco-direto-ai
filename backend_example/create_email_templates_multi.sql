-- ============================================================
-- Evoluir email_config para suportar múltiplos templates
-- + Adicionar email_template_id nos montadores
-- ============================================================

-- 1. Remover constraint UNIQUE(tipo) para permitir múltiplos templates
ALTER TABLE email_config DROP CONSTRAINT IF EXISTS email_config_tipo_key;

-- 2. Adicionar novas colunas para multi-template
ALTER TABLE email_config 
    ADD COLUMN IF NOT EXISTS nome VARCHAR(100),
    ADD COLUMN IF NOT EXISTS descricao TEXT,
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS variaveis TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE;

-- 3. Atualizar registros existentes com nomes padrão
UPDATE email_config SET nome = 'Padrão Prestador', is_default = TRUE WHERE tipo = 'prestador' AND nome IS NULL;
UPDATE email_config SET nome = 'Padrão Montador', is_default = TRUE WHERE tipo = 'montador' AND nome IS NULL;

-- 4. Garantir que só existe 1 default por tipo (limpar defaults duplicados)
UPDATE email_config SET is_default = FALSE WHERE id NOT IN (
    SELECT MIN(id) FROM email_config WHERE tipo = 'prestador'
) AND tipo = 'prestador';
UPDATE email_config SET is_default = FALSE WHERE id NOT IN (
    SELECT MIN(id) FROM email_config WHERE tipo = 'montador'
) AND tipo = 'montador';
UPDATE email_config SET is_default = TRUE WHERE id IN (
    SELECT MIN(id) FROM email_config WHERE tipo = 'prestador'
) AND tipo = 'prestador';
UPDATE email_config SET is_default = TRUE WHERE id IN (
    SELECT MIN(id) FROM email_config WHERE tipo = 'montador'
) AND tipo = 'montador';

-- 5. Adicionar email_template_id nos montadores (opcional, FK para email_config)
ALTER TABLE montadores
    ADD COLUMN IF NOT EXISTS email_template_id INTEGER REFERENCES email_config(id);

-- 6. Adicionar email_template_id no pre_cadastro_montadores
ALTER TABLE pre_cadastro_montadores
    ADD COLUMN IF NOT EXISTS email_template_id INTEGER REFERENCES email_config(id);

-- 7. Adicionar variáveis padrão nos templates existentes
UPDATE email_config SET variaveis = '{"{{periodo}}", "{{nome_prestador}}", "{{link_upload}}"}' 
    WHERE tipo = 'prestador' AND variaveis = '{}';
UPDATE email_config SET variaveis = '{"{{periodo_relatorio}}", "{{nome_montador}}", "{{link_upload}}"}' 
    WHERE tipo = 'montador' AND variaveis = '{}';
