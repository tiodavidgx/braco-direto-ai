-- Adicionar constraint unique para envio_montagem_id na tabela trello_cards
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'unique_envio_montagem_card'
    ) THEN
        ALTER TABLE trello_cards 
        ADD CONSTRAINT unique_envio_montagem_card UNIQUE (envio_montagem_id);
    END IF;
END $$;
