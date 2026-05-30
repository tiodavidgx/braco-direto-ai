-- Add parent-child ticket relationship
-- Run: psql -U braco -d braco_db -h 127.0.0.1 -f add_ticket_parent_id.sql

ALTER TABLE crm_tickets ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES crm_tickets(id);
CREATE INDEX IF NOT EXISTS idx_crm_tickets_parent ON crm_tickets(parent_id);
