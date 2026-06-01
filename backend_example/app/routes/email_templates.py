"""
Rotas de Templates de Email
CRUD para gerenciar múltiplos templates de email por tipo
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db_connection
import psycopg2.extras
from app.routes.sistema_auth import get_current_user

router = APIRouter()


class EmailTemplateCreate(BaseModel):
    tipo: str  # 'prestador' ou 'montador'
    nome: str
    descricao: Optional[str] = None
    assunto: str
    corpo: str
    cc: Optional[str] = None
    variaveis: Optional[List[str]] = None
    is_default: bool = False


class EmailTemplateUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    assunto: Optional[str] = None
    corpo: Optional[str] = None
    cc: Optional[str] = None
    variaveis: Optional[List[str]] = None
    ativo: Optional[bool] = None
    is_default: Optional[bool] = None


@router.get("")
def listar_templates(
    tipo: Optional[str] = None,
    ativo: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Lista todos os templates de email"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = "SELECT * FROM email_config WHERE 1=1"
        params = []
        
        if tipo:
            query += " AND tipo = %s"
            params.append(tipo)
        if ativo is not None:
            query += " AND ativo = %s"
            params.append(ativo)
        
        query += " ORDER BY tipo, is_default DESC, nome ASC"
        
        cur.execute(query, params)
        templates = cur.fetchall()
        return {"data": [dict(t) for t in templates]}


@router.get("/{template_id}")
def obter_template(
    template_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Obtém um template específico"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM email_config WHERE id = %s", (template_id,))
        template = cur.fetchone()
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        return dict(template)


@router.post("")
def criar_template(
    dados: EmailTemplateCreate,
    current_user: dict = Depends(get_current_user)
):
    """Cria um novo template de email"""
    if dados.tipo not in ('prestador', 'montador'):
        raise HTTPException(status_code=400, detail="Tipo deve ser 'prestador' ou 'montador'")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Se for default, desmarcar outros defaults do mesmo tipo
        if dados.is_default:
            cur.execute("""
                UPDATE email_config SET is_default = FALSE 
                WHERE tipo = %s AND is_default = TRUE
            """, (dados.tipo,))
        
        cur.execute("""
            INSERT INTO email_config (tipo, nome, descricao, assunto, corpo, cc, variaveis, ativo, is_default)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
            RETURNING *
        """, (
            dados.tipo, dados.nome, dados.descricao,
            dados.assunto, dados.corpo, dados.cc,
            dados.variaveis or [], dados.is_default
        ))
        
        template = cur.fetchone()
        conn.commit()
        return dict(template)


@router.put("/{template_id}")
def atualizar_template(
    template_id: int,
    dados: EmailTemplateUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Atualiza um template de email"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM email_config WHERE id = %s", (template_id,))
        template = cur.fetchone()
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        dados_dict = dados.dict(exclude_unset=True)
        
        # Se for marcar como default, desmarcar outros
        if dados_dict.get('is_default'):
            cur.execute("""
                UPDATE email_config SET is_default = FALSE 
                WHERE tipo = %s AND is_default = TRUE AND id != %s
            """, (template['tipo'], template_id))
        
        update_fields = []
        params = []
        
        for field, value in dados_dict.items():
            if field in ('nome', 'descricao', 'assunto', 'corpo', 'cc', 'variaveis', 'ativo', 'is_default'):
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        update_fields.append("atualizado_em = NOW()")
        params.append(template_id)
        
        cur.execute(f"""
            UPDATE email_config
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """, params)
        
        updated = cur.fetchone()
        conn.commit()
        return dict(updated)


@router.delete("/{template_id}")
def excluir_template(
    template_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Exclui um template de email (não permite excluir o único default do tipo)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM email_config WHERE id = %s", (template_id,))
        template = cur.fetchone()
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        # Não permitir excluir se for o único template do tipo
        cur.execute("SELECT COUNT(*) as cnt FROM email_config WHERE tipo = %s", (template['tipo'],))
        count = cur.fetchone()['cnt']
        if count <= 1:
            raise HTTPException(status_code=400, detail="Não é possível excluir o único template deste tipo")
        
        # Se for default, passar para outro template do mesmo tipo
        if template['is_default']:
            cur.execute("""
                UPDATE email_config SET is_default = TRUE 
                WHERE tipo = %s AND id != %s 
                ORDER BY id LIMIT 1
            """, (template['tipo'], template_id))
        
        cur.execute("DELETE FROM email_config WHERE id = %s", (template_id,))
        conn.commit()
        
        return {"success": True, "message": "Template excluído com sucesso"}
