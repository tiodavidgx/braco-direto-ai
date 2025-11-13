-- Script para criar tabela de configuração de jobs
-- Execute este script no seu banco de dados PostgreSQL

-- Criar tabela jobs_config
CREATE TABLE IF NOT EXISTS jobs_config (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    intervalo_minutos INTEGER DEFAULT 60,
    ultima_execucao TIMESTAMP,
    proxima_execucao TIMESTAMP,
    total_execucoes INTEGER DEFAULT 0,
    total_erros INTEGER DEFAULT 0,
    ultima_mensagem TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir job padrão de consulta de notas
INSERT INTO jobs_config (nome, descricao, ativo, intervalo_minutos)
VALUES (
    'consulta_notas',
    'Consulta notas fiscais na API e cria cards no Trello',
    TRUE,
    60
)
ON CONFLICT (nome) DO NOTHING;

-- Verificar se foi criado corretamente
SELECT * FROM jobs_config;
