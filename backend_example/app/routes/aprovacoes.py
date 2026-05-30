"""
Rotas de Aprovação de Edições de Montadores
Workflow: operador edita campo crítico → vai para fila → admin aprova/rejeita
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import psycopg2.extras
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user

router = APIRouter()


# ============================================================
# Modelos
# ============================================================

class AprovarRejeitarRequest(BaseModel):
    motivo_rejeicao: Optional[str] = None


# ============================================================
# Helpers
# ============================================================

CAMPOS_RESTRITOS = {
    'percentual_montagem', 'percentual_assistencia', 'percentual_desmontagem',
    'auxilio_semanal', 'dias_envio_mes', 'dia_fechamento', 'prazo_pagamento_dias',
    'envio_automatico',
}


def is_admin(user: dict) -> bool:
    return user.get('role') == 'admin'


# ============================================================
# Endpoints
# ============================================================

@router.get("/montadores")
def listar_aprovacoes_pendentes(
    status: Optional[str] = "pendente",
    current_user: dict = Depends(get_current_user),
):
    """Lista aprovações pendentes (admin only)"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                a.*,
                m.nome as montador_nome,
                m.identificador as montador_identificador
            FROM aprovacoes_montador a
            JOIN montadores m ON m.id = a.montador_id
            WHERE a.status = %s
            ORDER BY a.created_at DESC
        """, (status,))
        
        return cur.fetchall()


@router.get("/montadores/contagem")
def contar_aprovacoes_pendentes(
    current_user: dict = Depends(get_current_user),
):
    """Retorna contagem de aprovações pendentes (para badge no menu)"""
    if not is_admin(current_user):
        return {"pendentes": 0}
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM aprovacoes_montador WHERE status = 'pendente'"
        )
        count = cur.fetchone()[0]
        return {"pendentes": count}


@router.post("/montadores/{aprovacao_id}/aprovar")
def aprovar_edicao(
    aprovacao_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Aprova uma edição pendente e aplica no montador"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar aprovação
        cur.execute(
            "SELECT * FROM aprovacoes_montador WHERE id = %s AND status = 'pendente'",
            (aprovacao_id,)
        )
        aprovacao = cur.fetchone()
        
        if not aprovacao:
            raise HTTPException(status_code=404, detail="Aprovação não encontrada ou já processada")
        
        # Aplicar alteração no montador
        campo = aprovacao['campo']
        valor_novo = aprovacao['valor_novo']
        
        # Converter valor para o tipo correto
        if campo in ('dias_envio_mes',):
            # Array de inteiros
            import json
            if isinstance(valor_novo, str):
                valor_novo = json.loads(valor_novo)
            cur.execute(
                f"UPDATE montadores SET {campo} = %s::integer[] WHERE id = %s",
                (valor_novo, aprovacao['montador_id'])
            )
        elif campo in ('envio_automatico',):
            valor_novo = valor_novo in (True, 'true', 'True', 1, '1')
            cur.execute(
                f"UPDATE montadores SET {campo} = %s WHERE id = %s",
                (valor_novo, aprovacao['montador_id'])
            )
        elif campo in ('percentual_montagem', 'percentual_assistencia', 'percentual_desmontagem'):
            cur.execute(
                f"UPDATE montadores SET {campo} = %s WHERE id = %s",
                (float(valor_novo), aprovacao['montador_id'])
            )
        else:
            cur.execute(
                f"UPDATE montadores SET {campo} = %s WHERE id = %s",
                (valor_novo, aprovacao['montador_id'])
            )
        
        # Marcar como aprovado
        cur.execute("""
            UPDATE aprovacoes_montador 
            SET status = 'aprovado', 
                aprovador_id = %s, 
                aprovador_nome = %s,
                atualizado_em = NOW()
            WHERE id = %s
        """, (current_user['id'], current_user.get('nome', 'Admin'), aprovacao_id))
        
        conn.commit()
        
        return {
            "message": "Alteração aprovada e aplicada com sucesso",
            "campo": campo,
            "montador_id": aprovacao['montador_id']
        }


@router.post("/montadores/{aprovacao_id}/rejeitar")
def rejeitar_edicao(
    aprovacao_id: int,
    body: AprovarRejeitarRequest,
    current_user: dict = Depends(get_current_user),
):
    """Rejeita uma edição pendente"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE aprovacoes_montador 
            SET status = 'rejeitado', 
                aprovador_id = %s, 
                aprovador_nome = %s,
                motivo_rejeicao = %s,
                atualizado_em = NOW()
            WHERE id = %s AND status = 'pendente'
        """, (
            current_user['id'],
            current_user.get('nome', 'Admin'),
            body.motivo_rejeicao,
            aprovacao_id,
        ))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Aprovação não encontrada ou já processada")
        
        conn.commit()
        
        return {"message": "Alteração rejeitada"}
