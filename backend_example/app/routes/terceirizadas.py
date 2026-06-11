"""
Rotas de Terceirizadas (Empresas Intermediadoras)
CRUD de empresas terceirizadas que intermediam montadores
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from pydantic import BaseModel
import psycopg2.extras
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user

router = APIRouter()


# ============================================================
# Modelos
# ============================================================

class TerceirizadaBase(BaseModel):
    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    cnpj: Optional[str] = None
    percentual_montagem: float = 5.0
    percentual_assistencia: float = 5.0
    percentual_desmontagem: float = 5.0
    ativo: bool = True
    observacoes: Optional[str] = None


class TerceirizadaCreate(TerceirizadaBase):
    pass


class TerceirizadaUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    cnpj: Optional[str] = None
    percentual_montagem: Optional[float] = None
    percentual_assistencia: Optional[float] = None
    percentual_desmontagem: Optional[float] = None
    ativo: Optional[bool] = None
    observacoes: Optional[str] = None


# ============================================================
# Endpoints
# ============================================================

@router.get("")
def listar_terceirizadas(
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
):
    """Lista todas as terceirizadas (admin only)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        where_clause = " WHERE 1=1"
        params = []
        
        if search:
            where_clause += " AND nome ILIKE %s"
            params.append(f"%{search}%")
        
        if ativo is not None:
            where_clause += " AND ativo = %s"
            params.append(ativo)
        
        cur.execute(
            f"SELECT * FROM terceirizadas{where_clause} ORDER BY nome ASC",
            params
        )
        return cur.fetchall()


@router.get("/{id}")
def obter_terceirizada(
    id: int,
    current_user: dict = Depends(get_current_user),
):
    """Obtém uma terceirizada por ID"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM terceirizadas WHERE id = %s", (id,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Terceirizada não encontrada")
        
        return result


@router.post("", status_code=201)
def criar_terceirizada(
    terceirizada: TerceirizadaCreate,
    current_user: dict = Depends(get_current_user),
):
    """Cria uma nova terceirizada"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            INSERT INTO terceirizadas (
                nome, telefone, email, cnpj,
                percentual_montagem, percentual_assistencia, percentual_desmontagem,
                ativo, observacoes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            terceirizada.nome,
            terceirizada.telefone,
            terceirizada.email,
            terceirizada.cnpj,
            terceirizada.percentual_montagem,
            terceirizada.percentual_assistencia,
            terceirizada.percentual_desmontagem,
            terceirizada.ativo,
            terceirizada.observacoes,
        ))
        
        result = cur.fetchone()
        conn.commit()
        return result


@router.put("/{id}")
def atualizar_terceirizada(
    id: int,
    terceirizada: TerceirizadaUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza uma terceirizada"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se existe
        cur.execute("SELECT id FROM terceirizadas WHERE id = %s", (id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Terceirizada não encontrada")
        
        # Construir UPDATE dinâmico
        updates = terceirizada.dict(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        campos = [f"{k} = %s" for k in updates.keys()]
        valores = list(updates.values())
        valores.append(id)
        
        cur.execute(
            f"UPDATE terceirizadas SET {', '.join(campos)}, updated_at = NOW() WHERE id = %s RETURNING *",
            valores
        )
        
        result = cur.fetchone()
        conn.commit()
        return result


@router.delete("/{id}")
def excluir_terceirizada(
    id: int,
    current_user: dict = Depends(get_current_user),
):
    """Desativa uma terceirizada (soft delete)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Verificar se há montadores vinculados
        cur.execute("SELECT COUNT(*) FROM montadores WHERE terceirizada_id = %s", (id,))
        count = cur.fetchone()[0]
        
        if count > 0:
            # Desativar em vez de excluir
            cur.execute(
                "UPDATE terceirizadas SET ativo = FALSE, updated_at = NOW() WHERE id = %s",
                (id,)
            )
            conn.commit()
            return {
                "message": f"Terceirizada desativada (possui {count} montadores vinculados)",
                "desativada": True
            }
        
        cur.execute("DELETE FROM terceirizadas WHERE id = %s", (id,))
        conn.commit()
        return {"message": "Terceirizada excluída com sucesso"}


@router.get("/{id}/pagamentos")
def pagamentos_terceirizada(
    id: int,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna resumo de pagamentos da terceirizada.
    Mostra: quanto NM paga para a terc, quanto terc paga para cada montador.
    """
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    from datetime import datetime
    
    if not mes:
        mes = datetime.now().month
    if not ano:
        ano = datetime.now().year
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar terceirizada
        cur.execute("SELECT * FROM terceirizadas WHERE id = %s", (id,))
        terc = cur.fetchone()
        if not terc:
            raise HTTPException(status_code=404, detail="Terceirizada não encontrada")
        
        # Buscar montadores vinculados
        cur.execute("""
            SELECT id, nome, identificador,
                   percentual_montagem, percentual_assistencia, percentual_desmontagem
            FROM montadores 
            WHERE terceirizada_id = %s AND tipo_pagamento = 'terceirizada' AND ativo = TRUE
        """, (id,))
        montadores = cur.fetchall()
        
        # Para cada montador, buscar boletins pendentes
        resultado_montadores = []
        total_venda = 0
        total_comissao_terc = 0
        total_comissao_mont = 0
        
        for mont in montadores:
            cur.execute("""
                SELECT 
                    COUNT(*) as qtd_boletins,
                    COALESCE(SUM(valor_venda), 0) as total_venda,
                    COALESCE(SUM(comissao_calculada), 0) as total_comissao_montador
                FROM ingestao_boletins_montador
                WHERE identificador_montador = %s
                  AND status = 'pendente'
                  AND EXTRACT(MONTH FROM data_montagem) = %s
                  AND EXTRACT(YEAR FROM data_montagem) = %s
            """, (mont['identificador'], mes, ano))
            
            dados = cur.fetchone()
            
            if dados and dados['qtd_boletins'] > 0:
                # percentual_montagem é armazenado como porcentagem (ex: 13 = 13%), 
                # então divide por 100 para obter o fator decimal
                comissao_terc = float(dados['total_venda']) * (float(terc['percentual_montagem']) / 100)
                
                resultado_montadores.append({
                    "montador_id": mont['id'],
                    "montador_nome": mont['nome'],
                    "qtd_boletins": dados['qtd_boletins'],
                    "total_venda": float(dados['total_venda']),
                    "comissao_montador": float(dados['total_comissao_montador']),
                    "comissao_terceirizada": comissao_terc,
                })
                
                total_venda += float(dados['total_venda'])
                total_comissao_mont += float(dados['total_comissao_montador'])
                total_comissao_terc += comissao_terc
        
        return {
            "terceirizada": dict(terc),
            "periodo": f"{mes:02d}/{ano}",
            "montadores": resultado_montadores,
            "resumo": {
                "total_venda": total_venda,
                "total_comissao_terceirizada": total_comissao_terc,
                "nm_paga_terceirizada": total_comissao_terc,
                "total_comissao_montadores": total_comissao_mont,
                "terc_paga_montadores": total_comissao_mont,
                "margem_terceirizada": total_comissao_terc - total_comissao_mont,
            }
        }
