-- Add produto columns to crm_tickets
-- Run: psql -U braco -d braco_db -h 127.0.0.1 -f add_produto_columns.sql

ALTER TABLE crm_tickets ADD COLUMN IF NOT EXISTS produto VARCHAR(100) DEFAULT '';
ALTER TABLE crm_tickets ADD COLUMN IF NOT EXISTS nome_produto VARCHAR(255) DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_crm_tickets_pedido_produto ON crm_tickets(id_pedido, produto);
