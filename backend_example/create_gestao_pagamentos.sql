-- =====================================================
-- SISTEMA DE GESTÃO DE PAGAMENTOS - ROTEIRO FINANCEIRO
-- =====================================================

-- Tabela de configuração do orçamento diário
CREATE TABLE IF NOT EXISTS configuracao_orcamento (
    id SERIAL PRIMARY KEY,
    orcamento_diario DECIMAL(15, 2) NOT NULL DEFAULT 40000.00,
    dia_inicio_semana INTEGER DEFAULT 1, -- 1 = Segunda
    dias_uteis_semana INTEGER DEFAULT 5,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir configuração padrão
INSERT INTO configuracao_orcamento (orcamento_diario) 
VALUES (40000.00) 
ON CONFLICT DO NOTHING;

-- Tabela de prioridades de fornecedores (Tiers)
-- Tier 1: Crítico (não pode atrasar)
-- Tier 2: Alta prioridade
-- Tier 3: Média prioridade
-- Tier 4: Baixa prioridade (pode esperar)
CREATE TABLE IF NOT EXISTS fornecedor_prioridades (
    id SERIAL PRIMARY KEY,
    nome_fornecedor VARCHAR(255) NOT NULL,
    cnpj_cpf VARCHAR(20),
    tier INTEGER NOT NULL DEFAULT 3 CHECK (tier >= 1 AND tier <= 4),
    descricao TEXT,
    max_dias_atraso INTEGER DEFAULT 0, -- Quantos dias pode atrasar sem problemas
    notas TEXT, -- Observações sobre o fornecedor
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nome_fornecedor)
);

-- Tabela de exceções de pagamento
-- Para casos especiais como "prestador X precisa de R$ 80k esta semana"
CREATE TABLE IF NOT EXISTS pagamento_excecoes (
    id SERIAL PRIMARY KEY,
    nome_fornecedor VARCHAR(255) NOT NULL,
    cnpj_cpf VARCHAR(20),
    valor_solicitado DECIMAL(15, 2) NOT NULL,
    data_necessidade DATE NOT NULL, -- Quando precisa do dinheiro
    data_limite DATE, -- Até quando pode pagar
    motivo TEXT NOT NULL, -- Ex: "Pagar impostos"
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'aprovado', 'pago', 'cancelado')),
    prioridade_especial INTEGER DEFAULT 1, -- 1 = máxima urgência
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de títulos importados (contas a pagar)
CREATE TABLE IF NOT EXISTS titulos_importados (
    id SERIAL PRIMARY KEY,
    numero_titulo VARCHAR(100),
    nome_fornecedor VARCHAR(255) NOT NULL,
    cnpj_cpf VARCHAR(20),
    valor DECIMAL(15, 2) NOT NULL,
    data_vencimento DATE NOT NULL,
    data_emissao DATE,
    descricao TEXT,
    categoria VARCHAR(100), -- Tipo de despesa
    banco VARCHAR(100),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    pix VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'agendado', 'pago', 'cancelado')),
    data_agendamento DATE, -- Data que foi agendado para pagar
    lote_importacao VARCHAR(50), -- Identificador do lote de importação
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de roteiros gerados
CREATE TABLE IF NOT EXISTS roteiros_pagamento (
    id SERIAL PRIMARY KEY,
    data_roteiro DATE NOT NULL,
    orcamento_dia DECIMAL(15, 2) NOT NULL,
    total_agendado DECIMAL(15, 2) NOT NULL,
    total_titulos INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'gerado' CHECK (status IN ('gerado', 'executando', 'concluido')),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de itens do roteiro
CREATE TABLE IF NOT EXISTS roteiro_itens (
    id SERIAL PRIMARY KEY,
    roteiro_id INTEGER NOT NULL REFERENCES roteiros_pagamento(id) ON DELETE CASCADE,
    titulo_id INTEGER REFERENCES titulos_importados(id),
    excecao_id INTEGER REFERENCES pagamento_excecoes(id),
    nome_fornecedor VARCHAR(255) NOT NULL,
    valor DECIMAL(15, 2) NOT NULL,
    tier INTEGER,
    motivo_priorizacao TEXT, -- "Tier 1 - Crítico", "Exceção: Impostos", etc.
    ordem INTEGER NOT NULL, -- Ordem no roteiro
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'pago'))
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_titulos_vencimento ON titulos_importados(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_titulos_fornecedor ON titulos_importados(nome_fornecedor);
CREATE INDEX IF NOT EXISTS idx_titulos_status ON titulos_importados(status);
CREATE INDEX IF NOT EXISTS idx_excecoes_data ON pagamento_excecoes(data_necessidade);
CREATE INDEX IF NOT EXISTS idx_excecoes_status ON pagamento_excecoes(status);
CREATE INDEX IF NOT EXISTS idx_fornecedor_tier ON fornecedor_prioridades(tier);
CREATE INDEX IF NOT EXISTS idx_roteiro_data ON roteiros_pagamento(data_roteiro);

-- Comentários nas tabelas
COMMENT ON TABLE configuracao_orcamento IS 'Configuração do orçamento diário para pagamentos';
COMMENT ON TABLE fornecedor_prioridades IS 'Tiers de prioridade por fornecedor (1=Crítico, 4=Baixa)';
COMMENT ON TABLE pagamento_excecoes IS 'Exceções de pagamento - casos especiais com urgência';
COMMENT ON TABLE titulos_importados IS 'Títulos a pagar importados de planilhas';
COMMENT ON TABLE roteiros_pagamento IS 'Roteiros de pagamento gerados por dia';
COMMENT ON TABLE roteiro_itens IS 'Itens individuais de cada roteiro';
