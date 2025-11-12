# backend/app/routes/blacklist.py

"""
Rotas para gerenciamento de blacklist de O.S. e Boletins
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2.extras
from app.database import get_db_connection

router = APIRouter()

# ===== MODELS =====

class OSBlacklistAdd(BaseModel):
    """Modelo para adicionar O.S. à blacklist"""
    prestador_id: int
    os_numero: str
    motivo: str = None

class BoletimBlacklistAdd(BaseModel):
    """Modelo para adicionar Boletim à blacklist"""
    montador_id: int
    boletim: str
    motivo: str = None

class CheckList(BaseModel):
    """Modelo para verificar lista de números"""
    numbers: list[str]

# ===== ROTAS PARA O.S. (PRESTADORES) =====

@router.post("/os")
def adicionar_os_blacklist(item: OSBlacklistAdd):
    """
    Adiciona uma O.S. à blacklist
    
    Args:
        item: Dados da O.S. (prestador_id, os_numero, motivo)
    
    Returns:
        success: True se adicionado com sucesso
        message: Mensagem de confirmação
        id: ID do item criado
    
    Raises:
        HTTPException 400: Se O.S. já está na blacklist
    """
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO os_blacklist (prestador_id, os_numero, motivo)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (item.prestador_id, item.os_numero, item.motivo))
                
                blacklist_id = cur.fetchone()[0]
            
            conn.commit()
            return {
                "success": True,
                "message": f"O.S. {item.os_numero} adicionada à blacklist",
                "id": blacklist_id
            }
    
    except psycopg2.IntegrityError:
        raise HTTPException(
            status_code=400, 
            detail=f"O.S. {item.os_numero} já está na blacklist para este prestador"
        )

@router.get("/os")
def listar_os_blacklist():
    """
    Lista todas as O.S. na blacklist
    
    Returns:
        Lista de objetos com:
        - id: ID do registro
        - prestador_id: ID do prestador
        - prestador_nome: Nome do prestador
        - os_numero: Número da O.S.
        - motivo: Motivo da blacklist
        - data_adicao: Quando foi adicionado
    """
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    osb.id,
                    osb.prestador_id,
                    osb.os_numero,
                    osb.motivo,
                    osb.data_adicao,
                    p.nome as prestador_nome
                FROM os_blacklist osb
                JOIN prestadores p ON p.id = osb.prestador_id
                ORDER BY osb.data_adicao DESC
            """)
            
            items = cur.fetchall()
    
    return items

@router.delete("/os/{id}")
def remover_os_blacklist(id: int):
    """
    Remove uma O.S. da blacklist
    
    Args:
        id: ID do registro na blacklist
    
    Returns:
        success: True se removido
        message: Mensagem de confirmação
    
    Raises:
        HTTPException 404: Se item não foi encontrado
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM os_blacklist WHERE id = %s", (id,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Item não encontrado")
        
        conn.commit()
    
    return {"success": True, "message": "Item removido da blacklist"}

@router.post("/os/check")
def verificar_os_blacklist(data: CheckList):
    """
    Verifica quais O.S. de uma lista estão na blacklist
    
    Args:
        data: Lista de números de O.S.
    
    Returns:
        Lista com números que estão bloqueados
    """
    
    if not data.numbers:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT os_numero 
                FROM os_blacklist 
                WHERE os_numero = ANY(%s)
            """, (data.numbers,))
            
            blacklisted = [row['os_numero'] for row in cur.fetchall()]
    
    return blacklisted

# ===== ROTAS PARA BOLETINS (MONTADORES) =====

@router.post("/boletins")
def adicionar_boletim_blacklist(item: BoletimBlacklistAdd):
    """
    Adiciona um Boletim à blacklist
    
    Args:
        item: Dados do boletim (montador_id, boletim, motivo)
    
    Returns:
        success: True se adicionado com sucesso
        message: Mensagem de confirmação
        id: ID do item criado
    
    Raises:
        HTTPException 400: Se boletim já está na blacklist
    """
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO boletins_blacklist (montador_id, boletim, motivo)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (item.montador_id, item.boletim, item.motivo))
                
                blacklist_id = cur.fetchone()[0]
            
            conn.commit()
            return {
                "success": True,
                "message": f"Boletim {item.boletim} adicionado à blacklist",
                "id": blacklist_id
            }
    
    except psycopg2.IntegrityError:
        raise HTTPException(
            status_code=400, 
            detail=f"Boletim {item.boletim} já está na blacklist para este montador"
        )

@router.get("/boletins")
def listar_boletins_blacklist():
    """
    Lista todos os boletins na blacklist
    
    Returns:
        Lista de objetos com:
        - id: ID do registro
        - montador_id: ID do montador
        - montador_nome: Nome do montador
        - boletim: Número do boletim
        - motivo: Motivo da blacklist
        - data_adicao: Quando foi adicionado
    """
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    bb.id,
                    bb.montador_id,
                    bb.boletim,
                    bb.motivo,
                    bb.data_adicao,
                    m.nome as montador_nome
                FROM boletins_blacklist bb
                JOIN montadores m ON m.id = bb.montador_id
                ORDER BY bb.data_adicao DESC
            """)
            
            items = cur.fetchall()
    
    return items

@router.delete("/boletins/{id}")
def remover_boletim_blacklist(id: int):
    """
    Remove um boletim da blacklist
    
    Args:
        id: ID do registro na blacklist
    
    Returns:
        success: True se removido
        message: Mensagem de confirmação
    
    Raises:
        HTTPException 404: Se item não foi encontrado
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM boletins_blacklist WHERE id = %s", (id,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Item não encontrado")
        
        conn.commit()
    
    return {"success": True, "message": "Item removido da blacklist"}

@router.post("/boletins/check")
def verificar_boletins_blacklist(data: CheckList):
    """
    Verifica quais boletins de uma lista estão na blacklist
    
    Args:
        data: Lista de números de boletins
    
    Returns:
        Lista com números que estão bloqueados
    """
    
    if not data.numbers:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT boletim 
                FROM boletins_blacklist 
                WHERE boletim = ANY(%s)
            """, (data.numbers,))
            
            blacklisted = [row['boletim'] for row in cur.fetchall()]
    
    return blacklisted
