-- Adicionar templates de notificação de pagamento realizado

-- Template para prestador (com botões)
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES 
    ('prestador_pagamento_realizado', 'prestador', 
     E'Olá {{nome_prestador}}! 💰✅\n\n🎉 Seu pagamento foi realizado!\n\n📅 Período: {{periodo}}\n💵 Valor: R$ {{valor}}\n📆 Data do pagamento: {{data_pagamento}}\n\nO valor já deve estar disponível em sua conta. Qualquer dúvida, estamos à disposição!\n\n[BUTTONS]\n[✅ Recebi o pagamento|recebi_pagamento]\n[❌ Não recebi|nao_recebi_pagamento]\n[/BUTTONS]',
     ARRAY['nome_prestador', 'periodo', 'valor', 'data_pagamento'])
ON CONFLICT (nome) DO UPDATE 
SET 
    template = EXCLUDED.template,
    variaveis = EXCLUDED.variaveis,
    atualizado_em = CURRENT_TIMESTAMP;

-- Template para montador (com botões)
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES 
    ('montador_pagamento_realizado', 'montador', 
     E'Olá {{nome_montador}}! 💰✅\n\n🎉 Seu pagamento foi realizado!\n\n📅 Período: {{periodo}}\n💵 Valor: R$ {{valor}}\n📆 Data do pagamento: {{data_pagamento}}\n\nO valor já deve estar disponível em sua conta. Qualquer dúvida, estamos à disposição!\n\n[BUTTONS]\n[✅ Recebi o pagamento|recebi_pagamento]\n[❌ Não recebi|nao_recebi_pagamento]\n[/BUTTONS]',
     ARRAY['nome_montador', 'periodo', 'valor', 'data_pagamento'])
ON CONFLICT (nome) DO UPDATE 
SET 
    template = EXCLUDED.template,
    variaveis = EXCLUDED.variaveis,
    atualizado_em = CURRENT_TIMESTAMP;

-- Gatilho para prestador
INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 
    'pagamento_realizado_prestador',
    (SELECT id FROM templates_whatsapp WHERE nome = 'prestador_pagamento_realizado'),
    TRUE,  -- Já ativa por padrão
    NULL
WHERE NOT EXISTS (SELECT 1 FROM automacao_whatsapp WHERE evento = 'pagamento_realizado_prestador');

-- Gatilho para montador
INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 
    'pagamento_realizado_montador',
    (SELECT id FROM templates_whatsapp WHERE nome = 'montador_pagamento_realizado'),
    TRUE,  -- Já ativa por padrão
    NULL
WHERE NOT EXISTS (SELECT 1 FROM automacao_whatsapp WHERE evento = 'pagamento_realizado_montador');

-- Verificar se foi criado
SELECT 
    a.evento,
    t.nome as template_nome,
    a.ativo,
    t.template
FROM automacao_whatsapp a
JOIN templates_whatsapp t ON a.template_id = t.id::text
WHERE a.evento IN ('pagamento_realizado_prestador', 'pagamento_realizado_montador');
