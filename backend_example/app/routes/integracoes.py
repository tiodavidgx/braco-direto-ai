from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2
from ..database import get_db_connection

router = APIRouter()


class TrelloConfig(BaseModel):
    trello_api_key: Optional[str] = None
    trello_token: Optional[str] = None
    trello_board_id: Optional[str] = None
    trello_list_id: Optional[str] = None
    trello_ativo: bool = False


@router.get("/trello/config")
def get_trello_config():
    """Retorna a configuração atual do Trello"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT trello_api_key, trello_token, trello_board_id, trello_list_id, trello_ativo
            FROM integracoes_config
            WHERE id = 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            return {
                "trello_api_key": result[0] or "",
                "trello_token": result[1] or "",
                "trello_board_id": result[2] or "",
                "trello_list_id": result[3] or "",
                "trello_ativo": result[4] or False
            }
        else:
            return {
                "trello_api_key": "",
                "trello_token": "",
                "trello_board_id": "",
                "trello_list_id": "",
                "trello_ativo": False
            }
    finally:
        cursor.close()
        conn.close()


@router.post("/trello/config")
def save_trello_config(config: TrelloConfig):
    """Salva a configuração do Trello"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE integracoes_config
            SET 
                trello_api_key = %s,
                trello_token = %s,
                trello_board_id = %s,
                trello_list_id = %s,
                trello_ativo = %s,
                data_atualizacao = NOW()
            WHERE id = 1
        """, (
            config.trello_api_key,
            config.trello_token,
            config.trello_board_id,
            config.trello_list_id,
            config.trello_ativo
        ))
        
        conn.commit()
        return {"message": "Configuração salva com sucesso"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/trello/test")
def test_trello_connection():
    """Testa a conexão com o Trello"""
    # Aqui você implementaria a lógica real de teste
    # Por enquanto, apenas retorna sucesso
    return {"success": True, "message": "Conexão OK"}


@router.get("/trello/boards")
def list_boards():
    """Lista os boards do Trello"""
    # Implementar integração real com API do Trello
    return []


@router.get("/trello/boards/{board_id}/lists")
def list_lists(board_id: str):
    """Lista as listas de um board"""
    # Implementar integração real com API do Trello
    return []
