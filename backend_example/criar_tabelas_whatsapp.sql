-- Tabelas para integração WhatsApp e Automação

-- Tabela de templates WhatsApp
CREATE TABLE IF NOT EXISTS templates_whatsapp (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL, -- 'prestador' ou 'montador'
    template TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    variaveis TEXT[], -- Array de variáveis disponíveis
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de automação/gatilhos WhatsApp
CREATE TABLE IF NOT EXISTS automacao_whatsapp (
    id SERIAL PRIMARY KEY,
    evento TEXT NOT NULL UNIQUE,
    template_id INTEGER REFERENCES templates_whatsapp(id),
    ativo BOOLEAN NOT NULL DEFAULT FALSE,
    condicoes JSONB, -- Condições adicionais (ex: dias_antes, horario)
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de histórico de mensagens WhatsApp enviadas
CREATE TABLE IF NOT EXISTS historico_whatsapp (
    id SERIAL PRIMARY KEY,
    destinatario_tipo TEXT NOT NULL, -- 'prestador' ou 'montador'
    destinatario_id INTEGER NOT NULL,
    destinatario_nome TEXT NOT NULL,
    numero_telefone TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    template_id INTEGER REFERENCES templates_whatsapp(id),
    evento TEXT, -- Evento que disparou (se automático)
    status TEXT NOT NULL DEFAULT 'pendente', -- 'pendente', 'enviado', 'erro'
    erro TEXT,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_entregue TIMESTAMP
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_historico_whatsapp_destinatario ON historico_whatsapp(destinatario_tipo, destinatario_id);
CREATE INDEX IF NOT EXISTS idx_historico_whatsapp_data ON historico_whatsapp(data_envio);
CREATE INDEX IF NOT EXISTS idx_historico_whatsapp_status ON historico_whatsapp(status);

-- Adicionar campo telefone nas tabelas se não existir
ALTER TABLE prestadores ADD COLUMN IF NOT EXISTS telefone TEXT;
ALTER TABLE montadores ADD COLUMN IF NOT EXISTS telefone TEXT;

-- Inserir templates padrão se não existirem
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
     ARRAY['nome_montador', 'periodo_relatorio', 'valor_total'])
ON CONFLICT (nome) DO NOTHING;

-- Inserir gatilhos padrão se não existirem
INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 
    'envio_email_prestador',
    (SELECT id FROM templates_whatsapp WHERE nome = 'prestador_notificacao_relatorio'),
    FALSE,
    NULL
WHERE NOT EXISTS (SELECT 1 FROM automacao_whatsapp WHERE evento = 'envio_email_prestador');

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 
    'envio_email_montador',
    (SELECT id FROM templates_whatsapp WHERE nome = 'montador_notificacao_relatorio'),
    FALSE,
    NULL
WHERE NOT EXISTS (SELECT 1 FROM automacao_whatsapp WHERE evento = 'envio_email_montador');

COMMIT;
