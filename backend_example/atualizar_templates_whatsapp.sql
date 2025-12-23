-- Atualização de templates WhatsApp para incluir mais informações
-- Execute com: psql -U usuario -d database -f atualizar_templates_whatsapp.sql

-- Template de NF recebida do montador - adiciona ID do envio e período
UPDATE templates_whatsapp 
SET 
    template = E'✅ {{nome_montador}}, recebemos sua Nota Fiscal!\n\n📦 Envio #{{envio_id}}\n📅 Período: {{periodo}}\n📄 Arquivo: {{numero_nf}}\n💰 Valor: R$ {{valor}}\n📆 Data: {{data_recebimento}}\n\nObrigado! O pagamento será processado em breve.',
    variaveis = ARRAY['nome_montador', 'envio_id', 'periodo', 'numero_nf', 'valor', 'data_recebimento']
WHERE nome = 'nf_recebida_montador';

-- Template de NF recebida do prestador - adiciona ID do lote e período
UPDATE templates_whatsapp 
SET 
    template = E'✅ {{nome_prestador}}, recebemos sua Nota Fiscal!\n\n📦 Lote #{{lote_id}}\n📅 Período: {{periodo}}\n📄 Arquivo: {{numero_nf}}\n💰 Valor: R$ {{valor}}\n📆 Data: {{data_recebimento}}\n\nObrigado! O pagamento será processado em breve.',
    variaveis = ARRAY['nome_prestador', 'lote_id', 'periodo', 'numero_nf', 'valor', 'data_recebimento']
WHERE nome = 'nf_recebida_prestador';

-- Adiciona novos templates para Trello se não existirem
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES 
    ('trello_card_criado_prestador', 'prestador',
     E'🔗 {{nome_prestador}}, seu lote foi integrado no Trello!\n\n📦 Lote #{{lote_id}}\n💰 Valor: R$ {{valor}}\n📅 Data: {{data_integracao}}\n🔗 Link: {{card_url}}\n\nAcompanhe o status pelo link acima!',
     ARRAY['nome_prestador', 'lote_id', 'valor', 'data_integracao', 'card_url']),
    
    ('trello_card_criado_montador', 'montador',
     E'🔗 {{nome_montador}}, seu envio foi integrado no Trello!\n\n📦 Envio #{{envio_id}}\n💰 Valor: R$ {{valor}}\n📅 Data: {{data_integracao}}\n🔗 Link: {{card_url}}\n\nAcompanhe o status pelo link acima!',
     ARRAY['nome_montador', 'envio_id', 'valor', 'data_integracao', 'card_url'])
ON CONFLICT (nome) DO NOTHING;

-- Adiciona automação para Trello se não existir
INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'trello_card_criado_prestador', id, FALSE, NULL
FROM templates_whatsapp WHERE nome = 'trello_card_criado_prestador'
ON CONFLICT (evento) DO NOTHING;

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'trello_card_criado_montador', id, FALSE, NULL
FROM templates_whatsapp WHERE nome = 'trello_card_criado_montador'
ON CONFLICT (evento) DO NOTHING;

-- Verificar resultado
SELECT nome, template, variaveis FROM templates_whatsapp 
WHERE nome IN ('nf_recebida_prestador', 'nf_recebida_montador', 'trello_card_criado_prestador', 'trello_card_criado_montador');
