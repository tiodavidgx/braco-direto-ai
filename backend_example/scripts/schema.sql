-- ===========================================
-- Schema Completo - Braço Direto AI
-- Execute este arquivo para criar todas as tabelas
-- ===========================================

-- Extensões
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- TABELAS PRINCIPAIS
-- ===========================================

-- Prestadores
CREATE TABLE IF NOT EXISTS prestadores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    telefone VARCHAR(50),
    documento VARCHAR(50),
    tipo_pessoa VARCHAR(20) DEFAULT 'PJ',
    filial VARCHAR(100),
    localidade VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Montadores
CREATE TABLE IF NOT EXISTS montadores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(50),
    documento VARCHAR(50),
    filial VARCHAR(100),
    localidade VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lotes
CREATE TABLE IF NOT EXISTS lotes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    data_inicio DATE,
    data_fim DATE,
    status VARCHAR(50) DEFAULT 'aberto',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ordens de Serviço (OS)
CREATE TABLE IF NOT EXISTS os (
    id SERIAL PRIMARY KEY,
    numero_os VARCHAR(100) NOT NULL,
    prestador_id INTEGER REFERENCES prestadores(id),
    montador_id INTEGER REFERENCES montadores(id),
    lote_id INTEGER REFERENCES lotes(id),
    cliente VARCHAR(255),
    endereco TEXT,
    cidade VARCHAR(100),
    uf VARCHAR(2),
    tipo_servico VARCHAR(100),
    valor DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'pendente',
    data_servico DATE,
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notas Fiscais
CREATE TABLE IF NOT EXISTS notas_fiscais (
    id SERIAL PRIMARY KEY,
    numero_nf VARCHAR(100),
    prestador_id INTEGER REFERENCES prestadores(id),
    montador_id INTEGER REFERENCES montadores(id),
    lote_id INTEGER REFERENCES lotes(id),
    valor DECIMAL(10,2),
    data_emissao DATE,
    data_recebimento DATE,
    arquivo_path TEXT,
    status VARCHAR(50) DEFAULT 'pendente',
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relatórios
CREATE TABLE IF NOT EXISTS relatorios (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, -- 'prestador' ou 'montador'
    referencia_id INTEGER NOT NULL,
    lote_id INTEGER REFERENCES lotes(id),
    periodo_inicio DATE,
    periodo_fim DATE,
    valor_total DECIMAL(10,2),
    quantidade_os INTEGER,
    arquivo_path TEXT,
    status VARCHAR(50) DEFAULT 'gerado',
    enviado_em TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- TABELAS WHATSAPP
-- ===========================================

-- Templates WhatsApp
CREATE TABLE IF NOT EXISTS templates_whatsapp (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL, -- 'prestador' ou 'montador'
    template TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    variaveis TEXT[],
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Automação/Gatilhos WhatsApp
CREATE TABLE IF NOT EXISTS automacao_whatsapp (
    id SERIAL PRIMARY KEY,
    evento TEXT NOT NULL UNIQUE,
    template_id INTEGER REFERENCES templates_whatsapp(id),
    ativo BOOLEAN NOT NULL DEFAULT FALSE,
    condicoes JSONB,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de Mensagens WhatsApp
CREATE TABLE IF NOT EXISTS historico_whatsapp (
    id SERIAL PRIMARY KEY,
    destinatario_tipo TEXT NOT NULL,
    destinatario_id INTEGER NOT NULL,
    destinatario_nome TEXT NOT NULL,
    numero_telefone TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    template_id INTEGER REFERENCES templates_whatsapp(id),
    evento TEXT,
    status TEXT NOT NULL DEFAULT 'pendente',
    erro TEXT,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_entregue TIMESTAMP
);

-- ===========================================
-- TABELAS EMAIL
-- ===========================================

-- Templates de Email
CREATE TABLE IF NOT EXISTS email_templates (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL UNIQUE,
    assunto VARCHAR(500) NOT NULL,
    corpo TEXT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    variaveis TEXT[],
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de Emails
CREATE TABLE IF NOT EXISTS historico_emails (
    id SERIAL PRIMARY KEY,
    destinatario_email VARCHAR(255) NOT NULL,
    destinatario_nome VARCHAR(255),
    assunto VARCHAR(500) NOT NULL,
    corpo TEXT NOT NULL,
    template_id INTEGER REFERENCES email_templates(id),
    status VARCHAR(50) DEFAULT 'enviado',
    erro TEXT,
    enviado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- TABELAS TRELLO
-- ===========================================

-- Cards Trello
CREATE TABLE IF NOT EXISTS trello_cards (
    id SERIAL PRIMARY KEY,
    card_id VARCHAR(100) UNIQUE NOT NULL,
    montador_id INTEGER REFERENCES montadores(id),
    os_id INTEGER REFERENCES os(id),
    nome_card VARCHAR(500),
    lista_id VARCHAR(100),
    lista_nome VARCHAR(255),
    status VARCHAR(50) DEFAULT 'ativo',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- TABELAS JOBS/AGENDAMENTOS
-- ===========================================

-- Jobs Agendados
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(100) NOT NULL,
    cron_expression VARCHAR(100),
    ultimo_execucao TIMESTAMP,
    proxima_execucao TIMESTAMP,
    status VARCHAR(50) DEFAULT 'ativo',
    configuracoes JSONB,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de Execução de Jobs
CREATE TABLE IF NOT EXISTS jobs_historico (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    inicio TIMESTAMP NOT NULL,
    fim TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    resultado JSONB,
    erro TEXT
);

-- ===========================================
-- TABELA BLACKLIST
-- ===========================================

CREATE TABLE IF NOT EXISTS blacklist (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, -- 'prestador' ou 'montador'
    referencia_id INTEGER NOT NULL,
    motivo TEXT,
    data_inclusao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    incluido_por VARCHAR(255)
);

-- ===========================================
-- ÍNDICES
-- ===========================================

CREATE INDEX IF NOT EXISTS idx_os_prestador ON os(prestador_id);
CREATE INDEX IF NOT EXISTS idx_os_montador ON os(montador_id);
CREATE INDEX IF NOT EXISTS idx_os_lote ON os(lote_id);
CREATE INDEX IF NOT EXISTS idx_os_status ON os(status);
CREATE INDEX IF NOT EXISTS idx_nf_prestador ON notas_fiscais(prestador_id);
CREATE INDEX IF NOT EXISTS idx_nf_montador ON notas_fiscais(montador_id);
CREATE INDEX IF NOT EXISTS idx_historico_whatsapp_destinatario ON historico_whatsapp(destinatario_tipo, destinatario_id);
CREATE INDEX IF NOT EXISTS idx_historico_whatsapp_data ON historico_whatsapp(data_envio);
CREATE INDEX IF NOT EXISTS idx_historico_whatsapp_status ON historico_whatsapp(status);
CREATE INDEX IF NOT EXISTS idx_trello_cards_montador ON trello_cards(montador_id);

-- ===========================================
-- DADOS INICIAIS
-- ===========================================

-- Templates WhatsApp padrão
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES 
    ('prestador_notificacao_relatorio', 'prestador', 
     E'Olá {{nome_prestador}}! 👋\n\nSeu relatório do período {{periodo}} já está disponível.\n\n💰 Valor total: R$ {{valor}}\n🔗 Link: {{link}}\n\nQualquer dúvida, estamos à disposição!',
     ARRAY['nome_prestador', 'periodo', 'valor', 'link']),
    
    ('prestador_lembrete_nf', 'prestador',
     E'Olá {{nome_prestador}}! 📋\n\nLembramos que você precisa enviar a Nota Fiscal referente ao relatório de {{periodo}}.\n\n💰 Valor: R$ {{valor}}\n\n📨 Por favor, envie o quanto antes para agilizar o pagamento.',
     ARRAY['nome_prestador', 'periodo', 'valor']),
    
    ('montador_notificacao_relatorio', 'montador',
     E'Olá {{nome_montador}}! 👋\n\nSeu relatório do período {{periodo_relatorio}} já está disponível.\n\n💰 Valor total: R$ {{valor_total}}\n📦 Total de OSs: {{quantidade_os}}\n🔗 Link: {{link}}\n\nQualquer dúvida, estamos à disposição!',
     ARRAY['nome_montador', 'periodo_relatorio', 'valor_total', 'quantidade_os', 'link']),
    
    ('montador_lembrete_nf', 'montador',
     E'Olá {{nome_montador}}! 📋\n\nLembramos que você precisa enviar a Nota Fiscal referente ao relatório de {{periodo_relatorio}}.\n\n💰 Valor: R$ {{valor_total}}\n\n📨 Por favor, envie o quanto antes para agilizar o pagamento.',
     ARRAY['nome_montador', 'periodo_relatorio', 'valor_total']),

    ('nf_recebida_prestador', 'prestador',
     E'✅ {{nome_prestador}}, recebemos sua Nota Fiscal!\n\nNúmero: {{numero_nf}}\nValor: R$ {{valor}}\n\nObrigado! O pagamento será processado em breve.',
     ARRAY['nome_prestador', 'numero_nf', 'valor']),

    ('nf_recebida_montador', 'montador',
     E'✅ {{nome_montador}}, recebemos sua Nota Fiscal!\n\nNúmero: {{numero_nf}}\nValor: R$ {{valor}}\n\nObrigado! O pagamento será processado em breve.',
     ARRAY['nome_montador', 'numero_nf', 'valor']),

    ('card_trello_criado', 'montador',
     E'📋 {{nome_montador}}, um novo serviço foi atribuído a você!\n\nOS: {{numero_os}}\nCliente: {{cliente}}\nEndereço: {{endereco}}\n\nAcesse o Trello para mais detalhes.',
     ARRAY['nome_montador', 'numero_os', 'cliente', 'endereco'])
ON CONFLICT (nome) DO NOTHING;

-- Gatilhos de automação WhatsApp
INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'relatorio_enviado_prestador', id, FALSE, NULL
FROM templates_whatsapp WHERE nome = 'prestador_notificacao_relatorio'
ON CONFLICT (evento) DO NOTHING;

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'relatorio_enviado_montador', id, FALSE, NULL
FROM templates_whatsapp WHERE nome = 'montador_notificacao_relatorio'
ON CONFLICT (evento) DO NOTHING;

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'nf_recebida_prestador', id, FALSE, NULL
FROM templates_whatsapp WHERE nome = 'nf_recebida_prestador'
ON CONFLICT (evento) DO NOTHING;

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'nf_recebida_montador', id, FALSE, NULL
FROM templates_whatsapp WHERE nome = 'nf_recebida_montador'
ON CONFLICT (evento) DO NOTHING;

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'card_trello_criado', id, FALSE, NULL
FROM templates_whatsapp WHERE nome = 'card_trello_criado'
ON CONFLICT (evento) DO NOTHING;

-- Templates de Email padrão
INSERT INTO email_templates (nome, assunto, corpo, tipo, variaveis)
VALUES 
    ('relatorio_prestador', 
     'Relatório de Serviços - {{periodo}}',
     E'<h2>Olá {{nome}}!</h2>\n<p>Segue em anexo seu relatório de serviços do período {{periodo}}.</p>\n<p>Valor total: <strong>R$ {{valor}}</strong></p>\n<p>Atenciosamente,<br>Braço Direto</p>',
     'prestador',
     ARRAY['nome', 'periodo', 'valor']),
    
    ('relatorio_montador',
     'Relatório de Montagens - {{periodo}}',
     E'<h2>Olá {{nome}}!</h2>\n<p>Segue em anexo seu relatório de montagens do período {{periodo}}.</p>\n<p>Valor total: <strong>R$ {{valor}}</strong></p>\n<p>Total de OSs: {{quantidade_os}}</p>\n<p>Atenciosamente,<br>Braço Direto</p>',
     'montador',
     ARRAY['nome', 'periodo', 'valor', 'quantidade_os'])
ON CONFLICT (nome) DO NOTHING;

-- ===========================================
-- FIM DO SCHEMA
-- ===========================================
