-- CRM Tables Migration
-- Run: psql -U braco -d braco_db -f create_crm_tables.sql

-- Add CRM permission columns to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS crm_solicitante BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS crm_analista BOOLEAN DEFAULT FALSE;

-- CRM Tickets
CREATE TABLE IF NOT EXISTS crm_tickets (
    id SERIAL PRIMARY KEY,
    id_pedido VARCHAR(100) NOT NULL,
    nome_cliente VARCHAR(255) NOT NULL,
    telefone VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    anexo_url TEXT DEFAULT '',
    anexo_nome VARCHAR(255),
    motivo VARCHAR(100) NOT NULL,
    descricao TEXT NOT NULL,
    glpi VARCHAR(100) DEFAULT '',
    id_processo VARCHAR(100) DEFAULT '',
    plataforma VARCHAR(100) DEFAULT '',
    credenciada VARCHAR(100) DEFAULT '',
    prazo DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'novo' CHECK (status IN ('novo', 'em_andamento', 'resolvido')),
    solicitante_id INTEGER NOT NULL REFERENCES users(id),
    solicitante_nome VARCHAR(255) NOT NULL,
    analista_id INTEGER REFERENCES users(id),
    analista_nome VARCHAR(255),
    tipo_operacao_venda VARCHAR(100),
    situacao_timeline VARCHAR(100),
    status_detalhe VARCHAR(100) DEFAULT 'Novo',
    resolucao VARCHAR(255),
    descricao_resolucao TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- CRM Comments
CREATE TABLE IF NOT EXISTS crm_comentarios (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES crm_tickets(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES users(id),
    usuario_nome VARCHAR(255) NOT NULL,
    texto TEXT DEFAULT '',
    status_detalhe VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CRM Comment Attachments
CREATE TABLE IF NOT EXISTS crm_comentario_anexos (
    id SERIAL PRIMARY KEY,
    comentario_id INTEGER NOT NULL REFERENCES crm_comentarios(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    tipo VARCHAR(100) DEFAULT ''
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_crm_tickets_status ON crm_tickets(status);
CREATE INDEX IF NOT EXISTS idx_crm_tickets_id_pedido ON crm_tickets(id_pedido);
CREATE INDEX IF NOT EXISTS idx_crm_tickets_analista ON crm_tickets(analista_id);
CREATE INDEX IF NOT EXISTS idx_crm_tickets_solicitante ON crm_tickets(solicitante_id);
CREATE INDEX IF NOT EXISTS idx_crm_comentarios_ticket ON crm_comentarios(ticket_id);
