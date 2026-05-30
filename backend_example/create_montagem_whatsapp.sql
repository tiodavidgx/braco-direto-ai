-- ============================================================
-- WhatsApp Montagem 24h: tabelas auxiliares + templates/gatilhos
-- ============================================================

-- Idempotência dos alertas (evita reenvio)
CREATE TABLE IF NOT EXISTS montagem_alertas_enviados (
    pedido_id   TEXT NOT NULL,
    tipo        TEXT NOT NULL,          -- 'montagem_novo_ticket' | 'montagem_prazo_4h' | 'montagem_prazo_vencido' ...
    enviado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (pedido_id, tipo)
);

-- Snapshot do último status conhecido (para detectar transições standby->pendente/andamento)
CREATE TABLE IF NOT EXISTS montagem_ultimo_status (
    pedido_id       TEXT PRIMARY KEY,
    coluna          TEXT NOT NULL,      -- 'pendente' | 'em_andamento' | 'standby' | 'finalizado'
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Log de envios (para auditoria)
CREATE TABLE IF NOT EXISTS montagem_whatsapp_log (
    id          BIGSERIAL PRIMARY KEY,
    pedido_id   TEXT,
    user_id     INTEGER,
    tipo        TEXT NOT NULL,
    telefone    TEXT,
    mensagem    TEXT,
    sucesso     BOOLEAN NOT NULL DEFAULT FALSE,
    erro        TEXT,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_montagem_whatsapp_log_pedido ON montagem_whatsapp_log (pedido_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_montagem_whatsapp_log_tipo   ON montagem_whatsapp_log (tipo, criado_em DESC);

-- ============================================================
-- Templates (tipo = 'montagem')
-- ============================================================
INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES (
  'montagem_novo_ticket',
  'montagem',
  E'📋 *Novo pedido de montagem*\n\nPedido: *{{numero_pedido}}*\nCliente: {{cliente_nome}}\nFilial: {{filial_venda}}\nMontador: {{montador_nome}}\nEntrega: {{data_entrega_fmt}}\nPrazo limite: *{{prazo_limite_fmt}}*\n\nAcesse: https://suportedg.site/acompanhamento-montagem',
  ARRAY['numero_pedido','cliente_nome','filial_venda','montador_nome','data_entrega_fmt','prazo_limite_fmt']
)
ON CONFLICT (nome) DO UPDATE SET template = EXCLUDED.template, variaveis = EXCLUDED.variaveis, atualizado_em = NOW();

INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES (
  'montagem_comentario',
  'montagem',
  E'💬 *Novo comentário em pedido de montagem*\n\nPedido: *{{numero_pedido}}* - {{cliente_nome}}\nFilial: {{filial_venda}}\n\n*{{comentador_nome}}:*\n{{texto}}\n\nAcesse: https://suportedg.site/acompanhamento-montagem',
  ARRAY['numero_pedido','cliente_nome','filial_venda','comentador_nome','texto']
)
ON CONFLICT (nome) DO UPDATE SET template = EXCLUDED.template, variaveis = EXCLUDED.variaveis, atualizado_em = NOW();

INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES (
  'montagem_retomada',
  'montagem',
  E'▶️ *Montagem retomada de Stand-by*\n\nPedido: *{{numero_pedido}}* - {{cliente_nome}}\nFilial: {{filial_venda}}\nMontador: {{montador_nome}}\nPrazo limite: *{{prazo_limite_fmt}}*\n\nAcesse: https://suportedg.site/acompanhamento-montagem',
  ARRAY['numero_pedido','cliente_nome','filial_venda','montador_nome','prazo_limite_fmt']
)
ON CONFLICT (nome) DO UPDATE SET template = EXCLUDED.template, variaveis = EXCLUDED.variaveis, atualizado_em = NOW();

INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES (
  'montagem_prazo_4h',
  'montagem',
  E'⚠️ *Prazo próximo (menos de 4h)*\n\nPedido: *{{numero_pedido}}* - {{cliente_nome}}\nFilial: {{filial_venda}}\nMontador: {{montador_nome}}\nPrazo limite: *{{prazo_limite_fmt}}*\nFaltam: *{{horas_restantes}}h*\n\nAcesse: https://suportedg.site/acompanhamento-montagem',
  ARRAY['numero_pedido','cliente_nome','filial_venda','montador_nome','prazo_limite_fmt','horas_restantes']
)
ON CONFLICT (nome) DO UPDATE SET template = EXCLUDED.template, variaveis = EXCLUDED.variaveis, atualizado_em = NOW();

INSERT INTO templates_whatsapp (nome, tipo, template, variaveis)
VALUES (
  'montagem_prazo_vencido',
  'montagem',
  E'🚨 *Prazo VENCIDO*\n\nPedido: *{{numero_pedido}}* - {{cliente_nome}}\nFilial: {{filial_venda}}\nMontador: {{montador_nome}}\nVenceu em: *{{prazo_limite_fmt}}*\n\nAcesse: https://suportedg.site/acompanhamento-montagem',
  ARRAY['numero_pedido','cliente_nome','filial_venda','montador_nome','prazo_limite_fmt']
)
ON CONFLICT (nome) DO UPDATE SET template = EXCLUDED.template, variaveis = EXCLUDED.variaveis, atualizado_em = NOW();

-- ============================================================
-- Automações (evento -> template)
-- ============================================================
INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'montagem_novo_ticket', id, TRUE, NULL FROM templates_whatsapp WHERE nome='montagem_novo_ticket'
ON CONFLICT (evento) DO UPDATE SET template_id = EXCLUDED.template_id, atualizado_em = NOW();

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'montagem_comentario', id, TRUE, NULL FROM templates_whatsapp WHERE nome='montagem_comentario'
ON CONFLICT (evento) DO UPDATE SET template_id = EXCLUDED.template_id, atualizado_em = NOW();

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'montagem_retomada', id, TRUE, NULL FROM templates_whatsapp WHERE nome='montagem_retomada'
ON CONFLICT (evento) DO UPDATE SET template_id = EXCLUDED.template_id, atualizado_em = NOW();

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'montagem_prazo_4h', id, TRUE, NULL FROM templates_whatsapp WHERE nome='montagem_prazo_4h'
ON CONFLICT (evento) DO UPDATE SET template_id = EXCLUDED.template_id, atualizado_em = NOW();

INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
SELECT 'montagem_prazo_vencido', id, TRUE, NULL FROM templates_whatsapp WHERE nome='montagem_prazo_vencido'
ON CONFLICT (evento) DO UPDATE SET template_id = EXCLUDED.template_id, atualizado_em = NOW();

-- ============================================================
-- Job configurável
-- ============================================================
INSERT INTO jobs_config (nome, descricao, ativo, intervalo_minutos)
VALUES (
  'alertas_montagem_whatsapp',
  'Alertas WhatsApp Montagem 24h: novos pedidos, transição de stand-by, prazo 4h, prazo vencido',
  TRUE,
  10
)
ON CONFLICT (nome) DO UPDATE SET descricao = EXCLUDED.descricao;
