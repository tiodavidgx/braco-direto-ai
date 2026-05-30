"""
Rotas de Integrações (Trello, WhatsApp, etc)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database import get_db_connection
from app.services.trello_service import TrelloIntegration

router = APIRouter()


class TrelloConfigModel(BaseModel):
    trello_api_key: Optional[str] = None
    trello_token: Optional[str] = None
    trello_board_id: Optional[str] = None
    trello_list_id: Optional[str] = None
    trello_ativo: bool = False


@router.get("/trello/config")
async def get_trello_config():
    """Retorna a configuração atual do Trello do banco de dados"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    trello_api_key, 
                    trello_token, 
                    trello_board_id, 
                    trello_list_id,
                    trello_ativo
                FROM integracoes_config 
                WHERE id = 1
            """)
            
            result = cur.fetchone()
            
            if result:
                return {
                    "trello_api_key": result[0] or "",
                    "trello_token": result[1] or "",
                    "trello_board_id": result[2] or "",
                    "trello_list_id": result[3] or "",
                    "trello_ativo": result[4] or False
                }
            else:
                # Se não existir, criar registro padrão
                cur.execute("""
                    INSERT INTO integracoes_config 
                    (id, trello_api_key, trello_token, trello_board_id, trello_list_id, trello_ativo)
                    VALUES (1, '', '', '', '', false)
                    RETURNING trello_api_key, trello_token, trello_board_id, trello_list_id, trello_ativo
                """)
                conn.commit()
                result = cur.fetchone()
                
                return {
                    "trello_api_key": "",
                    "trello_token": "",
                    "trello_board_id": "",
                    "trello_list_id": "",
                    "trello_ativo": False
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar configuração: {str(e)}")


@router.post("/trello/config")
async def save_trello_config(config: TrelloConfigModel):
    """Salva a configuração do Trello no banco de dados"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Atualizar ou inserir configuração
            cur.execute("""
                INSERT INTO integracoes_config 
                (id, trello_api_key, trello_token, trello_board_id, trello_list_id, trello_ativo)
                VALUES (1, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET 
                    trello_api_key = EXCLUDED.trello_api_key,
                    trello_token = EXCLUDED.trello_token,
                    trello_board_id = EXCLUDED.trello_board_id,
                    trello_list_id = EXCLUDED.trello_list_id,
                    trello_ativo = EXCLUDED.trello_ativo
            """, (
                config.trello_api_key or '',
                config.trello_token or '',
                config.trello_board_id or '',
                config.trello_list_id or '',
                config.trello_ativo
            ))
            
            conn.commit()
            
        return {"success": True, "message": "Configuração salva com sucesso"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configuração: {str(e)}")


@router.post("/trello/test")
async def test_trello_connection():
    """Testa a conexão com o Trello listando boards"""
    try:
        trello = TrelloIntegration()
        
        if not trello.api_key or not trello.token:
            raise HTTPException(
                status_code=400, 
                detail="API Key e Token não configurados. Configure primeiro em Configurações."
            )
        
        # Tentar listar boards para testar credenciais
        boards = trello.listar_boards()
        
        return {
            "success": True, 
            "message": f"Conexão OK! {len(boards)} board(s) encontrado(s)",
            "boards_count": len(boards)
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao testar conexão: {str(e)}")


@router.get("/trello/boards")
async def list_trello_boards():
    """Lista os boards do Trello do usuário"""
    try:
        trello = TrelloIntegration()
        
        if not trello.api_key or not trello.token:
            return []
        
        boards = trello.listar_boards()
        
        # Retornar apenas id e nome
        return [
            {"id": board["id"], "name": board["name"]}
            for board in boards
        ]
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar boards: {str(e)}")


@router.get("/trello/listas/{board_id}")
async def list_trello_lists(board_id: str):
    """Lista as listas de um board específico do Trello"""
    try:
        trello = TrelloIntegration()
        
        if not trello.api_key or not trello.token:
            return []
        
        listas = trello.listar_listas(board_id)
        
        # Retornar apenas id e nome
        return [
            {"id": lista["id"], "name": lista["name"]}
            for lista in listas
        ]
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar listas: {str(e)}")


@router.get("/trello/boards/{board_id}/lists")
def list_lists(board_id: str):
    """Lista as listas de um board"""
    # Implementar integração real com API do Trello
    return []


# ==================== RECAPTCHA CONFIGURATION ====================

class RecaptchaConfigModel(BaseModel):
    recaptcha_enabled: bool = False
    recaptcha_site_key: Optional[str] = None
    recaptcha_secret_key: Optional[str] = None
    recaptcha_score_minimo: float = 0.5


def _ensure_recaptcha_columns():
    """Verifica se colunas de reCAPTCHA existem na tabela integracoes_config"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            columns = [
                ("recaptcha_enabled", "BOOLEAN DEFAULT FALSE"),
                ("recaptcha_site_key", "TEXT DEFAULT ''"),
                ("recaptcha_secret_key", "TEXT DEFAULT ''"),
                ("recaptcha_score_minimo", "NUMERIC(3,2) DEFAULT 0.50"),
            ]
            for col_name, col_def in columns:
                cur.execute("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'integracoes_config' AND column_name = %s
                """, (col_name,))
                if not cur.fetchone():
                    try:
                        cur.execute(f"ALTER TABLE integracoes_config ADD COLUMN {col_name} {col_def}")
                        conn.commit()
                    except Exception:
                        conn.rollback()
    except Exception as e:
        print(f"Aviso: erro ao verificar colunas recaptcha: {e}")

_ensure_recaptcha_columns()


@router.get("/recaptcha/config")
async def get_recaptcha_config():
    """Retorna a configuração do reCAPTCHA"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT recaptcha_enabled, recaptcha_site_key, recaptcha_secret_key, recaptcha_score_minimo
                FROM integracoes_config WHERE id = 1
            """)
            result = cur.fetchone()
            if result:
                return {
                    "recaptcha_enabled": result[0] or False,
                    "recaptcha_site_key": result[1] or "",
                    "recaptcha_secret_key": result[2] or "",
                    "recaptcha_score_minimo": float(result[3]) if result[3] else 0.5,
                }
            return {
                "recaptcha_enabled": False,
                "recaptcha_site_key": "",
                "recaptcha_secret_key": "",
                "recaptcha_score_minimo": 0.5,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar config reCAPTCHA: {str(e)}")


@router.post("/recaptcha/config")
async def save_recaptcha_config(config: RecaptchaConfigModel):
    """Salva a configuração do reCAPTCHA"""
    if config.recaptcha_score_minimo < 0.0 or config.recaptcha_score_minimo > 1.0:
        raise HTTPException(status_code=400, detail="Score deve estar entre 0.0 e 1.0")
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE integracoes_config
                SET recaptcha_enabled = %s,
                    recaptcha_site_key = %s,
                    recaptcha_secret_key = %s,
                    recaptcha_score_minimo = %s
                WHERE id = 1
            """, (
                config.recaptcha_enabled,
                config.recaptcha_site_key or '',
                config.recaptcha_secret_key or '',
                config.recaptcha_score_minimo,
            ))
            conn.commit()
        return {"success": True, "message": "Configuração reCAPTCHA salva com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar config reCAPTCHA: {str(e)}")


@router.get("/recaptcha/public")
async def get_recaptcha_public():
    """Retorna apenas dados públicos do reCAPTCHA (para o frontend/login)"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT recaptcha_enabled, recaptcha_site_key
                FROM integracoes_config WHERE id = 1
            """)
            result = cur.fetchone()
            if result and result[0]:
                return {
                    "enabled": True,
                    "site_key": result[1] or "",
                }
            return {"enabled": False, "site_key": ""}
    except Exception:
        return {"enabled": False, "site_key": ""}
