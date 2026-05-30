-- Tabelas de parâmetros do CRM
-- Motivos e Status Detalhe dinâmicos

CREATE TABLE IF NOT EXISTS crm_motivos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ordem INT NOT NULL DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm_status_detalhe (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    cor VARCHAR(30) DEFAULT 'gray',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ordem INT NOT NULL DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed motivos padrão
INSERT INTO crm_motivos (nome, ordem) VALUES
  ('Atraso na entrega', 1),
  ('Produto danificado', 2),
  ('Produto errado', 3),
  ('Falta de peças', 4),
  ('Montagem incorreta', 5),
  ('Cancelamento', 6),
  ('Reembolso', 7),
  ('Troca', 8),
  ('Reclamação de qualidade', 9),
  ('Problema com NF', 10),
  ('Divergência de valor', 11),
  ('Outro', 12)
ON CONFLICT (nome) DO NOTHING;

-- Seed status detalhe padrão
INSERT INTO crm_status_detalhe (nome, cor, ordem) VALUES
  ('Novo', 'gray', 1),
  ('Em Análise', 'blue', 2),
  ('Aguardando Cliente', 'amber', 3),
  ('Aguardando Fornecedor', 'amber', 4),
  ('Aguardando Transportadora', 'amber', 5),
  ('Em Andamento', 'blue', 6),
  ('Pendente Montagem', 'orange', 7),
  ('Pendente Troca', 'orange', 8),
  ('Pendente Peças', 'orange', 9),
  ('Resolvido', 'emerald', 10)
ON CONFLICT (nome) DO NOTHING;
