-- Permite que lote_id seja NULL (necessário para montadores que usam envio_montagem_id)
ALTER TABLE trello_cards 
ALTER COLUMN lote_id DROP NOT NULL;
