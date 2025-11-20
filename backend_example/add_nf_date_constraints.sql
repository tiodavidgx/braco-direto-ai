-- Adiciona check constraint para garantir que se tem nota_fiscal_path,
-- também tem data_recebimento_nf e data_vencimento_pagamento

-- Para lotes_servico
ALTER TABLE lotes_servico 
DROP CONSTRAINT IF EXISTS check_nf_com_datas;

ALTER TABLE lotes_servico 
ADD CONSTRAINT check_nf_com_datas 
CHECK (
    (nota_fiscal_path IS NULL) OR 
    (nota_fiscal_path IS NOT NULL AND data_recebimento_nf IS NOT NULL AND data_vencimento_pagamento IS NOT NULL)
);

-- Para envios_montagem
ALTER TABLE envios_montagem 
DROP CONSTRAINT IF EXISTS check_nf_com_datas;

ALTER TABLE envios_montagem 
ADD CONSTRAINT check_nf_com_datas 
CHECK (
    (nota_fiscal_path IS NULL) OR 
    (nota_fiscal_path IS NOT NULL AND data_recebimento_nf IS NOT NULL AND data_vencimento_pagamento IS NOT NULL)
);

-- Comentários explicativos
COMMENT ON CONSTRAINT check_nf_com_datas ON lotes_servico IS 
'Garante que se houver nota_fiscal_path, também terá data_recebimento_nf e data_vencimento_pagamento';

COMMENT ON CONSTRAINT check_nf_com_datas ON envios_montagem IS 
'Garante que se houver nota_fiscal_path, também terá data_recebimento_nf e data_vencimento_pagamento';
