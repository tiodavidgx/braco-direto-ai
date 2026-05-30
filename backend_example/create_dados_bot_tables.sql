-- ============================================================
-- Tabelas para dados do bot externo (vendas, montagem, nmresolve)
-- Usado para cruzamento de dados no CRM e outros módulos
-- ============================================================

-- Tabela de vendas (pode chegar a 5M+ linhas)
CREATE TABLE IF NOT EXISTS bot_vendas (
    id BIGSERIAL PRIMARY KEY,
    identificador_pedido VARCHAR(50) NOT NULL,
    identificador_nf VARCHAR(50),
    identificador_segunda_nf VARCHAR(50),
    filial_saida VARCHAR(50),
    filial_saida_segunda_nf VARCHAR(50),
    numero_nf VARCHAR(50),
    numero_segunda_nf VARCHAR(50),
    serie_nf VARCHAR(20),
    serie_segunda_nf VARCHAR(20),
    filial_venda VARCHAR(50),
    nome_cliente VARCHAR(255),
    cpf_cnpj_cliente VARCHAR(20),
    cidade_nf VARCHAR(100),
    uf_nf VARCHAR(5),
    data_emissao DATE,
    data_previsao_entrega DATE,
    situacao_timeline VARCHAR(100),
    data_entrega_efetiva DATE,
    deseja_entrega VARCHAR(50),
    tipo_operacao_venda VARCHAR(100),
    telefone_cliente VARCHAR(30),
    situacao_nota VARCHAR(100),
    produto VARCHAR(50),
    nome_produto VARCHAR(255),
    -- Controle de importação
    lote_importacao VARCHAR(100),
    importado_em TIMESTAMP DEFAULT NOW()
);

-- Índices para busca rápida (chave principal = identificador_pedido)
CREATE INDEX IF NOT EXISTS idx_bot_vendas_pedido ON bot_vendas(identificador_pedido);
CREATE INDEX IF NOT EXISTS idx_bot_vendas_nf ON bot_vendas(identificador_nf);
CREATE INDEX IF NOT EXISTS idx_bot_vendas_cpf ON bot_vendas(cpf_cnpj_cliente);
CREATE INDEX IF NOT EXISTS idx_bot_vendas_nome ON bot_vendas(nome_cliente);
CREATE INDEX IF NOT EXISTS idx_bot_vendas_lote ON bot_vendas(lote_importacao);
CREATE INDEX IF NOT EXISTS idx_bot_vendas_data_emissao ON bot_vendas(data_emissao);

-- Tabela de NM Resolve
CREATE TABLE IF NOT EXISTS bot_nmresolve (
    id BIGSERIAL PRIMARY KEY,
    identificador_pedido VARCHAR(50) NOT NULL,
    identificador_nf VARCHAR(50),
    identificador_segunda_nf VARCHAR(50),
    filial_saida VARCHAR(50),
    filial_saida_segunda_nf VARCHAR(50),
    numero_nf VARCHAR(50),
    boletim VARCHAR(50),
    modalidade VARCHAR(100),
    situacao_boletim VARCHAR(100),
    situacao_servico VARCHAR(100),
    id_prestador VARCHAR(50),
    prestador VARCHAR(255),
    data_finalizacao DATE,
    nome_produto VARCHAR(255),
    produto VARCHAR(50),
    -- Controle de importação
    lote_importacao VARCHAR(100),
    importado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_nmresolve_pedido ON bot_nmresolve(identificador_pedido);
CREATE INDEX IF NOT EXISTS idx_bot_nmresolve_nf ON bot_nmresolve(identificador_nf);
CREATE INDEX IF NOT EXISTS idx_bot_nmresolve_boletim ON bot_nmresolve(boletim);
CREATE INDEX IF NOT EXISTS idx_bot_nmresolve_prestador ON bot_nmresolve(id_prestador);
CREATE INDEX IF NOT EXISTS idx_bot_nmresolve_lote ON bot_nmresolve(lote_importacao);

-- Tabela de Montagem
CREATE TABLE IF NOT EXISTS bot_montagem (
    id BIGSERIAL PRIMARY KEY,
    identificador_pedido VARCHAR(50) NOT NULL,
    identificador_nf VARCHAR(50),
    filial_saida VARCHAR(50),
    filial_venda VARCHAR(50),
    filial_montadora VARCHAR(50),
    nota_fiscal VARCHAR(50),
    serie_nota_fiscal VARCHAR(20),
    modalidade_servico VARCHAR(100),
    data_previsao_montagem DATE,
    data_montagem DATE,
    situacao_boletim VARCHAR(100),
    nome_montador VARCHAR(255),
    identificador_montador VARCHAR(50),
    -- Controle de importação
    lote_importacao VARCHAR(100),
    importado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_montagem_pedido ON bot_montagem(identificador_pedido);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_nf ON bot_montagem(identificador_nf);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_montador ON bot_montagem(identificador_montador);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_lote ON bot_montagem(lote_importacao);

-- Tabela de configuração da API do bot
CREATE TABLE IF NOT EXISTS bot_config (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(255) NOT NULL,
    descricao VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Log de importações
CREATE TABLE IF NOT EXISTS bot_import_log (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,
    lote VARCHAR(100) NOT NULL,
    arquivo_nome VARCHAR(255),
    linhas_recebidas INTEGER DEFAULT 0,
    linhas_inseridas INTEGER DEFAULT 0,
    linhas_ignoradas INTEGER DEFAULT 0,
    duracao_ms INTEGER,
    status VARCHAR(20) DEFAULT 'sucesso',
    erro TEXT,
    importado_em TIMESTAMP DEFAULT NOW()
);

-- Gerar uma API key padrão
INSERT INTO bot_config (api_key, descricao)
VALUES ('bot-braco-direto-2026-key', 'Chave padrão do bot de relatórios')
ON CONFLICT DO NOTHING;
