-- Adiciona campos filial e localidade nas tabelas de prestadores e montadores

-- Adicionar colunas na tabela prestadores
ALTER TABLE prestadores ADD COLUMN IF NOT EXISTS filial VARCHAR(100);
ALTER TABLE prestadores ADD COLUMN IF NOT EXISTS localidade VARCHAR(100);

-- Adicionar colunas na tabela montadores
ALTER TABLE montadores ADD COLUMN IF NOT EXISTS filial VARCHAR(100);
ALTER TABLE montadores ADD COLUMN IF NOT EXISTS localidade VARCHAR(100);

-- Comentários para documentação
COMMENT ON COLUMN prestadores.filial IS 'Filial do prestador';
COMMENT ON COLUMN prestadores.localidade IS 'Localidade/cidade do prestador';
COMMENT ON COLUMN montadores.filial IS 'Filial do montador';
COMMENT ON COLUMN montadores.localidade IS 'Localidade/cidade do montador';
