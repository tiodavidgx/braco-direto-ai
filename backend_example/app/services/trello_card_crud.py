"""
CRUD para gerenciar cards do Trello no banco de dados
Garante que não haja duplicação de cards
"""

from app.database import get_db_connection
from typing import Optional, Dict
import psycopg2.extras


class TrelloCardCRUD:
    """Gerencia operações CRUD para cards do Trello"""
    
    @staticmethod
    def card_existe_para_lote(lote_id: int) -> bool:
        """
        Verifica se já existe card para um lote específico
        
        Args:
            lote_id: ID do lote (prestador)
            
        Returns:
            True se já existe card, False caso contrário
        """
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM trello_cards 
                WHERE lote_id = %s AND tipo = 'prestador'
            """, (lote_id,))
            count = cur.fetchone()[0]
            return count > 0
    
    @staticmethod
    def card_existe_para_montador(envio_montagem_id: int) -> bool:
        """
        Verifica se já existe card para um envio de montador específico
        
        Args:
            envio_montagem_id: ID do envio de montagem
            
        Returns:
            True se já existe card, False caso contrário
        """
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM trello_cards 
                WHERE envio_montagem_id = %s AND tipo = 'montador'
            """, (envio_montagem_id,))
            count = cur.fetchone()[0]
            return count > 0
    
    @staticmethod
    def obter_card_lote(lote_id: int) -> Optional[Dict]:
        """
        Obtém informações do card de um lote
        
        Args:
            lote_id: ID do lote
            
        Returns:
            Dict com informações do card ou None se não existir
        """
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT * FROM trello_cards 
                WHERE lote_id = %s AND tipo = 'prestador'
                ORDER BY data_criacao DESC
                LIMIT 1
            """, (lote_id,))
            return cur.fetchone()
    
    @staticmethod
    def obter_card_montador(envio_montagem_id: int) -> Optional[Dict]:
        """
        Obtém informações do card de um envio de montador
        
        Args:
            envio_montagem_id: ID do envio de montagem
            
        Returns:
            Dict com informações do card ou None se não existir
        """
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT * FROM trello_cards 
                WHERE envio_montagem_id = %s AND tipo = 'montador'
                ORDER BY data_criacao DESC
                LIMIT 1
            """, (envio_montagem_id,))
            return cur.fetchone()
    
    @staticmethod
    def criar_card_lote(lote_id: int, card_id: str, card_url: str) -> bool:
        """
        Cria um registro de card para um lote (com verificação de duplicação)
        
        Args:
            lote_id: ID do lote
            card_id: ID do card no Trello
            card_url: URL do card no Trello
            
        Returns:
            True se criado com sucesso, False se já existe ou erro
        """
        with get_db_connection() as conn:
            try:
                cur = conn.cursor()
                
                # Verificação atômica: tentar inserir apenas se não existe
                cur.execute("""
                    INSERT INTO trello_cards 
                    (lote_id, card_id, card_url, tipo, data_criacao)
                    SELECT %s, %s, %s, 'prestador', NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM trello_cards 
                        WHERE lote_id = %s AND tipo = 'prestador'
                    )
                    RETURNING id
                """, (lote_id, card_id, card_url, lote_id))
                
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    print(f"✅ Card registrado no banco para lote #{lote_id}")
                    return True
                else:
                    print(f"⚠️  Card já existe para lote #{lote_id} - pulando criação")
                    return False
                    
            except Exception as e:
                print(f"❌ Erro ao criar card no banco: {e}")
                conn.rollback()
                return False
    
    @staticmethod
    def criar_card_montador(envio_montagem_id: int, card_id: str, card_url: str) -> bool:
        """
        Cria um registro de card para um envio de montador (com verificação de duplicação)
        
        Args:
            envio_montagem_id: ID do envio de montagem
            card_id: ID do card no Trello
            card_url: URL do card no Trello
            
        Returns:
            True se criado com sucesso, False se já existe ou erro
        """
        with get_db_connection() as conn:
            try:
                cur = conn.cursor()
                
                # Verificação atômica: tentar inserir apenas se não existe
                cur.execute("""
                    INSERT INTO trello_cards 
                    (envio_montagem_id, card_id, card_url, tipo, data_criacao)
                    SELECT %s, %s, %s, 'montador', NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM trello_cards 
                        WHERE envio_montagem_id = %s AND tipo = 'montador'
                    )
                    RETURNING id
                """, (envio_montagem_id, card_id, card_url, envio_montagem_id))
                
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    print(f"✅ Card registrado no banco para montador #{envio_montagem_id}")
                    return True
                else:
                    print(f"⚠️  Card já existe para montador #{envio_montagem_id} - pulando criação")
                    return False
                    
            except Exception as e:
                print(f"❌ Erro ao criar card no banco: {e}")
                conn.rollback()
                return False
    
    @staticmethod
    def deletar_card_lote(lote_id: int) -> bool:
        """
        Remove registro de card de um lote
        
        Args:
            lote_id: ID do lote
            
        Returns:
            True se removido com sucesso
        """
        with get_db_connection() as conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    DELETE FROM trello_cards 
                    WHERE lote_id = %s AND tipo = 'prestador'
                """, (lote_id,))
                conn.commit()
                return True
            except Exception as e:
                print(f"❌ Erro ao deletar card: {e}")
                conn.rollback()
                return False
    
    @staticmethod
    def deletar_card_montador(envio_montagem_id: int) -> bool:
        """
        Remove registro de card de um envio de montador
        
        Args:
            envio_montagem_id: ID do envio de montagem
            
        Returns:
            True se removido com sucesso
        """
        with get_db_connection() as conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    DELETE FROM trello_cards 
                    WHERE envio_montagem_id = %s AND tipo = 'montador'
                """, (envio_montagem_id,))
                conn.commit()
                return True
            except Exception as e:
                print(f"❌ Erro ao deletar card: {e}")
                conn.rollback()
                return False
