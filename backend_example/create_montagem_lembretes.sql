-- Lembretes agendados do kanban Montagem 24h.
-- Ao disparar: envia WhatsApp ao usuário e adiciona um comentário no ticket.
CREATE TABLE IF NOT EXISTS montagem_lembretes (
    id               BIGSERIAL PRIMARY KEY,
    pedido_id        TEXT        NOT NULL,
    usuario_id       INTEGER     NOT NULL,
    usuario_telefone TEXT,
    agendar_para     TIMESTAMPTZ NOT NULL,
    enviado          BOOLEAN     NOT NULL DEFAULT FALSE,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_montagem_lembretes_pendentes
    ON montagem_lembretes (agendar_para)
    WHERE enviado = FALSE;

CREATE INDEX IF NOT EXISTS idx_montagem_lembretes_ticket
    ON montagem_lembretes (pedido_id, usuario_id);

GRANT ALL ON montagem_lembretes TO braco;
GRANT USAGE, SELECT ON SEQUENCE montagem_lembretes_id_seq TO braco;

-- Template e automação para a mensagem do lembrete
INSERT INTO templates_whatsapp (nome, template, ativo)
VALUES (
    'montagem_lembrete',
    '🔔 *Lembrete – Montagem 24h*' || chr(10) || chr(10) ||
    '🧾 Pedido: *{{numero_pedido}}*' || chr(10) ||
    '👤 Cliente: {{cliente_nome}}' || chr(10) ||
    '🏬 Filial: {{filial_venda}}' || chr(10) ||
    '🛠️ Montador: {{montador_nome}}' || chr(10) ||
    '⏰ Prazo: {{prazo_limite_fmt}}' || chr(10) || chr(10) ||
    'Você pediu para ser lembrado deste pedido.',
    TRUE
)
ON CONFLICT (nome) DO NOTHING;

INSERT INTO automacao_whatsapp (evento, template_id, ativo)
SELECT 'montagem_lembrete', t.id::text, TRUE
FROM templates_whatsapp t
WHERE t.nome = 'montagem_lembrete'
ON CONFLICT (evento) DO UPDATE
   SET template_id = EXCLUDED.template_id,
       ativo       = TRUE;
