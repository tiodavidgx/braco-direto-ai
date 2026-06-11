"""
Rotas de Montadores
Endpoints para CRUD de montadores
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import psycopg2.extras
from app.database import get_db_connection

router = APIRouter()

# Modelos Pydantic
class MontadorBase(BaseModel):
    nome: str
    identificador: str
    email: EmailStr
    fornecedor_id: str
    telefone: Optional[str] = None
    pix: str = ""
    percentual_montagem: float = 0.05
    percentual_assistencia: float = 0.05
    percentual_desmontagem: float = 0.05
    auxilio_semanal: float = 100.0
    ativo: bool = True
    regra_envio: str = "Nenhuma"
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: int = 10
    emails_adicionais: Optional[str] = None
    filial: Optional[str] = None
    cidade: Optional[str] = None
    dia_envio_1: Optional[int] = None
    dia_envio_2: Optional[int] = None
    # Novos campos - Envio Automático
    envio_automatico: bool = True
    dia_fechamento: int = 25
    dias_envio_mes: Optional[List[int]] = None
    prazo_pagamento_dias: int = 10
    email_responsavel_nm: Optional[str] = None
    # Novos campos - Terceirizada
    tipo_pagamento: str = "novo_mundo"
    terceirizada_id: Optional[int] = None
    # Template de email
    email_template_id: Optional[int] = None

class MontadorCreate(MontadorBase):
    pass

class MontadorUpdate(BaseModel):
    nome: Optional[str] = None
    identificador: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    pix: Optional[str] = None
    percentual_montagem: Optional[float] = None
    percentual_assistencia: Optional[float] = None
    percentual_desmontagem: Optional[float] = None
    auxilio_semanal: Optional[float] = None
    ativo: Optional[bool] = None
    regra_envio: Optional[str] = None
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: Optional[int] = None
    emails_adicionais: Optional[str] = None
    filial: Optional[str] = None
    cidade: Optional[str] = None
    dia_envio_1: Optional[int] = None
    dia_envio_2: Optional[int] = None
    # Novos campos - Envio Automático
    envio_automatico: Optional[bool] = None
    dia_fechamento: Optional[int] = None
    dias_envio_mes: Optional[List[int]] = None
    prazo_pagamento_dias: Optional[int] = None
    email_responsavel_nm: Optional[str] = None
    # Novos campos - Terceirizada
    tipo_pagamento: Optional[str] = None
    terceirizada_id: Optional[int] = None
    # Template de email
    email_template_id: Optional[int] = None

@router.get("")
def listar_montadores(
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000)
):
    """Lista todos os montadores com paginação e filtros"""
    offset = (page - 1) * limit
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query base para filtros
        where_clause = " WHERE 1=1"
        params = []
        
        if search:
            where_clause += " AND nome ILIKE %s"
            params.append(f"%{search}%")
        
        if ativo is not None:
            where_clause += " AND ativo = %s"
            params.append(ativo)
        
        # Count total
        count_query = "SELECT COUNT(*) FROM montadores" + where_clause
        cur.execute(count_query, params)
        total = cur.fetchone()['count']
        
        # Query principal com cidade
        query = "SELECT *, localidade as cidade FROM montadores" + where_clause
        query += " ORDER BY nome ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        montadores = cur.fetchall()
        
        return {
            "data": montadores,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }

@router.post("", status_code=201)
def criar_montador(montador: MontadorCreate):
    """Cria um novo montador"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO montadores 
                (nome, identificador, email, telefone, pix, percentual_montagem, 
                 percentual_assistencia, percentual_desmontagem,
                 auxilio_semanal, ativo, fornecedor_id, regra_envio, dias_envio,
                 tempo_vencimento_dias, emails_adicionais, filial, localidade,
                 dia_envio_1, dia_envio_2,
                 envio_automatico, dia_fechamento, dias_envio_mes, prazo_pagamento_dias,
                 email_responsavel_nm, tipo_pagamento, terceirizada_id, email_template_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    montador.nome,
                    montador.identificador,
                    montador.email,
                    montador.telefone,
                    montador.pix,
                    montador.percentual_montagem,
                    montador.percentual_assistencia,
                    montador.percentual_desmontagem,
                    montador.auxilio_semanal,
                    montador.ativo,
                    montador.fornecedor_id,
                    montador.regra_envio,
                    montador.dias_envio,
                    montador.tempo_vencimento_dias,
                    montador.emails_adicionais,
                    montador.filial,
                    montador.cidade,
                    montador.dia_envio_1,
                    montador.dia_envio_2,
                    montador.envio_automatico,
                    montador.dia_fechamento,
                    montador.dias_envio_mes,
                    montador.prazo_pagamento_dias,
                    montador.email_responsavel_nm,
                    montador.tipo_pagamento,
                    montador.terceirizada_id,
                    montador.email_template_id
                )
            )
            montador_id = cur.fetchone()[0]
            return {
                "id": montador_id,
                "message": "Montador criado com sucesso"
            }
        except psycopg2.IntegrityError:
            raise HTTPException(
                status_code=400,
                detail="Identificador já existe"
            )

