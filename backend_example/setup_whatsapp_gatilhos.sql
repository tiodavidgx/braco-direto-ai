-- Script para criar templates e automações padrão de WhatsApp
-- Execute: psql -d email -f setup_whatsapp_gatilhos.sql

-- =====================================================
-- TEMPLATES DE WHATSAPP
-- =====================================================

-- Template: Relatório Enviado - Prestador
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis, ativo)
VALUES (
    'Relatório Enviado - Prestador',
    'envio_relatorio',
    'Olá {{nome_prestador}}, 

📄 Seu relatório de fechamento do período *{{periodo}}* foi enviado para o seu e-mail.

💰 *Valor Total:* R$ {{valor}}

📎 *Link para envio da NF:* {{link}}

Qualquer dúvida, estamos à disposição!',
    'nome_prestador, periodo, valor, link',
    TRUE
) ON CONFLICT DO NOTHING;

-- Template: Relatório Enviado - Montador
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis, ativo)
VALUES (
    'Relatório Enviado - Montador',
    'envio_relatorio',
    'Olá {{nome_montador}}, 

📄 Seu relatório de pagamento de montagem do período *{{periodo}}* foi enviado para o seu e-mail.

💰 *Valor Total:* R$ {{valor}}

📎 *Link para envio da NF:* {{link}}

Qualquer dúvida, estamos à disposição!',
    'nome_montador, periodo, valor, link',
    TRUE
) ON CONFLICT DO NOTHING;

-- Template: NF Recebida - Prestador
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis, ativo)
VALUES (
    'NF Recebida - Prestador',
    'nf_recebida',
    'Olá {{nome_prestador}}, 

✅ Recebemos sua Nota Fiscal!

📄 *Arquivo:* {{numero_nf}}
📅 *Data:* {{data_recebimento}}
💰 *Valor:* R$ {{valor}}

Obrigado! O pagamento será processado conforme o prazo acordado.',
    'nome_prestador, numero_nf, data_recebimento, valor, periodo',
    TRUE
) ON CONFLICT DO NOTHING;

-- Template: NF Recebida - Montador
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis, ativo)
VALUES (
    'NF Recebida - Montador',
    'nf_recebida',
    'Olá {{nome_montador}}, 

✅ Recebemos sua Nota Fiscal!

📄 *Arquivo:* {{numero_nf}}
📅 *Data:* {{data_recebimento}}
💰 *Valor:* R$ {{valor}}

Obrigado! O pagamento será processado conforme o prazo acordado.',
    'nome_montador, numero_nf, data_recebimento, valor, periodo',
    TRUE
) ON CONFLICT DO NOTHING;

-- Template: Integração Trello - Prestador
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis, ativo)
VALUES (
    'Integração Trello - Prestador',
    'trello_integracao',
    'Olá {{nome_prestador}}, 

🔗 Seu pagamento foi integrado ao sistema de gestão!

📦 *Lote:* #{{lote_id}}
💰 *Valor:* {{valor}}
📅 *Data:* {{data_integracao}}

✅ Acompanhe o status pelo link: {{card_url}}',
    'nome_prestador, lote_id, valor, data_integracao, card_url',
    TRUE
) ON CONFLICT DO NOTHING;

-- Template: Integração Trello - Montador
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis, ativo)
VALUES (
    'Integração Trello - Montador',
    'trello_integracao',
    'Olá {{nome_montador}}, 

🔗 Seu pagamento foi integrado ao sistema de gestão!

🔧 *Envio:* #{{envio_id}}
💰 *Valor:* {{valor}}
📅 *Data:* {{data_integracao}}

✅ Acompanhe o status pelo link: {{card_url}}',
    'nome_montador, envio_id, valor, data_integracao, card_url',
    TRUE
) ON CONFLICT DO NOTHING;

-- =====================================================
-- AUTOMAÇÕES DE WHATSAPP
-- =====================================================

-- Automação: Envio de Email Prestador
INSERT INTO automacao_whatsapp (evento, template_id, condicoes, ativo)
SELECT 'envio_email_prestador', id::text, NULL, TRUE
FROM templates_whatsapp 
WHERE nome = 'Relatório Enviado - Prestador'
ON CONFLICT DO NOTHING;

-- Automação: Envio de Email Montador
INSERT INTO automacao_whatsapp (evento, template_id, condicoes, ativo)
SELECT 'envio_email_montador', id::text, NULL, TRUE
FROM templates_whatsapp 
WHERE nome = 'Relatório Enviado - Montador'
ON CONFLICT DO NOTHING;

-- Automação: NF Recebida Prestador
INSERT INTO automacao_whatsapp (evento, template_id, condicoes, ativo)
SELECT 'nf_recebida_prestador', id::text, NULL, TRUE
FROM templates_whatsapp 
WHERE nome = 'NF Recebida - Prestador'
ON CONFLICT DO NOTHING;

-- Automação: NF Recebida Montador
INSERT INTO automacao_whatsapp (evento, template_id, condicoes, ativo)
SELECT 'nf_recebida_montador', id::text, NULL, TRUE
FROM templates_whatsapp 
WHERE nome = 'NF Recebida - Montador'
ON CONFLICT DO NOTHING;

-- Automação: Card Trello Criado Prestador
INSERT INTO automacao_whatsapp (evento, template_id, condicoes, ativo)
SELECT 'trello_card_criado_prestador', id::text, NULL, TRUE
FROM templates_whatsapp 
WHERE nome = 'Integração Trello - Prestador'
ON CONFLICT DO NOTHING;

-- Automação: Card Trello Criado Montador
INSERT INTO automacao_whatsapp (evento, template_id, condicoes, ativo)
SELECT 'trello_card_criado_montador', id::text, NULL, TRUE
FROM templates_whatsapp 
WHERE nome = 'Integração Trello - Montador'
ON CONFLICT DO NOTHING;

-- =====================================================
-- VERIFICAÇÃO
-- =====================================================

-- Listar templates criados
SELECT id, nome, tipo, ativo FROM templates_whatsapp ORDER BY id;

-- Listar automações criadas
SELECT a.id, a.evento, t.nome as template_nome, a.ativo 
FROM automacao_whatsapp a 
JOIN templates_whatsapp t ON a.template_id = t.id::text 
ORDER BY a.id;

-- =====================================================
-- RESUMO DOS GATILHOS
-- =====================================================
-- 
-- 1. envio_email_prestador    -> Quando relatório é enviado para prestador
-- 2. envio_email_montador     -> Quando relatório é enviado para montador
-- 3. nf_recebida_prestador    -> Quando NF do prestador é recebida
-- 4. nf_recebida_montador     -> Quando NF do montador é recebida
-- 5. trello_card_criado_prestador -> Quando card Trello é criado para prestador
-- 6. trello_card_criado_montador  -> Quando card Trello é criado para montador
--
-- =====================================================
