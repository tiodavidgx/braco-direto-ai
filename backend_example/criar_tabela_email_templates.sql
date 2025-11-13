-- Tabela para armazenar as últimas configurações de email usadas
CREATE TABLE IF NOT EXISTS email_config (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL, -- 'prestador' ou 'montador'
    assunto TEXT NOT NULL,
    corpo TEXT NOT NULL,
    cc TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE(tipo) -- Apenas uma config por tipo
);

-- Inserir configurações padrão iniciais
INSERT INTO email_config (tipo, assunto, corpo, cc) 
VALUES 
(
    'prestador',
    'Novo Mundo Resolve | Nota Fiscal | Período: {{periodo}} | Prestador: {{nome_prestador}}',
    'Segue a relação de boletins para emissão da nota fiscal de serviços entre **{{periodo}}**.

📎 Para anexar a Nota Fiscal, acesse o link abaixo:
{{link_upload}}

⚠️ Este link é válido por 30 dias.

Obrigado.',
    'projetos.qualidade@novomundo.com.br'
),
(
    'montador',
    'Relatório de Pagamento de Montagem - Período: {{periodo_relatorio}}',
    'Olá, {{nome_montador}},

Segue em anexo o seu relatório de pagamento de montagens referente ao período de **{{periodo_relatorio}}**.

📎 **Link para upload de documentos:** {{link_upload}}

Qualquer dúvida, estamos à disposição.',
    'projetos.qualidade@novomundo.com.br'
)
ON CONFLICT (tipo) DO NOTHING;