@router.put("/{montador_id}")
def atualizar_montador(montador_id: int, montador: MontadorUpdate):
    """Atualiza um montador existente"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se existe e pegar valores atuais dos campos unique
        cur.execute(
            "SELECT id, identificador, fornecedor_id FROM montadores WHERE id = %s",
            (montador_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Montador não encontrado")
        identificador_atual = row['identificador']
        fornecedor_id_atual = row.get('fornecedor_id')
        
        # Construir query de update dinamicamente
        campos = []
        valores = []
        
        for campo, valor in montador.dict(exclude_unset=True).items():            # Pular campos com valor None (não foram realmente alterados)
            if valor is None:
                continue            # Pular campos unique se valor igual ao atual
            if campo == "identificador" and str(valor or '').strip() == str(identificador_atual or '').strip():
                continue
            if campo == "fornecedor_id" and str(valor or '').strip() == str(fornecedor_id_atual or '').strip():
                continue
            
            # Validar campos unique antes do UPDATE
            if campo == "identificador":
                cur.execute(
                    "SELECT id FROM montadores WHERE identificador = %s AND id != %s",
                    (str(valor).strip(), montador_id)
                )
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Identificador já está em uso por outro montador")
            
            if campo == "fornecedor_id":
                cur.execute(
                    "SELECT id FROM montadores WHERE fornecedor_id = %s AND id != %s",
                    (str(valor).strip(), montador_id)
                )
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Fornecedor ID já está em uso por outro montador")
            
            db_campo = "localidade" if campo == "cidade" else campo
            campos.append(f"{db_campo} = %s")
            valores.append(valor)
        
        if not campos:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        valores.append(montador_id)
        query = f"UPDATE montadores SET {', '.join(campos)} WHERE id = %s RETURNING *"
        
        try:
            cur.execute(query, valores)
        except psycopg2.IntegrityError as e:
            conn.rollback()
            msg = str(e)
            if 'identificador' in msg:
                detail = "Identificador já está em uso por outro montador"
            elif 'fornecedor_id' in msg:
                detail = "Fornecedor ID já está em uso por outro montador"
            else:
                detail = f"Erro de integridade: {msg}"
            raise HTTPException(status_code=400, detail=detail)
        montador_atualizado = cur.fetchone()
        
        return montador_atualizado

@router.delete("/{montador_id}", status_code=204)
def deletar_montador(montador_id: int):
    """Remove um montador"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Verificar se existe
        cur.execute("SELECT id FROM montadores WHERE id = %s", (montador_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Montador não encontrado")
        
        # Deletar
        cur.execute("DELETE FROM montadores WHERE id = %s", (montador_id,))
        
        return None
