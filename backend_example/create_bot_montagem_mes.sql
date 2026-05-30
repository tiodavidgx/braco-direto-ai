-- Tabela da view nova "montagem_mes" (26 colunas enviadas pelo dev do ERP)
CREATE TABLE IF NOT EXISTS bot_montagem_mes (
    id BIGSERIAL PRIMARY KEY,
    identificador_pedido VARCHAR(50),
    identificador_nf VARCHAR(50),
    identificador_boletim_montagem VARCHAR(50),
    filial_saida VARCHAR(50),
    filial_venda VARCHAR(50),
    filial_montadora VARCHAR(50),
    nota_fiscal VARCHAR(50),
    serie_nota_fiscal VARCHAR(20),
    modalidade_servico VARCHAR(100),
    data_previsao_montagem DATE,
    data_emissao_nf DATE,
    data_previsao_entrega DATE,
    data_entrega DATE,
    situacao_boletim VARCHAR(100),
    situacao_timeline VARCHAR(100),
    identificador_montador VARCHAR(50),
    nome_montador VARCHAR(255),
    produto VARCHAR(100),
    nome_produto VARCHAR(255),
    uf VARCHAR(5),
    localidade VARCHAR(150),
    bairro VARCHAR(150),
    data_montagem DATE,
    data_agenda_montagem DATE,
    observacao_montagem TEXT,
    telefone_completo VARCHAR(50),
    -- Controle de importação
    lote_importacao VARCHAR(100),
    importado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_montagem_mes_pedido ON bot_montagem_mes(identificador_pedido);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_mes_nf ON bot_montagem_mes(identificador_nf);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_mes_boletim ON bot_montagem_mes(identificador_boletim_montagem);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_mes_montador ON bot_montagem_mes(identificador_montador);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_mes_lote ON bot_montagem_mes(lote_importacao);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_mes_data_previsao ON bot_montagem_mes(data_previsao_montagem);
CREATE INDEX IF NOT EXISTS idx_bot_montagem_mes_data_entrega ON bot_montagem_mes(data_entrega);

-- Unique constraint usada pelo INSERT ... ON CONFLICT no upload incremental
ALTER TABLE bot_montagem_mes
    DROP CONSTRAINT IF EXISTS bot_montagem_mes_dedup_uq;
ALTER TABLE bot_montagem_mes
    ADD CONSTRAINT bot_montagem_mes_dedup_uq
    UNIQUE (identificador_boletim_montagem, produto);
