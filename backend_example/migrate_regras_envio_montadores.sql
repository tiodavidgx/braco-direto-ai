-- ============================================================
-- Migração das regras de envio antigas para o novo modelo
-- regra_envio/dia_envio_1/dia_envio_2 → envio_automatico/dias_envio_mes
-- ============================================================

-- Ativar envio automático para montadores que já tinham regra configurada
UPDATE montadores 
SET envio_automatico = TRUE 
WHERE regra_envio IS NOT NULL 
  AND regra_envio != 'Nenhuma' 
  AND regra_envio != '';

-- Migrar dia_envio_1 e dia_envio_2 para array dias_envio_mes
-- Cria array com os dias não-nulos
UPDATE montadores 
SET dias_envio_mes = ARRAY(
    SELECT DISTINCT unnest(ARRAY[
        CASE WHEN dia_envio_1 IS NOT NULL THEN dia_envio_1 END,
        CASE WHEN dia_envio_2 IS NOT NULL THEN dia_envio_2 END
    ]) AS d
    WHERE d IS NOT NULL
)
WHERE (dia_envio_1 IS NOT NULL OR dia_envio_2 IS NOT NULL)
  AND envio_automatico = TRUE;

-- Migrar tempo_vencimento_dias → prazo_pagamento_dias
UPDATE montadores 
SET prazo_pagamento_dias = tempo_vencimento_dias 
WHERE tempo_vencimento_dias IS NOT NULL 
  AND tempo_vencimento_dias != 10;

-- Definir dia_fechamento como o menor dia de envio - 3 (heurística)
UPDATE montadores 
SET dia_fechamento = GREATEST(1, (
    SELECT MIN(d) - 3 FROM unnest(dias_envio_mes) AS d
))
WHERE array_length(dias_envio_mes, 1) > 0
  AND envio_automatico = TRUE;
