"""
Rotas de Montadores
Endpoints para CRUD de montadores
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
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
    percentual_montagem: float = 0.05
    percentual_assistencia: float = 0.05
    percentual_desmontagem: float = 0.05
    auxilio_semanal: float = 100.0
    ativo: bool = True
    regra_envio: str = "Nenhuma"
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: int = 10
    emails_adicionais: Optional[str] = None

class MontadorCreate(MontadorBase):
    pass

class MontadorUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    percentual_montagem: Optional[float] = None
    percentual_assistencia: Optional[float] = None
    percentual_desmontagem: Optional[float] = None
    auxilio_semanal: Optional[float] = None
    ativo: Optional[bool] = None
    regra_envio: Optional[str] = None
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: Optional[int] = None
    emails_adicionais: Optional[str] = None

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
        
        query = "SELECT * FROM montadores WHERE 1=1"
        params = []
        
        if search:
            query += " AND nome ILIKE %s"
            params.append(f"%{search}%")
        
        if ativo is not None:
            query += " AND ativo = %s"
            params.append(ativo)
        
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cur.execute(count_query, params)
        total = cur.fetchone()['count']
        
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
                (nome, identificador, email, telefone, percentual_montagem, 
                 percentual_assistencia, percentual_desmontagem,
                 auxilio_semanal, ativo, fornecedor_id, regra_envio, dias_envio,
                 tempo_vencimento_dias, emails_adicionais)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    montador.nome,
                    montador.identificador,
                    montador.email,
                    montador.telefone,
                    montador.percentual_montagem,
                    montador.percentual_assistencia,
                    montador.percentual_desmontagem,
                    montador.auxilio_semanal,
                    montador.ativo,
                    montador.fornecedor_id,
                    montador.regra_envio,
                    montador.dias_envio,
                    montador.tempo_vencimento_dias,
                    montador.emails_adicionais
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
        
        # Verificar se existe
        cur.execute("SELECT id FROM montadores WHERE id = %s", (montador_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Montador não encontrado")
        
        # Construir query de update dinamicamente
        campos = []
        valores = []
        
        for campo, valor in montador.dict(exclude_unset=True).items():
            campos.append(f"{campo} = %s")
            valores.append(valor)
        
        if not campos:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        valores.append(montador_id)
        query = f"UPDATE montadores SET {', '.join(campos)} WHERE id = %s RETURNING *"
        
        cur.execute(query, valores)
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
